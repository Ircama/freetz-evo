//! Daemon-owned radio arbitration and GATT sessions. The serial reader remains the
//! only reader; unrelated advertisements are returned to the normal pipeline.

use crate::config::ScannerConfig;
use crate::codec::spec::Spec;
use crate::gatt::{self, hex_bytes};
use crate::link::{self, Cmd, Link, ScanFlags, Status};
use serde::Deserialize;
use serde_json::{json, Value};
use std::time::{Duration, Instant};

pub use crate::gatt::recover_connection;

#[derive(Debug, Deserialize)]
#[serde(tag = "command", rename_all = "kebab-case", deny_unknown_fields)]
pub enum Command {
    Diagnostic {
        name: Diagnostic,
        #[serde(default)]
        pin: u8,
    },
    Gatt(gatt::Request),
    GattOpen(gatt::Open),
    GattClose { session: String },
    TxadvStart { phy: u8, interval_units: u16, data: String },
    TxadvStop,
    ScanStart,
    ScanStop,
}

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Diagnostic {
    Info, Version, Uart, Rfsdk, Vbat, GpioEvents, GpioStatus, GpioRead,
    AnalogRead, ConnectionStatus, TxadvStatus,
}

#[derive(Default)]
pub struct Radio {
    pub scanning: bool,
    pub scan_suppressed: bool,
    pub txadv_active: bool,
    pub recovery_required: bool,
    pub gatt_recovery_required: bool,
    gatt: Option<gatt::State>,
    suspended: Option<Suspended>,
    txadv: Option<Txadv>,
    gatt_error: String,
}

impl Radio {
    pub fn has_session(&self) -> bool { self.gatt.is_some() }

    pub fn snapshot(&self) -> Value {
        json!({"scanning": self.scanning, "scan_suppressed": self.scan_suppressed,
            "txadv_active": self.txadv_active, "recovery_required": self.recovery_required,
            "gatt": self.gatt.as_ref().map(gatt::State::snapshot), "gatt_error": self.gatt_error})
    }
}

#[derive(Clone)]
struct Txadv {
    phy: u8,
    interval_units: u16,
    data: Vec<u8>,
}

impl Txadv {
    fn frame(&self) -> Vec<u8> {
        let mut parameters = vec![1, self.phy];
        parameters.extend_from_slice(&self.interval_units.to_le_bytes());
        parameters.push(self.data.len() as u8);
        parameters.extend_from_slice(&self.data);
        link::build_command(Cmd::TxAdv, [0; 6], &parameters)
    }
}

#[derive(Clone)]
struct Suspended {
    scanning: bool,
    scan_suppressed: bool,
    scanner: ScannerConfig,
    txadv: Option<Txadv>,
}

pub fn parse(value: Value) -> Result<Command, String> {
    let command: Command = serde_json::from_value(value).map_err(|error| error.to_string())?;
    match &command {
        Command::Gatt(request) => request.validate()?,
        Command::GattOpen(open) => open.validate()?,
        Command::GattClose { session } => gatt::validate_session(session)?,
        Command::TxadvStart { phy, interval_units, data } => {
            if *phy > 2 { return Err("phy must be 0 (legacy 1M), 1 (extended 1M) or 2 (coded)".into()); }
            if *interval_units < 32 { return Err("interval_units must be 32-65535 (0.625 ms units)".into()); }
            hex_bytes(data, 31)?;
        }
        _ => {}
    }
    Ok(command)
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

fn suspend_radio(link: &mut Link, radio: &mut Radio, scanner: &ScannerConfig, timeout: Duration) -> Result<(), String> {
    let (_, status) = checked_request(link, &link::build_command(Cmd::TxAdv, [0; 6], &[2]), Cmd::TxAdv, timeout)?;
    if status.len() != 6 || status[0] > 3 { return Err("malformed TXADV status; GATT was not opened".into()); }
    let txadv = if status[0] != 0 {
        let saved = radio.txadv.as_ref().filter(|saved| saved.phy + 1 == status[0] &&
            saved.interval_units.to_le_bytes() == status[1..3] && saved.data.len() == usize::from(status[3]))
            .ok_or("active TXADV was not configured by this daemon; stop it explicitly before GATT because its payload cannot be recovered")?;
        Some(saved.clone())
    } else { None };
    radio.txadv_active = txadv.is_some();
    radio.suspended = Some(Suspended { scanning: radio.scanning, scan_suppressed: radio.scan_suppressed,
        scanner: scanner.clone(), txadv });
    if radio.scanning {
        radio.scanning = false;
        set_scan(link, None, timeout)?;
    }
    if radio.txadv_active {
        checked_request(link, &link::build_command(Cmd::TxAdv, [0; 6], &[0]), Cmd::TxAdv, timeout)?;
        radio.txadv_active = false;
    }
    Ok(())
}

pub fn restore_radio(link: &mut Link, radio: &mut Radio, timeout: Duration) -> Result<(), String> {
    let Some(saved) = radio.suspended.clone() else { return Ok(()); };
    if radio.gatt_recovery_required { return Err("cannot restore radio before GATT cleanup".into()); }
    let result = (|| {
        if let Some(txadv) = &saved.txadv {
            radio.txadv_active = true;
            checked_request(link, &txadv.frame(), Cmd::TxAdv, timeout)
                .map_err(|error| format!("cannot restore TXADV: {error}"))?;
        }
        if saved.scanning {
            set_scan(link, Some(&saved.scanner), timeout).map_err(|error| format!("cannot restore scanner: {error}"))?;
            radio.scanning = true;
        }
        radio.scan_suppressed = saved.scan_suppressed;
        radio.suspended = None;
        Ok(())
    })();
    if result.is_err() { radio.recovery_required = true; }
    result
}

fn finish_gatt(link: &mut Link, radio: &mut Radio, timeout: Duration, owns_connection: bool) -> Result<(), String> {
    radio.gatt = None;
    if owns_connection {
        if let Err(error) = recover_connection(link, timeout) {
            radio.recovery_required = true;
            radio.gatt_recovery_required = true;
            let error = format!("GATT cleanup failed: {error}; radio restoration deferred until connection recovery");
            radio.gatt_error = error.clone();
            return Err(error);
        }
    }
    let result = restore_radio(link, radio, timeout);
    if let Err(error) = &result { radio.gatt_error = error.clone(); }
    result
}

pub fn abort_gatt(link: &mut Link, radio: &mut Radio, timeout: Duration, reason: &str) -> Result<(), String> {
    if !radio.has_session() { return Ok(()); }
    radio.gatt_error = reason.into();
    log::warn!("closing GATT session: {reason}");
    finish_gatt(link, radio, timeout, true)
}

pub fn maintain_gatt(link: &mut Link, radio: &mut Radio, timeout: Duration) -> Result<(), String> {
    if radio.gatt.as_ref().is_some_and(|state| Instant::now() >= state.expires) {
        abort_gatt(link, radio, timeout, "GATT session idle timeout expired")?;
    }
    Ok(())
}

pub fn observe_gatt(link: &mut Link, radio: &mut Radio, timeout: Duration, event: &link::Event) -> Result<bool, String> {
    let Some(state) = radio.gatt.as_mut() else { return Ok(false); };
    match state.observe(event) {
        Ok(consumed) => Ok(consumed),
        Err(error) => match abort_gatt(link, radio, timeout, &error) {
            Ok(()) => Err(error),
            Err(cleanup) => Err(format!("{error}; {cleanup}")),
        }
    }
}

fn open_gatt(link: &mut Link, radio: &mut Radio, scanner: &ScannerConfig, timeout: Duration, open: &gatt::Open) -> Result<Value, String> {
    if radio.has_session() { return Err("a GATT session is already active; use its token or close it".into()); }
    let mut state = gatt::State::new(open)?;
    radio.gatt_error.clear();
    if let Err(error) = suspend_radio(link, radio, scanner, timeout) {
        return match restore_radio(link, radio, timeout) {
            Ok(()) => Err(format!("cannot suspend radio; GATT was not opened: {error}")),
            Err(restore) => Err(format!("cannot suspend radio: {error}; {restore}")),
        };
    }
    let (result, owns_connection) = gatt::open(link, &mut state, open);
    match result {
        Ok(result) => { radio.gatt = Some(state); Ok(result) }
        Err(error) => {
            radio.gatt_error = error.clone();
            match finish_gatt(link, radio, timeout, owns_connection) {
                Ok(()) => Err(error),
                Err(cleanup) => Err(format!("{error}; {cleanup}")),
            }
        }
    }
}

fn authorize(radio: &Radio, session: &str) -> Result<(), String> {
    match radio.gatt.as_ref() {
        Some(state) if state.token == session => Ok(()),
        Some(_) => Err("GATT session is owned by another client; token does not match".into()),
        None => Err("GATT session is not active or has expired".into()),
    }
}

pub fn execute(link: &mut Link, radio: &mut Radio, scanner: &ScannerConfig, timeout: Duration, spec: &Spec, command: &Command) -> Result<Value, String> {
    if radio.recovery_required { return Err("radio recovery is required before another command".into()); }
    match command {
        Command::GattOpen(open) => return open_gatt(link, radio, scanner, timeout, open),
        Command::GattClose { session } => {
            authorize(radio, session)?;
            finish_gatt(link, radio, timeout, true)?;
            return Ok(json!({"confirmation": "disconnected"}));
        }
        Command::Gatt(request) => {
            request.validate_spec(spec)?;
            let started = Instant::now();
            if request.session.is_empty() { open_gatt(link, radio, scanner, timeout, &request.open())?; }
            else { authorize(radio, &request.session)?; }
            let state = radio.gatt.as_mut().expect("authorized GATT session");
            let mut bounded = request.clone();
            let remaining = Duration::from_millis(request.timeout_ms).saturating_sub(started.elapsed());
            bounded.timeout_ms = remaining.as_millis() as u64;
            let result = gatt::execute(link, state, &bounded, spec);
            let close = request.session.is_empty() || result.is_err() || request.operation == gatt::Operation::Unpair;
            if close {
                if let Err(error) = &result { radio.gatt_error = error.clone(); log::warn!("GATT operation failed: {error}"); }
                if let Err(cleanup) = finish_gatt(link, radio, timeout, true) {
                    let previous = result.err().map(|error| format!("{error}; ")).unwrap_or_default();
                    return Err(format!("{previous}{cleanup}"));
                }
            }
            return result;
        }
        _ if radio.has_session() => return Err("radio is reserved by an active GATT session; close it before other commands".into()),
        _ => {}
    }
    if matches!(command, Command::ScanStart) {
        return Err("scan-start must be handled with the configured MAC filters".into());
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
        Command::Gatt(_) | Command::GattOpen(_) | Command::GattClose { .. } => unreachable!(),
        Command::TxadvStart { phy, interval_units, data } => {
            // Suppress automatic scanning even if the start ACK is lost: the
            // adapter may already be transmitting.
            let previous = (radio.scan_suppressed, radio.txadv_active, radio.txadv.clone());
            radio.scan_suppressed = true;
            radio.txadv_active = true;
            let bytes = hex_bytes(data, 31)?;
            radio.txadv = Some(Txadv { phy: *phy, interval_units: *interval_units, data: bytes });
            let frame = radio.txadv.as_ref().expect("saved TXADV parameters").frame();
            match link.request(&frame, Cmd::TxAdv, timeout) {
                Ok((status, _)) if status.is_ok() => Ok(json!({"confirmation": "txadv-started"})),
                Ok((status, _)) => {
                    (radio.scan_suppressed, radio.txadv_active, radio.txadv) = previous;
                    Err(format!("TXADV: {}", status.as_str()))
                }
                Err(error) => Err(error),
            }
        }
        Command::TxadvStop => {
            checked_request(link, &link::build_command(Cmd::TxAdv, [0; 6], &[0]), Cmd::TxAdv, timeout)
                .map(|_| { radio.txadv_active = false; radio.txadv = None; json!({"confirmation": "txadv-stopped"}) })
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
    use crate::link::Event;

    #[test]
    fn validates_commands_before_touching_serial() {
        assert!(parse(json!({"command":"diagnostic","name":"info"})).is_ok());
        for invalid in [
            json!({"command":"diagnostic","name":"reset"}),
            json!({"command":"diagnostic","name":"info","raw":"00"}),
            json!({"command":"gatt","mac":"bad","operation":"read","handle":1}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"read","handle":0}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"read","handle":1,"timeout_ms":30001}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"write","handle":1,"value":"AB".repeat(57)}),
            json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"read","handle":1,"uuid":"1F1F"}),
            json!({"command":"gatt","session":"bad","operation":"discover"}),
            json!({"command":"gatt-open","mac":"AABBCCDDEEFF","idle_timeout_ms":0}),
            json!({"command":"gatt-close","session":"bad"}),
            json!({"command":"txadv-start","phy":3,"interval_units":160,"data":""}),
            json!({"command":"txadv-start","phy":0,"interval_units":31,"data":""}),
            json!({"command":"txadv-start","phy":0,"interval_units":160,"data":"AB".repeat(32)}),
            json!({"command":"txadv-start","phy":0,"interval_units":160,"data":"0"}),
        ] { assert!(parse(invalid.clone()).is_err(), "{invalid}"); }
        assert!(parse(json!({"command":"gatt","mac":"AABBCCDDEEFF","operation":"write","handle":0xFF01,"value":"01"})).is_ok());
        assert!(parse(json!({"command":"gatt-open","mac":"AABBCCDDEEFF"})).is_ok());
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
        let result = execute(&mut link, &mut radio, &ScannerConfig::default(), Duration::from_millis(100),
            &Spec::embedded().unwrap(), &parse(command).unwrap());
        let _master = firmware.join().unwrap();
        (result, radio, std::mem::take(&mut link.pending))
    }

    fn stop_step() -> (Vec<u8>, Vec<Vec<u8>>) {
        (vec![1, 0, 0, 0], vec![response(1, 0, &[])])
    }

    fn txadv_idle_step() -> (Vec<u8>, Vec<Vec<u8>>) {
        (vec![11, 2], vec![response(11, 0, &[0; 6])])
    }

    fn mtu_event() -> Vec<u8> { response(12, 0x84, &[10, 0, 0, 0, 200, 0]) }

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
            txadv_idle_step(),
            stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 0, 0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 1],
                vec![connecting, advertisement, connected.clone(), response(12, 0, &[200, 0]), mtu_event()]),
            (vec![12, 6, 0, 0x34, 0x12], vec![connected.clone(), response(12, 0x84, &[6, 0x34, 0x12, 0, 0xAB, 0xCD])]),
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
            txadv_idle_step(),
            stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 1, 6, 5, 4, 3, 2, 1, 1], vec![connecting.clone()]),
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
        let (result, radio, _) = run_steps(vec![txadv_idle_step(), stop_step(),
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
    fn gatt_write_waits_for_typed_att_completion_and_uses_reserved_byte() {
        let idle = response(12, 0, &[0, 0, 0, 0, 0, 0]);
        let connected = response(12, 0, &[2, 0, 0, 0, 40, 0]);
        let (result, radio, _) = run_steps(vec![
            txadv_idle_step(),
            stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 0, 6, 5, 4, 3, 2, 1, 1], vec![connected.clone(), mtu_event()]),
            (vec![12, 7, 0, 42, 0, 2, 0xAA, 0xBB],
                vec![connected.clone(), response(12, 0x84, &[7, 42, 0, 0])]),
            (vec![12, 0], vec![connected]),
            (vec![12, 3], vec![idle]),
            resume_step(),
        ], json!({"command":"gatt","mac":"010203040506","operation":"write","handle":42,"value":"AABB"}), true);
        let result = result.unwrap();
        assert_eq!(result["confirmation"], "att-write-complete");
        assert_eq!(result["att_confirmed"], true);
        assert_eq!(result["application_confirmed"], false);
        assert!(radio.scanning);
    }

    #[test]
    fn gatt_subscription_att_failure_disconnects_before_restoring_scan() {
        let idle = response(12, 0, &[0; 6]);
        let connected = response(12, 0, &[2, 0, 0, 0, 40, 0]);
        let (result, radio, _) = run_steps(vec![
            txadv_idle_step(), stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 0, 6, 5, 4, 3, 2, 1, 1], vec![connected.clone(), mtu_event()]),
            (vec![12, 13, 0, 42, 0, 1], vec![connected.clone(), response(12, 0x84, &[13, 42, 0, 3, 1])]),
            (vec![12, 0], vec![connected]),
            (vec![12, 3], vec![idle]),
            resume_step(),
        ], json!({"command":"gatt","mac":"010203040506","operation":"exchange","handle":42,"value":"55","prefix":"55"}), true);
        assert!(result.unwrap_err().contains("status 0x03"));
        assert!(radio.scanning);
        assert!(!radio.recovery_required);
    }

    #[test]
    fn gatt_exchange_keeps_early_notification_and_ignores_other_handles_and_prefixes() {
        let idle = response(12, 0, &[0; 6]);
        let connected = response(12, 0, &[2, 0, 0, 0, 40, 0]);
        let (result, radio, _) = run_steps(vec![
            txadv_idle_step(), stop_step(),
            (vec![12, 0], vec![idle.clone()]),
            (vec![12, 1, 0, 6, 5, 4, 3, 2, 1, 1], vec![connected.clone(), mtu_event()]),
            (vec![12, 13, 0, 42, 0, 1], vec![connected.clone(),
                response(14, 0x1B, &[42, 0, 2, 0x55, 0xFF]),
                response(12, 0x84, &[13, 42, 0, 0, 1])]),
            (vec![12, 7, 0, 42, 0, 1, 0x55], vec![connected.clone(),
                response(14, 0x1B, &[43, 0, 2, 0x55, 0xEE]),
                response(14, 0x1B, &[42, 0, 2, 0x44, 0xEE]),
                response(14, 0x1B, &[42, 0, 3, 0x55, 0xAB, 0xCD]),
                response(12, 0x84, &[7, 42, 0, 0])]),
            (vec![12, 0], vec![connected]),
            (vec![12, 3], vec![idle]),
            resume_step(),
        ], json!({"command":"gatt","mac":"010203040506","operation":"exchange","handle":42,"value":"55","prefix":"55"}), true);
        let result = result.unwrap();
        assert_eq!(result["confirmation"], "application-notification");
        assert_eq!(result["notifications"][0]["value"], "55ABCD");
        assert!(radio.scanning);
    }
}
