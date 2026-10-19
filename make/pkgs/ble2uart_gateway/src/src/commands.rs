//! Daemon-owned, bounded firmware transactions. The serial reader remains the
//! only reader; unrelated advertisements are returned to the normal pipeline.

use crate::config::ScannerConfig;
use crate::link::{self, Cmd, ConnOp, Event, Link, ScanFlags, Status};
use serde::Deserialize;
use serde_json::{json, Value};
use std::time::{Duration, Instant};

#[derive(Debug, Deserialize)]
#[serde(tag = "command", rename_all = "kebab-case", deny_unknown_fields)]
pub enum Command {
    Diagnostic {
        name: Diagnostic,
        #[serde(default)]
        pin: u8,
    },
    Gatt {
        mac: String,
        #[serde(default)]
        addr_type: u8,
        #[serde(default)]
        coded: bool,
        operation: GattOperation,
        #[serde(default)]
        handle: u16,
        #[serde(default)]
        value: String,
        #[serde(default = "default_timeout")]
        timeout_ms: u64,
    },
    TxadvStart { phy: u8, interval_units: u16, data: String },
    TxadvStop,
    ScanStart,
    ScanStop,
}

fn default_timeout() -> u64 { 10000 }

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Diagnostic {
    Info, Version, Uart, Rfsdk, Vbat, GpioEvents, GpioStatus, GpioRead,
    AnalogRead, ConnectionStatus, TxadvStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum GattOperation {
    Discover, Read, ReadDescriptor, Write, WriteDescriptor, WriteWithoutResponse,
    Mtu, Unpair,
}

#[derive(Default)]
pub struct Radio {
    pub scanning: bool,
    pub scan_suppressed: bool,
    pub txadv_active: bool,
    pub recovery_required: bool,
    pub gatt_recovery_required: bool,
}

impl Radio {
    pub fn snapshot(&self) -> Value {
        json!({"scanning": self.scanning, "scan_suppressed": self.scan_suppressed,
            "txadv_active": self.txadv_active, "recovery_required": self.recovery_required})
    }
}

pub fn parse(value: Value) -> Result<Command, String> {
    let command: Command = serde_json::from_value(value).map_err(|error| error.to_string())?;
    match &command {
        Command::Gatt { mac, addr_type, operation, handle, value, timeout_ms, .. } => {
            crate::config::parse_mac(mac)?;
            if *addr_type > 1 { return Err("addr_type must be 0 (public) or 1 (random)".into()); }
            if !(100..=30000).contains(timeout_ms) { return Err("timeout_ms must be 100-30000".into()); }
            let bytes = hex_bytes(value, 20)?;
            let needs_handle = matches!(operation, GattOperation::Read | GattOperation::ReadDescriptor |
                GattOperation::Write | GattOperation::WriteDescriptor | GattOperation::WriteWithoutResponse);
            let writes = matches!(operation, GattOperation::Write | GattOperation::WriteDescriptor |
                GattOperation::WriteWithoutResponse);
            if needs_handle != (*handle != 0) { return Err("provide a nonzero handle only for read/write operations".into()); }
            if !writes && !bytes.is_empty() { return Err("value is only allowed for writes".into()); }
            // The current firmware's CONN write length guard uses the high
            // handle byte, not the value length. Do not pad or alter the value.
            if matches!(operation, GattOperation::Write | GattOperation::WriteDescriptor) &&
                usize::from(handle >> 8) > bytes.len() + 1 {
                return Err("this handle/value is rejected by the current firmware CONN length guard; firmware fix required".into());
            }
        }
        Command::TxadvStart { phy, interval_units, data } => {
            if *phy > 2 { return Err("phy must be 0 (legacy 1M), 1 (extended 1M) or 2 (coded)".into()); }
            if *interval_units < 32 { return Err("interval_units must be 32-65535 (0.625 ms units)".into()); }
            hex_bytes(data, 31)?;
        }
        _ => {}
    }
    Ok(command)
}

fn hex_bytes(text: &str, max: usize) -> Result<Vec<u8>, String> {
    // Accept spaces/newlines in pasted hex, but never punctuation or odd nibbles.
    let digits: String = text.chars().filter(|character| !character.is_ascii_whitespace()).collect();
    if !digits.is_ascii() || digits.len() % 2 != 0 || digits.len() / 2 > max {
        return Err(format!("expected hexadecimal byte pairs, at most {max} bytes"));
    }
    (0..digits.len()).step_by(2).map(|index|
        u8::from_str_radix(&digits[index..index + 2], 16).map_err(|_| "invalid hexadecimal data".into())
    ).collect()
}

pub fn scan_frame(scanner: &ScannerConfig) -> Vec<u8> {
    link::scan_command(&ScanFlags {
        own_addr_type: 0,
        discard_random: scanner.discard_random,
        discard_rpa: scanner.discard_rpa,
        dup_filter: scanner.dup_filter,
        active: scanner.active_scan,
        phy_coded: scanner.phy_coded,
        phy_1m: scanner.phy_1m,
    }, scanner.window_1m, scanner.window_coded)
}

fn checked_request(link: &mut Link, frame: &[u8], cmd: Cmd, timeout: Duration) -> Result<(Status, Vec<u8>), String> {
    let (status, payload) = link.request(frame, cmd, timeout)?;
    if !status.is_ok() { return Err(format!("{}: {}", cmd.name(), status.as_str())); }
    Ok((status, payload))
}

pub fn set_scan(link: &mut Link, scanner: Option<&ScannerConfig>, timeout: Duration) -> Result<(), String> {
    let frame = scanner.map(scan_frame).unwrap_or_else(link::stop_scan_command);
    checked_request(link, &frame, Cmd::Scan, timeout).map(|_| ())
}

fn diagnostic(link: &mut Link, name: Diagnostic, pin: u8, timeout: Duration) -> Result<Value, String> {
    let (cmd, parameters) = match name {
        Diagnostic::Info => (Cmd::Info, vec![]),
        Diagnostic::Version => (Cmd::Version, vec![]),
        Diagnostic::Uart => (Cmd::Uart, vec![0]),
        Diagnostic::Rfsdk => (Cmd::Rfsdk, vec![0]),
        Diagnostic::Vbat => (Cmd::Vbat, vec![]),
        Diagnostic::GpioEvents => (Cmd::GpioEvt, vec![0]),
        Diagnostic::GpioStatus => (Cmd::Gpio, vec![0, pin]),
        Diagnostic::GpioRead => (Cmd::Gpio, vec![1, pin]),
        Diagnostic::AnalogRead => (Cmd::Gpio, vec![7, pin]),
        Diagnostic::ConnectionStatus => (Cmd::Conn, vec![0]),
        Diagnostic::TxadvStatus => (Cmd::TxAdv, vec![2]),
    };
    let (status, payload) = checked_request(link, &link::build_command(cmd, [0; 6], &parameters), cmd, timeout)?;
    Ok(json!({"firmware_command": cmd.name(), "status": status.as_str(),
        "metadata": if let Status::Metadata(value) = status { Some(value) } else { None },
        "data": crate::codec::value::hex(&payload)}))
}

struct Session<'a> {
    link: &'a mut Link,
    deferred: Vec<Event>,
    deadline: Instant,
    cancellable: bool,
}

impl Drop for Session<'_> {
    fn drop(&mut self) {
        self.deferred.append(&mut self.link.pending);
        self.link.pending = std::mem::take(&mut self.deferred);
    }
}

impl Session<'_> {
    fn discard_stale_control(&mut self) -> Result<(), String> {
        while let Some(event) = self.link.try_next() {
            self.defer(event)?;
        }
        Ok(())
    }

    fn defer(&mut self, event: Event) -> Result<(), String> {
        match event {
            Event::Adv(_) => self.deferred.push(event),
            Event::Spontaneous { cmd, .. } if cmd != Cmd::Conn as u8 => self.deferred.push(event),
            Event::Debug(text) => log::debug!("firmware: {text}"),
            other => log::debug!("GATT: unrelated event {other:?}"),
        }
        if self.deferred.len() > 1024 { return Err("too many unrelated events during GATT transaction".into()); }
        Ok(())
    }

    fn send(&mut self, op: ConnOp, parameters: &[u8]) -> Result<(), String> {
        let mut payload = vec![op as u8];
        payload.extend_from_slice(parameters);
        self.link.send(&link::build_command(Cmd::Conn, [0; 6], &payload))
    }

    fn wait<T>(&mut self, mut accept: impl FnMut(&Event) -> Option<Result<T, String>>) -> Result<T, String> {
        loop {
            if self.cancellable && crate::STOP_REQUESTED.load(std::sync::atomic::Ordering::Relaxed) {
                return Err("command cancelled: gateway is stopping".into());
            }
            let remaining = self.deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() { return Err("GATT operation timed out".into()); }
            if let Some(event) = self.link.next(remaining.min(Duration::from_millis(100)))? {
                if let Some(result) = accept(&event) { return result; }
                self.defer(event)?;
            }
        }
    }

    fn state(&mut self, expected: Option<u8>) -> Result<u8, String> {
        self.wait(|event| match event {
            Event::Response { cmd: 0x0C, status, payload, .. }
                if payload.len() == 6 && payload[0] <= 2 && payload[1] <= 1 => {
                if !status.is_ok() { Some(Err(format!("CONN: {}", status.as_str()))) }
                else if expected.is_none_or(|state| state == payload[0]) { Some(Ok(payload[0])) }
                else { None }
            }
            _ => None,
        })
    }

    fn operation(&mut self, operation: GattOperation, handle: u16, bytes: &[u8]) -> Result<Value, String> {
        self.discard_stale_control()?;
        match operation {
            GattOperation::Discover => {
                self.send(ConnOp::DiscoverServices, &[])?;
                let mut entries = Vec::new();
                self.wait(|event| match event {
                    Event::Spontaneous { cmd: 0x0C, sub, payload, .. } => {
                        if *sub == 3 { return Some(Ok(())); }
                        if entries.len() >= 512 { return Some(Err("GATT discovery exceeds 512 entries".into())); }
                        entries.push(json!({"type": sub, "data": crate::codec::value::hex(payload)}));
                        None
                    }
                    Event::Response { cmd: 0x0C, status, .. } if !status.is_ok() =>
                        Some(Err(format!("GATT discovery: {}", status.as_str()))),
                    _ => None,
                })?;
                Ok(json!({"entries": entries, "confirmation": "discovery-complete"}))
            }
            GattOperation::Read | GattOperation::ReadDescriptor => {
                let op = if operation == GattOperation::Read { ConnOp::ReadCharacteristic } else { ConnOp::ReadDescriptor };
                self.send(op, &handle.to_le_bytes())?;
                self.wait(|event| match event {
                    Event::Response { cmd: 0x0C, status, payload, .. }
                        if payload.len() >= 3 && payload[..2] == handle.to_le_bytes() &&
                            payload.len() == 3 + usize::from(payload[2]) => {
                        Some(if status.is_ok() {
                            Ok(json!({"handle": handle, "value": crate::codec::value::hex(&payload[3..]), "confirmation": "read-result"}))
                        } else { Err(format!("GATT read: {}", status.as_str())) })
                    }
                    Event::Response { cmd: 0x0C, status, .. } if !status.is_ok() =>
                        Some(Err(format!("GATT read: {}", status.as_str()))),
                    _ => None,
                })
            }
            GattOperation::WriteWithoutResponse => {
                self.link.send(&link::tx_data_command(handle, bytes))?;
                self.wait(|event| match event {
                    Event::Response { cmd: 0x0D, status, payload, .. } => Some(
                        if status.is_ok() && payload.get(3) == Some(&0) {
                            Ok(json!({"confirmation": "stack-accepted", "att_confirmed": false}))
                        } else { Err(format!("TXDATA: {}", status.as_str())) }),
                    _ => None,
                })
            }
            GattOperation::Write | GattOperation::WriteDescriptor => {
                let mut parameters = handle.to_le_bytes().to_vec();
                parameters.push(bytes.len() as u8);
                parameters.extend_from_slice(bytes);
                self.send(if operation == GattOperation::Write { ConnOp::WriteCharacteristic } else { ConnOp::WriteDescriptor }, &parameters)?;
                self.state(Some(2))?;
                Ok(json!({"confirmation": "stack-accepted", "att_confirmed": false,
                    "note": "firmware does not report final ATT write completion to the host"}))
            }
            GattOperation::Mtu => {
                self.send(ConnOp::ExchangeMtu, &[])?;
                self.wait(|event| match event {
                    Event::Response { cmd: 0x0C, status, payload, .. } if payload.len() == 2 && status.is_ok() =>
                        Some(Ok(json!({"mtu": u16::from_le_bytes([payload[0], payload[1]]), "confirmation": "mtu-result"}))),
                    Event::Response { cmd: 0x0C, status, .. } if !status.is_ok() => Some(Err("MTU exchange denied".into())),
                    _ => None,
                })
            }
            GattOperation::Unpair => {
                self.send(ConnOp::Unpair, &[])?;
                self.state(None)?;
                Ok(json!({"confirmation": "stack-accepted", "security_confirmed": false}))
            }
        }
    }
}

pub fn recover_connection(link: &mut Link, timeout: Duration) -> Result<(), String> {
    let mut session = Session { link, deferred: Vec::new(), deadline: Instant::now() + timeout, cancellable: false };
    session.discard_stale_control()?;
    session.send(ConnOp::StatusQuery, &[])?;
    let state = session.state(None)?;
    if state != 0 {
        session.send(if state == 1 { ConnOp::CancelOpen } else { ConnOp::Disconnect }, &[])?;
        session.state(Some(0))?;
    }
    Ok(())
}

fn gatt(link: &mut Link, command: &Command, cleanup_timeout: Duration) -> (Result<Value, String>, bool) {
    let Command::Gatt { mac, addr_type, coded, operation, handle, value, timeout_ms } = command else { unreachable!() };
    let mut address = crate::config::parse_mac(mac).expect("validated MAC");
    address.reverse();
    let bytes = hex_bytes(value, 20).expect("validated hex");
    let mut owns_connection = false;
    let result = {
        let mut session = Session { link, deferred: Vec::new(), deadline: Instant::now() + Duration::from_millis(*timeout_ms), cancellable: true };
        (|| {
            session.discard_stale_control()?;
            session.send(ConnOp::StatusQuery, &[])?;
            if session.state(None)? != 0 { return Err("adapter already has a GATT connection; disconnect it before issuing a transaction".into()); }
            owns_connection = true;
            session.link.send(&link::conn_open_command(*addr_type, &address, *coded))?;
            session.state(Some(2))?;
            session.operation(*operation, *handle, &bytes)
        })()
    };
    if !owns_connection { return (result, false); }
    match recover_connection(link, cleanup_timeout) {
        Ok(()) => (result, false),
        Err(error) => {
            let previous = result.err().map(|error| format!("{error}; ")).unwrap_or_default();
            (Err(format!("{previous}GATT cleanup failed: {error}")), true)
        }
    }
}

pub fn execute(link: &mut Link, radio: &mut Radio, scanner: &ScannerConfig, timeout: Duration, command: &Command) -> Result<Value, String> {
    if matches!(command, Command::ScanStart) {
        return Err("scan-start must be handled with the configured MAC filters".into());
    }
    if matches!(command, Command::Gatt { .. }) && radio.txadv_active {
        return Err("stop TXADV before starting a GATT transaction".into());
    }
    if matches!(command, Command::ScanStop) {
        radio.scan_suppressed = true;
        radio.scanning = false;
        return set_scan(link, None, timeout)
            .map(|_| json!({"confirmation": "scanner-stopped"}));
    }
    let resume = radio.scanning;
    if resume {
        radio.scanning = false;
        if let Err(pause) = set_scan(link, None, timeout) {
            return match set_scan(link, Some(scanner), timeout) {
                Ok(()) => {
                    radio.scanning = true;
                    Err(format!("cannot pause scanner; command not sent: {pause}"))
                }
                Err(restore) => {
                    radio.recovery_required = true;
                    Err(format!("cannot pause scanner: {pause}; cannot restore scanner: {restore}"))
                }
            };
        }
    }
    let result = match command {
        Command::Diagnostic { name, pin } => diagnostic(link, *name, *pin, timeout),
        Command::Gatt { .. } => {
            let (result, uncertain) = gatt(link, command, timeout);
            radio.recovery_required |= uncertain;
            radio.gatt_recovery_required |= uncertain;
            result
        }
        Command::TxadvStart { phy, interval_units, data } => {
            // Suppress automatic scanning even if the start ACK is lost: the
            // adapter may already be transmitting.
            let previous = (radio.scan_suppressed, radio.txadv_active);
            radio.scan_suppressed = true;
            radio.txadv_active = true;
            let bytes = hex_bytes(data, 31)?;
            let mut parameters = vec![1, *phy];
            parameters.extend_from_slice(&interval_units.to_le_bytes());
            parameters.push(bytes.len() as u8);
            parameters.extend_from_slice(&bytes);
            match link.request(&link::build_command(Cmd::TxAdv, [0; 6], &parameters), Cmd::TxAdv, timeout) {
                Ok((status, _)) if status.is_ok() => Ok(json!({"confirmation": "txadv-started"})),
                Ok((status, _)) => {
                    (radio.scan_suppressed, radio.txadv_active) = previous;
                    Err(format!("TXADV: {}", status.as_str()))
                }
                Err(error) => Err(error),
            }
        }
        Command::TxadvStop => {
            checked_request(link, &link::build_command(Cmd::TxAdv, [0; 6], &[0]), Cmd::TxAdv, timeout)
                .map(|_| { radio.txadv_active = false; json!({"confirmation": "txadv-stopped"}) })
        }
        Command::ScanStart | Command::ScanStop => unreachable!(),
    };
    if resume && !radio.scan_suppressed {
        if let Err(error) = set_scan(link, Some(scanner), timeout) {
            radio.recovery_required = true;
            let previous = result.err().map(|error| format!("{error}; ")).unwrap_or_default();
            return Err(format!("{previous}cannot restore scanner: {error}"));
        }
        radio.scanning = true;
    }
    if let Err(error) = &result { log::warn!("firmware command failed: {error}"); }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_commands_before_touching_serial() {
        assert!(parse(json!({"command":"diagnostic","name":"info"})).is_ok());
        for invalid in [
            json!({"command":"diagnostic","name":"reset"}),
            json!({"command":"diagnostic","name":"info","raw":"00"}),
            json!({"command":"gatt","mac":"bad","operation":"read","handle":1}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"read","handle":0}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"read","handle":1,"timeout_ms":30001}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"write","handle":1,"value":"AB".repeat(21)}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"write","handle":0xFF01,"value":"01"}),
            json!({"command":"txadv-start","phy":3,"interval_units":160,"data":""}),
            json!({"command":"txadv-start","phy":0,"interval_units":31,"data":""}),
            json!({"command":"txadv-start","phy":0,"interval_units":160,"data":"AB".repeat(32)}),
            json!({"command":"txadv-start","phy":0,"interval_units":160,"data":"0"}),
        ] { assert!(parse(invalid.clone()).is_err(), "{invalid}"); }
        assert_eq!(hex_bytes("01 ab\nFF", 3).unwrap(), [1, 0xAB, 0xFF]);
    }

    fn response(cmd: u8, status: u8, payload: &[u8]) -> Vec<u8> {
        let mut frame = vec![payload.len().saturating_sub(6) as u8, cmd, status, payload.len() as u8, 0xFF];
        frame.extend_from_slice(&payload[..payload.len().min(6)]);
        frame.resize(11, 0);
        if payload.len() > 6 { frame.extend_from_slice(&payload[6..]); }
        frame.extend_from_slice(&link::crc16_arc(&frame).to_le_bytes());
        frame
    }

    fn run_steps(
        steps: Vec<(Vec<u8>, Vec<Vec<u8>>)>,
        command: Value,
        scanning: bool,
    ) -> (Result<Value, String>, Radio, Vec<Event>) {
        use std::io::{Read, Write};
        use std::os::fd::FromRawFd;
        let mut master_fd = -1;
        let mut slave_fd = -1;
        assert_eq!(unsafe { libc::openpty(&mut master_fd, &mut slave_fd, std::ptr::null_mut(), std::ptr::null(), std::ptr::null()) }, 0);
        let mut master = unsafe { std::fs::File::from_raw_fd(master_fd) };
        let _slave = unsafe { std::fs::File::from_raw_fd(slave_fd) };
        let mut link = Link::open(&format!("/proc/self/fd/{slave_fd}"), 115200, false).unwrap();
        let firmware = std::thread::spawn(move || {
            for (mut expected, replies) in steps {
                expected.extend_from_slice(&link::crc16_arc(&expected).to_le_bytes());
                let mut received = vec![0; expected.len()];
                let mut offset = 0;
                while offset < received.len() {
                    let mut poll = libc::pollfd { fd: master_fd, events: libc::POLLIN, revents: 0 };
                    assert_eq!(unsafe { libc::poll(&mut poll, 1, 3000) }, 1, "missing command {expected:?}");
                    let count = master.read(&mut received[offset..]).unwrap();
                    assert_ne!(count, 0);
                    offset += count;
                }
                assert_eq!(received, expected);
                for reply in replies { master.write_all(&reply).unwrap(); }
            }
            let mut poll = libc::pollfd { fd: master_fd, events: libc::POLLIN, revents: 0 };
            assert_eq!(unsafe { libc::poll(&mut poll, 1, 150) }, 0, "unexpected extra firmware command");
            master
        });
        let mut radio = Radio { scanning, ..Radio::default() };
        let result = execute(&mut link, &mut radio, &ScannerConfig::default(), Duration::from_millis(100), &parse(command).unwrap());
        let _master = firmware.join().unwrap();
        (result, radio, std::mem::take(&mut link.pending))
    }

    fn stop_step() -> (Vec<u8>, Vec<Vec<u8>>) {
        (vec![1, 0, 0, 0], vec![response(1, 0, &[])])
    }

    fn resume_step() -> (Vec<u8>, Vec<Vec<u8>>) {
        let mut frame = scan_frame(&ScannerConfig::default());
        frame.truncate(frame.len() - 2);
        (frame, vec![response(1, 0, &[])])
    }

    #[test]
    fn diagnostics_restore_scan_on_success_denial_and_timeout() {
        for replies in [vec![response(15, 0, &[0x34, 0x12])], vec![response(15, 3, &[])], vec![]] {
            let expected_success = !replies.is_empty() && replies[0][2] == 0;
            let (result, radio, _) = run_steps(vec![stop_step(), (vec![15], replies), resume_step()],
                json!({"command":"diagnostic","name":"vbat"}), true);
            assert_eq!(result.is_ok(), expected_success);
            assert!(radio.scanning);
            assert!(!radio.scan_suppressed);
        }
        let (result, radio, _) = run_steps(vec![(vec![15], vec![response(15, 0, &[])])],
            json!({"command":"diagnostic","name":"vbat"}), false);
        assert!(result.is_ok());
        assert!(!radio.scanning);
    }

    #[test]
    fn txadv_start_and_stop_never_restart_scan() {
        let (result, radio, _) = run_steps(vec![stop_step(),
            (vec![11, 1, 0, 160, 0, 3, 2, 1, 6], vec![response(11, 0, &[1, 0, 160, 0, 3, 0])])],
            json!({"command":"txadv-start","phy":0,"interval_units":160,"data":"020106"}), true);
        assert!(result.is_ok());
        assert!(!radio.scanning);
        assert!(radio.scan_suppressed);
        assert!(radio.txadv_active);
        let (result, radio, _) = run_steps(vec![(vec![11, 0], vec![response(11, 0, &[])])],
            json!({"command":"txadv-stop"}), false);
        assert!(result.is_ok());
        assert!(!radio.scanning);
    }

    #[test]
    fn txadv_lost_ack_stays_off_but_explicit_denial_restores_previous_scan() {
        let start = vec![11, 1, 0, 160, 0, 3, 2, 1, 6];
        let command = json!({"command":"txadv-start","phy":0,"interval_units":160,"data":"020106"});
        let (result, radio, _) = run_steps(vec![stop_step(), (start.clone(), vec![])], command.clone(), true);
        assert!(result.is_err());
        assert!(!radio.scanning);
        assert!(radio.scan_suppressed);
        assert!(radio.txadv_active);
        let (result, radio, _) = run_steps(vec![stop_step(), (start, vec![response(11, 3, &[])]), resume_step()], command, true);
        assert!(result.is_err());
        assert!(radio.scanning);
        assert!(!radio.scan_suppressed);
        assert!(!radio.txadv_active);
    }

    #[test]
    fn gatt_read_waits_for_connection_and_read_result_then_disconnects_and_resumes() {
        let idle = response(12, 0, &[0, 0, 0, 0, 0, 0]);
        let connecting = response(12, 0, &[1, 0, 0, 0, 40, 0]);
        let connected = response(12, 0, &[2, 0, 0, 0, 40, 0]);
        let mut advertisement = vec![0, 196, 0, 0, 1, 6, 5, 4, 3, 2, 1];
        advertisement.extend_from_slice(&link::crc16_arc(&advertisement).to_le_bytes());
        let (result, radio, pending) = run_steps(vec![
            stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 0, 0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA],
                vec![connecting, advertisement, connected.clone(), response(12, 0, &[23, 0])]),
            (vec![12, 6, 0x34, 0x12], vec![connected.clone(), response(12, 0, &[0x34, 0x12, 2, 0xAB, 0xCD])]),
            (vec![12, 0], vec![connected.clone()]),
            (vec![12, 3], vec![connected, idle]),
            resume_step(),
        ], json!({"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"read","handle":4660}), true);
        assert_eq!(result.unwrap()["value"], "ABCD");
        assert!(radio.scanning);
        assert!(!radio.recovery_required);
        assert!(pending.iter().any(|event| matches!(event, Event::Adv(_))));
    }

    #[test]
    fn gatt_timeout_cancels_open_and_restores_scan() {
        let idle = response(12, 0, &[0, 0, 0, 0, 0, 0]);
        let connecting = response(12, 0, &[1, 0, 0, 0, 40, 0]);
        let (result, radio, _) = run_steps(vec![
            stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 1, 6, 5, 4, 3, 2, 1], vec![connecting.clone()]),
            (vec![12, 0], vec![connecting.clone()]),
            (vec![12, 4], vec![connecting, idle]),
            resume_step(),
        ], json!({"command":"gatt","mac":"010203040506","addr_type":1,"operation":"discover","timeout_ms":100}), true);
        assert!(result.unwrap_err().contains("timed out"));
        assert!(radio.scanning);
        assert!(!radio.recovery_required);
    }

    #[test]
    fn gatt_does_not_disconnect_a_preexisting_connection() {
        let (result, radio, _) = run_steps(vec![stop_step(),
            (vec![12, 0], vec![response(12, 0, &[2, 0, 0, 0, 40, 0])]),
            resume_step(),
        ], json!({"command":"gatt","mac":"010203040506","operation":"discover"}), true);
        assert!(result.unwrap_err().contains("already has a GATT connection"));
        assert!(radio.scanning);
    }

    #[test]
    fn scan_restore_failure_is_explicit_and_requests_recovery() {
        let (result, radio, _) = run_steps(vec![stop_step(),
            (vec![15], vec![response(15, 0, &[])]),
            (resume_step().0, vec![]),
        ], json!({"command":"diagnostic","name":"vbat"}), true);
        assert!(result.unwrap_err().contains("cannot restore scanner"));
        assert!(!radio.scanning);
        assert!(radio.recovery_required);
        assert!(!radio.gatt_recovery_required);
    }

    #[test]
    fn failed_pause_does_not_send_command_and_attempts_to_restore_scan() {
        let (result, radio, _) = run_steps(vec![(stop_step().0, vec![]), resume_step()],
            json!({"command":"diagnostic","name":"vbat"}), true);
        assert!(result.unwrap_err().contains("command not sent"));
        assert!(radio.scanning);
    }

    #[test]
    fn gatt_write_reports_only_stack_acceptance_and_uses_unpadded_layout() {
        let idle = response(12, 0, &[0, 0, 0, 0, 0, 0]);
        let connected = response(12, 0, &[2, 0, 0, 0, 40, 0]);
        let (result, radio, _) = run_steps(vec![
            stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 0, 6, 5, 4, 3, 2, 1], vec![connected.clone()]),
            (vec![12, 7, 42, 0, 2, 0xAA, 0xBB], vec![connected.clone()]),
            (vec![12, 0], vec![connected]),
            (vec![12, 3], vec![idle]),
            resume_step(),
        ], json!({"command":"gatt","mac":"010203040506","operation":"write","handle":42,"value":"AABB"}), true);
        let result = result.unwrap();
        assert_eq!(result["confirmation"], "stack-accepted");
        assert_eq!(result["att_confirmed"], false);
        assert!(radio.scanning);
    }
}
