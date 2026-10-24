//! Serial link to the ESP32 ADV_BLE2UART firmware (ble50_scan) - the complete
//! wire protocol.
//!
//! Frame layout (host -> device, device -> host, advertisements, responses):
//!
//! ```text
//! off  size  meaning                                   adv report        command
//! 0    1     payload_len                               0..229            data_len echo
//! 1    1     RSSI (s8) / CMD_ID                          RSSI              CMD_ID_xxx
//! 2    1     event_type / status (bit 7 = spontaneous)   event_type        status
//! 3    1     addr_type | dir<<4 / data_len               addr type         FRAME_DATA_LEN echo
//! 4    1     primary_phy | secondary_phy<<4 / 0xFF       PHY map           0xFF for commands
//! 5..10 6    peer MAC (LE) / command data field          6-byte MAC         command parameters
//! 11.. N     extended advertisement payload               payload_len       command-specific
//! end-2 2    CRC-16/ARC, little endian, over everything before it
//! ```
//!
//! `byte[4] == 0xFF` discriminates a command response/event from an
//! advertisement report; within a command frame, bit 7 of `byte[2]` marks a
//! spontaneous device-to-host event (GATT discovery, GPIO edge, ...).

use std::io::{Read, Write};
use std::os::unix::io::{AsRawFd, RawFd};
use std::sync::mpsc::{Receiver, RecvTimeoutError};
use std::sync::{Arc, atomic::{AtomicBool, Ordering}};
use std::time::{Duration, Instant};

/// CRC used by the firmware (`main/crc.c`, and `crc_16()` in adv2uart.py):
/// reflected polynomial 0xA001, init 0xFFFF, no final XOR. The firmware README
/// calls it "CRC-16/ARC", but that combination is what the standard catalogue
/// names **CRC-16/MODBUS** (CRC-16/ARC uses init 0x0000); the reference check
/// value for "123456789" is 0x4B37, not 0xBB3D. A frame with its own CRC
/// appended checks out to zero, which is how adv2uart.py validates packets.
pub fn crc16_arc(data: &[u8]) -> u16 {
    let mut crc: u16 = 0xFFFF;
    for byte in data {
        crc ^= *byte as u16;
        for _ in 0..8 {
            if crc & 1 != 0 {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    crc
}

pub const ADV_DATA_MAX: usize = 229;
pub const CMD_DATA_MAX: usize = 6;

/// Command identifiers (host -> device).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Cmd {
    Info = 0x00,
    Scan = 0x01,
    Wmac = 0x02,
    Bmac = 0x03,
    Clrm = 0x04,
    Prnt = 0x05,
    Gpio = 0x06,
    Uart = 0x08,
    Rfsdk = 0x09,
    Version = 0x0A,
    TxAdv = 0x0B,
    Conn = 0x0C,
    TxData = 0x0D,
    RxData = 0x0E,
    Vbat = 0x0F,
    GpioEvt = 0x10,
}

impl Cmd {
    pub fn from_u8(value: u8) -> Option<Cmd> {
        Some(match value {
            0x00 => Cmd::Info,
            0x01 => Cmd::Scan,
            0x02 => Cmd::Wmac,
            0x03 => Cmd::Bmac,
            0x04 => Cmd::Clrm,
            0x05 => Cmd::Prnt,
            0x06 => Cmd::Gpio,
            0x08 => Cmd::Uart,
            0x09 => Cmd::Rfsdk,
            0x0A => Cmd::Version,
            0x0B => Cmd::TxAdv,
            0x0C => Cmd::Conn,
            0x0D => Cmd::TxData,
            0x0E => Cmd::RxData,
            0x0F => Cmd::Vbat,
            0x10 => Cmd::GpioEvt,
            _ => return None,
        })
    }

    pub fn name(&self) -> &'static str {
        match self {
            Cmd::Info => "INFO",
            Cmd::Scan => "SCAN",
            Cmd::Wmac => "WMAC",
            Cmd::Bmac => "BMAC",
            Cmd::Clrm => "CLRM",
            Cmd::Prnt => "PRNT",
            Cmd::Gpio => "GPIO",
            Cmd::Uart => "UART",
            Cmd::Rfsdk => "RFSDK",
            Cmd::Version => "VERSION",
            Cmd::TxAdv => "TXADV",
            Cmd::Conn => "CONN",
            Cmd::TxData => "TXDATA",
            Cmd::RxData => "RXDATA",
            Cmd::Vbat => "VBAT",
            Cmd::GpioEvt => "GPIOEVT",
        }
    }
}

/// Response status of a command frame.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    Ok,
    Metadata(u8),
    BadArguments,
    UnknownPin,
    Denied,
    BadValue,
    Other(u8),
}

impl Status {
    pub fn from_u8(value: u8) -> Status {
        match value {
            0 => Status::Ok,
            1 => Status::BadArguments,
            2 => Status::UnknownPin,
            3 => Status::Denied,
            4 => Status::BadValue,
            other => Status::Other(other),
        }
    }

    pub fn is_ok(&self) -> bool {
        matches!(self, Status::Ok | Status::Metadata(_))
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Status::Ok | Status::Metadata(_) => "OK",
            Status::BadArguments => "bad arguments",
            Status::UnknownPin => "unknown pin",
            Status::Denied => "denied",
            Status::BadValue => "bad value",
            Status::Other(_) => "error",
        }
    }
}

/// An advertisement report (`byte[4] != 0xFF`).
#[derive(Debug, Clone)]
pub struct AdvReport {
    pub rssi: i8,
    /// Raw `event_type` byte (the reference implementation exposes it as is).
    pub event_type: u8,
    pub addr_type: u8,
    pub directed: bool,
    /// Raw PHY map byte: low nibble = primary PHY, high nibble = secondary PHY
    /// (`0xFF` would mean a command frame). ESP32 firmware codes are 1=1M,
    /// 2=2M, 3=Coded; secondary 0 means no secondary advertisement.
    pub phys: u8,
    /// On-wire (little endian) address exactly as the firmware reports it.
    pub mac: [u8; 6],
    /// Advertisement data: the legacy AD structure or the extended payload.
    pub data: Vec<u8>,
}

impl AdvReport {
    /// The address in the order the configuration and the codecs use, i.e. the
    /// reverse of the on-wire order (`ReversedMacAddress` in adv2uart.py).
    pub fn mac_display(&self) -> [u8; 6] {
        let mut mac = self.mac;
        mac.reverse();
        mac
    }

    /// "AABBCCDDEEFF".
    pub fn mac_string(&self) -> String {
        crate::config::mac_string(&self.mac_display())
    }

    /// "AA:BB:CC:DD:EE:FF".
    pub fn mac_colon(&self) -> String {
        self.mac_display()
            .iter()
            .map(|b| format!("{b:02X}"))
            .collect::<Vec<_>>()
            .join(":")
    }

    pub fn primary_phy(&self) -> u8 {
        self.phys & 0x0F
    }

    pub fn secondary_phy(&self) -> u8 {
        self.phys >> 4
    }

    pub fn phy_summary(&self) -> String {
        fn name(code: u8) -> &'static str {
            match code {
                0 => "none",
                1 => "1M",
                2 => "2M",
                3 => "Coded",
                _ => "unknown",
            }
        }
        format!("phy_raw=0x{:02X} primary={} secondary={}", self.phys, name(self.primary_phy()), name(self.secondary_phy()))
    }

    /// True when a primary or secondary 1M PHY is reported.
    #[cfg(test)]
    pub fn hint_1m(&self) -> bool {
        self.primary_phy() == 1 || self.secondary_phy() == 1
    }

    /// True when a primary or secondary Coded PHY is reported.
    #[cfg(test)]
    pub fn hint_coded(&self) -> bool {
        self.primary_phy() == 3 || self.secondary_phy() == 3
    }
}

/// Everything the reader thread can deliver.
#[derive(Debug, Clone)]
pub enum Event {
    Adv(Box<AdvReport>),
    /// Response to a host command.
    Response {
        cmd: u8,
        status: Status,
        #[allow(dead_code, reason = "Preserve the raw command header alongside the combined payload")]
        data: [u8; CMD_DATA_MAX],
        payload: Vec<u8>,
    },
    /// Device-to-host event with bit 7 of the status byte set (GATT discovery
    /// sub-types, GPIO edges, notifications).
    Spontaneous {
        cmd: u8,
        sub: u8,
        #[allow(dead_code, reason = "Preserve the raw event header alongside the combined payload")]
        data: [u8; CMD_DATA_MAX],
        payload: Vec<u8>,
    },
    /// PRNT: human readable diagnostic string from the firmware.
    Debug(String),
}

/// Host requests use the short `[CMD_ID][parameters...][CRC16 LE]` format.
pub fn build_command(cmd: Cmd, _data: [u8; CMD_DATA_MAX], payload: &[u8]) -> Vec<u8> {
    let mut frame = Vec::with_capacity(3 + payload.len());
    frame.push(cmd as u8);
    frame.extend_from_slice(payload);
    let crc = crc16_arc(&frame);
    frame.push((crc & 0xFF) as u8);
    frame.push((crc >> 8) as u8);
    frame
}

/// SCAN flags byte.
pub struct ScanFlags {
    pub own_addr_type: u8, // 0 public, 1 random, 2/3 RPA
    pub discard_random: bool,
    pub discard_rpa: bool,
    pub dup_filter: bool,
    pub active: bool,
    pub phy_coded: bool,
    pub phy_1m: bool,
}

impl ScanFlags {
    pub fn byte(&self) -> u8 {
        ((self.own_addr_type & 0x3) << 6)
            | ((self.discard_random as u8) << 5)
            | ((self.discard_rpa as u8) << 4)
            | ((self.dup_filter as u8) << 3)
            | ((self.active as u8) << 2)
            | ((self.phy_coded as u8) << 1)
            | (self.phy_1m as u8)
    }
}

/// Build the SCAN command. `window_*` are BLE window units (0.625 ms);
/// 0xFFFF disables a PHY without touching the other one.
pub fn scan_command(flags: &ScanFlags, window_1m: u16, window_coded: u16) -> Vec<u8> {
    if window_coded == 0 || window_coded == window_1m {
        // Legacy short form: both PHYs share the window.
        build_command(
            Cmd::Scan,
            [0; CMD_DATA_MAX],
            &[flags.byte(), (window_1m & 0xFF) as u8, (window_1m >> 8) as u8],
        )
    } else {
        build_command(
            Cmd::Scan,
            [0; CMD_DATA_MAX],
            &[
                flags.byte(),
                (window_1m & 0xFF) as u8,
                (window_1m >> 8) as u8,
                (window_coded & 0xFF) as u8,
                (window_coded >> 8) as u8,
            ],
        )
    }
}

/// Stop scanning (both PHY bits cleared).
pub fn stop_scan_command() -> Vec<u8> {
    build_command(Cmd::Scan, [0; CMD_DATA_MAX], &[0x00, 0x00, 0x00])
}

/// Add a whitelist (0x02) or blacklist (0x03) entry: 1 to 6 bytes, MAC prefix
/// or full address, little endian on the wire.
pub fn mac_list_command(whitelist: bool, mac: &[u8]) -> Vec<u8> {
    let cmd = if whitelist { Cmd::Wmac } else { Cmd::Bmac };
    let len = mac.len().min(CMD_DATA_MAX);
    build_command(cmd, [0; CMD_DATA_MAX], &mac[..len])
}

pub fn clear_mac_list_command() -> Vec<u8> {
    build_command(Cmd::Clrm, [0; CMD_DATA_MAX], &[])
}

/// GPIO op codes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
#[allow(dead_code, reason = "Complete firmware GPIO operations, not yet exposed by the gateway")]
pub enum GpioOp {
    StatusQuery = 0,
    ReadLevel = 1,
    WriteLevel = 2,
    ToggleLevel = 3,
    Configure = 4,
    AnalogRead = 7,
    SetRgb = 8,
}

/// Build a GPIO command: `[op, pin_id, ...]`.
#[allow(dead_code, reason = "Firmware GPIO command builder retained for protocol support")]
pub fn gpio_command(op: GpioOp, pin: u8, extra: &[u8]) -> Vec<u8> {
    let mut payload = Vec::with_capacity(2 + extra.len());
    payload.push(op as u8);
    payload.push(pin);
    payload.extend_from_slice(extra);
    build_command(Cmd::Gpio, [0; CMD_DATA_MAX], &payload)
}

/// Pull mode of GPIO op 4 (configure).
#[allow(dead_code, reason = "Firmware GPIO configuration value retained for protocol support")]
pub const GPIO_PULL_FLOAT: u8 = 0;
#[allow(dead_code, reason = "Firmware GPIO configuration value retained for protocol support")]
pub const GPIO_PULL_UP: u8 = 1;
#[allow(dead_code, reason = "Firmware GPIO configuration value retained for protocol support")]
pub const GPIO_PULL_DOWN: u8 = 2;

/// GPIOEVT sub-operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
#[allow(dead_code, reason = "The gateway queries GPIO events but retains all firmware operations")]
pub enum GpioEvtOp {
    Query = 0,
    Enable = 1,
    Disable = 2,
    DisableAll = 3,
}

pub fn gpio_evt_command(op: GpioEvtOp, pin: u8) -> Vec<u8> {
    let payload = match op {
        GpioEvtOp::Query | GpioEvtOp::DisableAll => vec![op as u8],
        GpioEvtOp::Enable | GpioEvtOp::Disable => vec![op as u8, pin],
    };
    build_command(Cmd::GpioEvt, [0; CMD_DATA_MAX], &payload)
}

/// CONN (GATT central) op codes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
#[allow(dead_code, reason = "Retain the optional firmware pairing operation")]
pub enum ConnOp {
    StatusQuery = 0,
    Open1M = 1,
    OpenCoded = 2,
    Disconnect = 3,
    CancelOpen = 4,
    DiscoverServices = 5,
    ReadCharacteristic = 6,
    WriteCharacteristic = 7,
    ReadDescriptor = 8,
    WriteDescriptor = 9,
    ExchangeMtu = 10,
    Pair = 11,
    Unpair = 12,
    Subscribe = 13,
}

/// Connection state reported by CONN op 0-4 responses.
#[allow(dead_code, reason = "Firmware GATT state names retained for protocol support")]
pub fn conn_state_name(state: u8) -> &'static str {
    match state {
        0 => "idle",
        1 => "connecting",
        2 => "connected",
        _ => "unknown",
    }
}

#[allow(dead_code, reason = "Firmware GATT command builder retained for protocol support")]
pub fn conn_open_command(addr_type: u8, mac: &[u8; 6], coded: bool) -> Vec<u8> {
    let mut payload = Vec::with_capacity(7);
    payload.push(addr_type);
    payload.extend_from_slice(mac);
    build_command(
        Cmd::Conn,
        [0; CMD_DATA_MAX],
        &{
            let mut framed = vec![if coded { ConnOp::OpenCoded } else { ConnOp::Open1M } as u8];
            framed.extend_from_slice(&payload);
            framed
        },
    )
}

pub fn conn_open_managed_command(addr_type: u8, mac: &[u8; 6], coded: bool) -> Vec<u8> {
    let mut payload = vec![if coded { ConnOp::OpenCoded } else { ConnOp::Open1M } as u8, addr_type];
    payload.extend_from_slice(mac);
    payload.push(1);
    build_command(Cmd::Conn, [0; CMD_DATA_MAX], &payload)
}

/// Read a characteristic: `[op, reserved_zero, handle_lo, handle_hi]`.
#[allow(dead_code, reason = "Firmware GATT command builder retained for protocol support")]
pub fn conn_read_command(handle: u16) -> Vec<u8> {
    build_command(
        Cmd::Conn,
        [0; CMD_DATA_MAX],
        &[
            ConnOp::ReadCharacteristic as u8,
            0,
            (handle & 0xFF) as u8,
            (handle >> 8) as u8,
        ],
    )
}

/// Write a characteristic: `[op, reserved_zero, handle_lo, handle_hi, len, data...]`.
#[allow(dead_code, reason = "Firmware GATT command builder retained for protocol support")]
pub fn conn_write_command(handle: u16, value: &[u8]) -> Result<Vec<u8>, String> {
    if value.len() > 56 { return Err("CONN writes carry at most 56 bytes".into()); }
    let mut payload = vec![
        ConnOp::WriteCharacteristic as u8,
        0,
        (handle & 0xFF) as u8,
        (handle >> 8) as u8,
        value.len() as u8,
    ];
    payload.extend_from_slice(value);
    Ok(build_command(Cmd::Conn, [0; CMD_DATA_MAX], &payload))
}

/// ATT write without response: `[handle_lo, handle_hi, len, data...]`.
#[allow(dead_code, reason = "Firmware ATT command builder retained for protocol support")]
pub fn tx_data_command(handle: u16, value: &[u8]) -> Result<Vec<u8>, String> {
    if value.len() > 58 { return Err("TXDATA writes carry at most 58 bytes".into()); }
    let mut payload = vec![
        (handle & 0xFF) as u8,
        (handle >> 8) as u8,
        value.len() as u8,
    ];
    payload.extend_from_slice(value);
    Ok(build_command(Cmd::TxData, [0; CMD_DATA_MAX], &payload))
}

/// Incremental frame parser: feeds bytes, yields complete frames.
pub struct FrameParser {
    buffer: Vec<u8>,
}

impl Default for FrameParser {
    fn default() -> Self {
        FrameParser { buffer: Vec::new() }
    }
}

impl FrameParser {
    pub fn push(&mut self, bytes: &[u8]) {
        self.buffer.extend_from_slice(bytes);
    }

    /// Returns the next complete, CRC-checked frame (without the trailing
    /// CRC). The fixed part of a frame is 11 bytes (payload_len, rssi/cmd,
    /// event/status, addr/len, phy or 0xFF, 6-byte data field), followed by the
    /// payload and the 2-byte CRC: `adv2uart.py` describes it as "11 bytes +
    /// crc16".
    pub fn next_frame(&mut self) -> Option<Vec<u8>> {
        const HEADER: usize = 11;
        const CRC: usize = 2;
        loop {
            if self.buffer.len() < HEADER + CRC {
                return None;
            }
            let payload_len = self.buffer[0] as usize;
            let total = HEADER + payload_len + CRC;
            if payload_len > ADV_DATA_MAX {
                // Nonsense length: resynchronise by dropping one byte.
                log::warn!("link: dropping a byte, implausible payload length {payload_len}");
                self.buffer.remove(0);
                continue;
            }
            if self.buffer.len() < total {
                return None;
            }
            let frame: Vec<u8> = self.buffer.drain(..total).collect();
            let crc = (frame[total - 2] as u16) | ((frame[total - 1] as u16) << 8);
            if crc != crc16_arc(&frame[..total - 2]) {
                log::warn!("link: CRC mismatch, dropping a byte to resynchronise");
                // Put the frame back without its first byte, keeping the bytes
                // that were NOT consumed at the end of the buffer.
                let mut restored = frame[1..].to_vec();
                restored.extend_from_slice(&self.buffer);
                self.buffer = restored;
                continue;
            }
            return Some(frame[..total - 2].to_vec());
        }
    }
}

/// Decode a CRC-checked frame into an event. The frame has no trailing CRC:
/// 11 bytes of header plus `payload_len` bytes of payload.
pub fn decode_frame(frame: &[u8]) -> Option<Event> {
    if frame.len() < 11 {
        return None;
    }
    let payload_len = frame[0] as usize;
    let cmd_or_rssi = frame[1];
    let status_or_event = frame[2];
    let data_len = frame[3];
    let phy_or_ff = frame[4];
    let mut data = [0u8; CMD_DATA_MAX];
    data.copy_from_slice(&frame[5..11]);
    let payload = if frame.len() > 11 {
        let available = frame.len() - 11;
        let wanted = payload_len.min(available);
        frame[11..11 + wanted].to_vec()
    } else {
        Vec::new()
    };

    if phy_or_ff == 0xFF {
        // Command response or spontaneous device-to-host event.
        let cmd = cmd_or_rssi;
        if cmd == Cmd::Prnt as u8 {
            return Some(Event::Debug(
                String::from_utf8_lossy(&payload)
                    .trim_end_matches('\0')
                    .to_string(),
            ));
        }
        if status_or_event & 0x80 != 0 || (cmd == Cmd::RxData as u8 && matches!(status_or_event, 0x1B | 0x1D)) {
            let mut combined = data.to_vec();
            combined.extend_from_slice(&payload);
            combined.truncate(data_len as usize);
            return Some(Event::Spontaneous {
                cmd,
                sub: status_or_event & 0x7F,
                data,
                payload: combined,
            });
        }
        return Some(Event::Response {
            cmd,
            status: if matches!(Cmd::from_u8(cmd), Some(Cmd::Info | Cmd::Version | Cmd::Scan | Cmd::Clrm | Cmd::Wmac | Cmd::Bmac)) {
                Status::Metadata(status_or_event)
            } else {
                Status::from_u8(status_or_event)
            },
            data,
            payload: {
                // The data field is part of the response payload for GPIO etc.:
                // expose it to the caller as well.
                let mut all = Vec::with_capacity(6 + payload.len());
                all.extend_from_slice(&data);
                all.extend_from_slice(&payload);
                all.truncate((data_len as usize).min(all.len()));
                all
            },
        });
    }

    Some(Event::Adv(Box::new(AdvReport {
        rssi: cmd_or_rssi as i8,
        event_type: status_or_event,
        addr_type: data_len & 0x0F,
        directed: (data_len >> 4) & 1 != 0,
        phys: phy_or_ff,
        mac: data,
        data: payload,
    })))
}

/// The serial port, opened in raw mode. USB CDC ignores the baud rate; it is
/// configured anyway because some stacks need it to open the device.
pub struct SerialPort {
    file: std::fs::File,
}

impl SerialPort {
    pub fn open(path: &str, baudrate: u32, reset_on_open: bool) -> Result<SerialPort, String> {
        let file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open(path)
            .map_err(|e| format!("{path}: {e}"))?;
        let fd = file.as_raw_fd();
        if unsafe { libc::flock(fd, libc::LOCK_EX | libc::LOCK_NB) } != 0 {
            return Err(format!("{path}: serial port already owned or lock unavailable: {}; stop the gateway service before foreground diagnostics", std::io::Error::last_os_error()));
        }
        configure_raw(fd, baudrate)?;
        if reset_on_open {
            // A DTR/RTS pulse resets the ESP32-C3; the firmware keeps them low
            // otherwise, so a running module is not disturbed.
            set_modem_bits(fd, false, true)?;
            std::thread::sleep(Duration::from_millis(120));
            set_modem_bits(fd, false, false)?;
        }
        Ok(SerialPort { file })
    }

    pub fn as_raw_fd(&self) -> RawFd {
        self.file.as_raw_fd()
    }

    #[cfg(unix)]
    pub fn try_clone(&self) -> Result<SerialPort, String> {
        self.file
            .try_clone()
            .map(|file| SerialPort { file })
            .map_err(|e| e.to_string())
    }

    pub fn write_all(&mut self, bytes: &[u8]) -> Result<(), String> {
        self.file.write_all(bytes).map_err(|e| e.to_string())?;
        crate::logger::tx(bytes);
        Ok(())
    }

    pub fn read(&mut self, buffer: &mut [u8]) -> Result<usize, String> {
        self.file.read(buffer).map_err(|e| e.to_string())
    }
}

fn speed_constant(baudrate: u32) -> libc::speed_t {
    match baudrate {
        9600 => libc::B9600,
        19200 => libc::B19200,
        38400 => libc::B38400,
        57600 => libc::B57600,
        115200 => libc::B115200,
        230400 => libc::B230400,
        460800 => libc::B460800,
        921600 => libc::B921600,
        1000000 => libc::B1000000,
        2000000 => libc::B2000000,
        _ => libc::B115200,
    }
}

fn configure_raw(fd: RawFd, baudrate: u32) -> Result<(), String> {
    unsafe {
        let mut termios: libc::termios = std::mem::zeroed();
        if libc::tcgetattr(fd, &mut termios) != 0 {
            return Err(format!(
                "tcgetattr: {}",
                std::io::Error::last_os_error()
            ));
        }
        libc::cfmakeraw(&mut termios);
        libc::cfsetispeed(&mut termios, speed_constant(baudrate));
        libc::cfsetospeed(&mut termios, speed_constant(baudrate));
        termios.c_cflag |= libc::CLOCAL | libc::CREAD;
        termios.c_cflag &= !(libc::PARENB | libc::CSTOPB | libc::CSIZE);
        termios.c_cflag |= libc::CS8;
        termios.c_cc[libc::VMIN] = 1;
        termios.c_cc[libc::VTIME] = 1; // 100 ms read timeout
        if libc::tcsetattr(fd, libc::TCSANOW, &termios) != 0 {
            return Err(format!(
                "tcsetattr: {}",
                std::io::Error::last_os_error()
            ));
        }
    }
    Ok(())
}

fn set_modem_bits(fd: RawFd, dtr: bool, rts: bool) -> Result<(), String> {
    unsafe {
        let mut flags: libc::c_int = 0;
        if libc::ioctl(fd, libc::TIOCMGET, &mut flags) != 0 {
            return Err(format!("TIOCMGET: {}", std::io::Error::last_os_error()));
        }
        let mut set = flags;
        set &= !(libc::TIOCM_DTR | libc::TIOCM_RTS);
        if dtr {
            set |= libc::TIOCM_DTR;
        }
        if rts {
            set |= libc::TIOCM_RTS;
        }
        if libc::ioctl(fd, libc::TIOCMSET, &set) != 0 {
            return Err(format!("TIOCMSET: {}", std::io::Error::last_os_error()));
        }
    }
    Ok(())
}

/// Reader thread: pushes parsed events into a channel. The `FrameParser`
/// resynchronises after a CRC error or a truncated packet, which is what the
/// firmware does on its side too.
pub fn spawn_reader(mut port: SerialPort, stopped: Arc<AtomicBool>) -> Receiver<Event> {
    let (sender, receiver) = std::sync::mpsc::sync_channel(1024);
    std::thread::Builder::new()
        .name("ble-link".into())
        .spawn(move || {
            let mut parser = FrameParser::default();
            let mut buffer = [0u8; 1024];
            while !stopped.load(Ordering::Relaxed) {
                let mut descriptor = libc::pollfd { fd: port.as_raw_fd(), events: libc::POLLIN, revents: 0 };
                let ready = unsafe { libc::poll(&mut descriptor, 1, 100) };
                if ready == 0 {
                    continue;
                }
                if ready < 0 {
                    if std::io::Error::last_os_error().kind() == std::io::ErrorKind::Interrupted {
                        continue;
                    }
                    break;
                }
                if descriptor.revents & (libc::POLLERR | libc::POLLHUP | libc::POLLNVAL) != 0 {
                    break;
                }
                match port.read(&mut buffer) {
                    Ok(0) => break,
                    Ok(count) => {
                        crate::logger::rx(&buffer[..count]);
                        parser.push(&buffer[..count]);
                        while let Some(frame) = parser.next_frame() {
                            if let Some(event) = decode_frame(&frame) {
                                if let Event::Adv(report) = &event {
                                    crate::logger::phy(report, "rx", "crc_ok", "pending");
                                    log::trace!(
                                        "adv {} rssi={} {} event=0x{:02X} len={}",
                                        report.mac_string(),
                                        report.rssi,
                                        report.phy_summary(),
                                        report.event_type,
                                        report.data.len()
                                    );
                                }
                                if sender.send(event).is_err() {
                                    return;
                                }
                            }
                        }
                    }
                    Err(error) => {
                        log::warn!("link: read failed: {error}");
                        break;
                    }
                }
            }
        })
        .expect("cannot spawn the link reader thread");
    receiver
}

/// A request/response helper.
///
/// The serial port is opened once and cloned: the reader thread owns one handle
/// and the daemon the other, so reads never block writes. Responses are matched
/// by command id; events that arrive while waiting are kept in `pending` and
/// handed back to the caller, so nothing is lost.
pub struct Link {
    port: SerialPort,
    events: Receiver<Event>,
    pub pending: Vec<Event>,
    stopped: Arc<AtomicBool>,
}

impl Drop for Link {
    fn drop(&mut self) {
        self.stopped.store(true, Ordering::Relaxed);
    }
}

impl Link {
    pub fn send(&mut self, frame: &[u8]) -> Result<(), String> {
        self.port.write_all(frame)
    }

    /// Open the port and start the reader thread. `reset_on_open` pulses DTR/RTS
    /// (the ESP32-C3 resets on that pulse).
    pub fn open(
        path: &str,
        baudrate: u32,
        reset_on_open: bool,
    ) -> Result<Link, String> {
        let port = SerialPort::open(path, baudrate, reset_on_open)?;
        let reader_port = port.try_clone()?;
        let stopped = Arc::new(AtomicBool::new(false));
        let events = spawn_reader(reader_port, Arc::clone(&stopped));
        Ok(Link {
            port,
            events,
            pending: Vec::new(),
            stopped,
        })
    }

    /// Take the next event, if one is already queued.
    #[allow(dead_code, reason = "Nonblocking serial API retained alongside the timed next method")]
    pub fn try_next(&mut self) -> Option<Event> {
        if !self.pending.is_empty() {
            return Some(self.pending.remove(0));
        }
        self.events.try_recv().ok()
    }

    /// Block for the next event (advertisements, spontaneous frames).
    pub fn next(&mut self, timeout: Duration) -> Result<Option<Event>, String> {
        if !self.pending.is_empty() {
            return Ok(Some(self.pending.remove(0)));
        }
        match self.events.recv_timeout(timeout) {
            Ok(event) => Ok(Some(event)),
            Err(RecvTimeoutError::Timeout) => Ok(None),
            Err(RecvTimeoutError::Disconnected) => Err("serial reader disconnected".into()),
        }
    }

    /// Send a command and wait for its response, collecting advertisements
    /// meanwhile.
    pub fn request(
        &mut self,
        frame: &[u8],
        cmd: Cmd,
        timeout: Duration,
    ) -> Result<(Status, Vec<u8>), String> {
        self.port.write_all(frame)?;
        let deadline = Instant::now() + timeout;
        loop {
            let now = Instant::now();
            if now >= deadline {
                return Err(format!("{}: no response within {:?}", cmd.name(), timeout));
            }
            match self.events.recv_timeout(deadline - now) {
                Ok(Event::Response { cmd: reply, status, payload, .. }) if reply == cmd as u8 => {
                    return Ok((status, payload))
                }
                Ok(Event::Debug(text)) => log::debug!("firmware: {text}"),
                Ok(other) => self.pending.push(other),
                Err(RecvTimeoutError::Timeout) => {
                    return Err(format!("{}: timed out", cmd.name()))
                }
                Err(RecvTimeoutError::Disconnected) => {
                    return Err("link: reader thread stopped".into())
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn phy_nibbles_distinguish_1m_2m_coded_and_unknown() {
        for (raw, primary, secondary, one_m, coded) in [
            (0x01, "1M", "none", true, false),
            (0x03, "Coded", "none", false, true),
            (0x11, "1M", "1M", true, false),
            (0x21, "1M", "2M", true, false),
            (0x31, "1M", "Coded", true, true),
            (0x33, "Coded", "Coded", false, true),
            (0x44, "unknown", "unknown", false, false),
        ] {
            let frame = [0, 200, 0, 0, raw, 1, 2, 3, 4, 5, 6];
            let Some(Event::Adv(report)) = decode_frame(&frame) else { panic!("advertisement expected") };
            assert_eq!(report.primary_phy(), raw & 15);
            assert_eq!(report.secondary_phy(), raw >> 4);
            assert_eq!(report.phy_summary(), format!("phy_raw=0x{raw:02X} primary={primary} secondary={secondary}"));
            assert_eq!(report.hint_1m(), one_m);
            assert_eq!(report.hint_coded(), coded);
        }
    }

    #[test]
    fn crc_matches_the_firmware_implementation() {
        // CRC-16/MODBUS check value (init 0xFFFF, reflected 0xA001).
        assert_eq!(crc16_arc(b"123456789"), 0x4B37);
        assert_eq!(crc16_arc(&[]), 0xFFFF);
        // The property adv2uart.py relies on: a frame with its own little
        // endian CRC appended checks out to zero.
        let mut frame = build_command(Cmd::Info, [0; CMD_DATA_MAX], &[]);
        assert_eq!(crc16_arc(&frame), 0);
        frame.push(0x01);
        assert_ne!(crc16_arc(&frame), 0);
    }

    #[test]
    fn scan_command_layout() {
        let flags = ScanFlags {
            own_addr_type: 0,
            discard_random: false,
            discard_rpa: false,
            dup_filter: true,
            active: false,
            phy_coded: true,
            phy_1m: true,
        };
        let frame = scan_command(&flags, 320, 320);
        assert_eq!(&frame[..4], &[0x01, 0x0B, 0x40, 0x01]);
        assert_eq!(frame.len(), 6);
        assert_eq!(crc16_arc(&frame), 0);

        let frame = scan_command(&flags, 320, 64);
        assert_eq!(&frame[..6], &[0x01, 0x0B, 0x40, 0x01, 0x40, 0x00]);
        assert_eq!(frame.len(), 8);
    }

    #[test]
    fn empty_scan_stops() {
        assert_eq!(&stop_scan_command()[..4], &[1, 0, 0, 0]);
        assert_eq!(build_command(Cmd::Info, [0; 6], &[]), vec![0, 0xBF, 0x40]);
    }

    #[test]
    fn mac_list_entry_is_little_endian_prefix() {
        let frame = mac_list_command(false, &[0x30, 0xF9, 0x4B]);
        assert_eq!(&frame[..4], &[3, 0x30, 0xF9, 0x4B]);
    }

    #[test]
    fn gatt_handles_follow_the_reserved_byte_without_value_padding() {
        let read = conn_read_command(0x1234);
        assert_eq!(&read[..read.len() - 2], &[0x0C, 6, 0, 0x34, 0x12]);
        assert_eq!(crc16_arc(&read), 0);
        let write = conn_write_command(0x1234, &[0xAA, 0xBB]).unwrap();
        assert_eq!(&write[..write.len() - 2], &[0x0C, 7, 0, 0x34, 0x12, 2, 0xAA, 0xBB]);
        assert_eq!(crc16_arc(&write), 0);
        let maximum = conn_write_command(0xFF01, &[0xAB; 56]).unwrap();
        assert_eq!(maximum.len(), 64);
        assert_eq!(maximum[5], 56);
        assert_eq!(&maximum[6..62], &[0xAB; 56]);
        assert_eq!(crc16_arc(&maximum), 0);
        let maximum = tx_data_command(0xFF01, &[0xCD; 58]).unwrap();
        assert_eq!(maximum.len(), 64);
        assert_eq!(maximum[3], 58);
        assert_eq!(&maximum[4..62], &[0xCD; 58]);
        assert_eq!(crc16_arc(&maximum), 0);
        assert!(conn_write_command(1, &[0; 57]).is_err());
        assert!(tx_data_command(1, &[0; 59]).is_err());
    }

    #[test]
    fn gpio_and_gatt_protocol_helpers_preserve_wire_layout() {
        for (frame, expected) in [
            (gpio_command(GpioOp::Configure, 9, &[GPIO_PULL_UP]), vec![6, 4, 9, 1]),
            (gpio_evt_command(GpioEvtOp::Query, 9), vec![0x10, 0]),
            (gpio_evt_command(GpioEvtOp::Enable, 9), vec![0x10, 1, 9]),
            (gpio_evt_command(GpioEvtOp::Disable, 9), vec![0x10, 2, 9]),
            (gpio_evt_command(GpioEvtOp::DisableAll, 9), vec![0x10, 3]),
            (conn_open_command(1, &[1, 2, 3, 4, 5, 6], false), vec![0x0C, 1, 1, 1, 2, 3, 4, 5, 6]),
            (conn_open_command(1, &[1, 2, 3, 4, 5, 6], true), vec![0x0C, 2, 1, 1, 2, 3, 4, 5, 6]),
            (conn_open_managed_command(1, &[1, 2, 3, 4, 5, 6], true), vec![0x0C, 2, 1, 1, 2, 3, 4, 5, 6, 1]),
            (tx_data_command(0x1234, &[0xAA, 0xBB]).unwrap(), vec![0x0D, 0x34, 0x12, 2, 0xAA, 0xBB]),
        ] {
            assert_eq!(&frame[..frame.len() - 2], expected);
            assert_eq!(crc16_arc(&frame), 0);
        }
    }

    #[test]
    fn command_events_retain_raw_header_and_combined_payload() {
        for status in [0, 0x80] {
            let frame = [2, Cmd::Gpio as u8, status, 8, 0xFF, 1, 2, 3, 4, 5, 6, 7, 8];
            let (data, payload) = match decode_frame(&frame).unwrap() {
                Event::Response { data, payload, .. } if status == 0 => (data, payload),
                Event::Spontaneous { data, payload, .. } if status == 0x80 => (data, payload),
                other => panic!("unexpected command event: {other:?}"),
            };
            assert_eq!(data, [1, 2, 3, 4, 5, 6]);
            assert_eq!(payload, [1, 2, 3, 4, 5, 6, 7, 8]);
        }
    }

    #[test]
    fn serial_port_has_one_owner_until_closed() {
        use std::os::fd::FromRawFd;
        let mut master = -1;
        let mut slave = -1;
        assert_eq!(unsafe { libc::openpty(&mut master, &mut slave, std::ptr::null_mut(), std::ptr::null(), std::ptr::null()) }, 0);
        let _master = unsafe { std::fs::File::from_raw_fd(master) };
        let _slave = unsafe { std::fs::File::from_raw_fd(slave) };
        let path = format!("/proc/self/fd/{slave}");
        let owner = SerialPort::open(&path, 115200, false).unwrap();
        assert!(SerialPort::open(&path, 115200, false).is_err());
        drop(owner);
        assert!(SerialPort::open(&path, 115200, false).is_ok());
    }

    #[test]
    fn parser_roundtrip_and_resync() {
        let mut parser = FrameParser::default();
        let mut frame = vec![0, 0, 2, 6, 0xFF, 1, 2, 3, 4, 5, 6];
        frame.extend_from_slice(&crc16_arc(&frame).to_le_bytes());
        assert_eq!(frame.len(), 13, "11-byte header + CRC");
        parser.push(&frame);
        assert_eq!(parser.next_frame().unwrap().len(), 11);
        assert!(parser.next_frame().is_none());

        // A corrupted prefix must not stop the parser: it resynchronises.
        parser.push(&[0xFF, 0x00, 0x01]);
        parser.push(&frame);
        assert!(parser.next_frame().is_some());
        assert!(parser.next_frame().is_none());
    }

    #[test]
    fn decodes_an_advertisement_report() {
        // payload_len=1, rssi=-40, event_type=3, addr=00, phy=0x01 -> 1M
        let mut frame = vec![1, (-40i8) as u8, 3, 0x00, 0x01];
        frame.extend_from_slice(&[0x1D, 0x8A, 0x3B, 0x34, 0x2D, 0x58]);
        frame.push(0xAB);
        let crc = crc16_arc(&frame);
        frame.push((crc & 0xFF) as u8);
        frame.push((crc >> 8) as u8);

        let mut parser = FrameParser::default();
        parser.push(&frame);
        let decoded = decode_frame(&parser.next_frame().unwrap()).unwrap();
        match decoded {
            Event::Adv(report) => {
                assert_eq!(report.rssi, -40);
                // On-wire order is little endian: the display order is reversed.
                assert_eq!(report.mac_string(), "582D343B8A1D");
                assert_eq!(report.mac_colon(), "58:2D:34:3B:8A:1D");
                assert!(report.hint_1m());
                assert_eq!(report.data, vec![0xAB]);
            }
            other => panic!("expected an advertisement, got {other:?}"),
        }
    }

    #[test]
    fn decodes_a_gpio_edge_event() {
        // payload_len=6, cmd=GPIOEVT, status=0x80|pin, data_len=6, phy=0xFF,
        // then the 6-byte data field and the 6-byte payload
        // (pin, level, 32-bit millisecond timestamp).
        let mut frame = vec![0, Cmd::GpioEvt as u8, 0x80 | 9, 6, 0xFF];
        frame.extend_from_slice(&[9, 1, 0x10, 0x27, 0x00, 0x00]);
        let crc = crc16_arc(&frame);
        frame.push((crc & 0xFF) as u8);
        frame.push((crc >> 8) as u8);
        let mut parser = FrameParser::default();
        parser.push(&frame);
        match decode_frame(&parser.next_frame().unwrap()).unwrap() {
            Event::Spontaneous { cmd, sub, payload, .. } => {
                assert_eq!(cmd, Cmd::GpioEvt as u8);
                assert_eq!(sub & 0x1F, 9, "pin id in the low five bits");
                assert_eq!(payload, vec![9, 1, 0x10, 0x27, 0x00, 0x00]);
            }
            other => panic!("expected a spontaneous event, got {other:?}"),
        }
    }
}
