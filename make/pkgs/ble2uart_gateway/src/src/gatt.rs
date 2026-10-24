//! Host-managed GATT, with separate ATT completion and application notifications.

use crate::codec::{decode::Decoder, encode::Encoder, spec::Spec, value};
use crate::link::{self, Cmd, ConnOp, Event, Link};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, VecDeque};
use std::io::Read;
use std::time::{Duration, Instant};

pub fn default_timeout() -> u64 {
    10000
}
fn default_idle_timeout() -> u64 {
    60000
}
fn one() -> u8 {
    1
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Open {
    pub mac: String,
    #[serde(default)]
    pub addr_type: u8,
    #[serde(default)]
    pub coded: bool,
    #[serde(default = "default_timeout")]
    pub timeout_ms: u64,
    #[serde(default = "default_idle_timeout")]
    pub idle_timeout_ms: u64,
}

impl Open {
    pub fn validate(&self) -> Result<(), String> {
        crate::config::parse_mac(&self.mac)?;
        if self.addr_type > 1 {
            return Err("addr_type must be 0 (public) or 1 (random)".into());
        }
        validate_timeout(self.timeout_ms)?;
        if !(1000..=300000).contains(&self.idle_timeout_ms) {
            return Err("idle_timeout_ms must be 1000-300000".into());
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Operation {
    Discover,
    Read,
    ReadDescriptor,
    Write,
    WriteDescriptor,
    WriteWithoutResponse,
    Mtu,
    Unpair,
    Subscribe,
    Notifications,
    PollNotifications,
    Exchange,
    Patch,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    #[serde(default)]
    pub mac: String,
    #[serde(default)]
    pub session: String,
    #[serde(default)]
    pub addr_type: u8,
    #[serde(default)]
    pub coded: bool,
    pub operation: Operation,
    #[serde(default)]
    pub handle: u16,
    #[serde(default)]
    pub uuid: String,
    #[serde(default)]
    pub value: String,
    #[serde(default)]
    pub prefix: String,
    #[serde(default = "one")]
    pub mode: u8,
    #[serde(default = "one")]
    pub count: u8,
    #[serde(default)]
    pub codec: String,
    #[serde(default)]
    pub offset: usize,
    #[serde(default)]
    pub write_offset: usize,
    #[serde(default)]
    pub write_prefix: Option<String>,
    #[serde(default)]
    pub patch: Option<Value>,
    #[serde(default = "default_timeout")]
    pub timeout_ms: u64,
}

impl Request {
    pub fn open(&self) -> Open {
        Open {
            mac: self.mac.clone(),
            addr_type: self.addr_type,
            coded: self.coded,
            timeout_ms: self.timeout_ms,
            idle_timeout_ms: default_idle_timeout(),
        }
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.session.is_empty() {
            self.open().validate()?;
        } else {
            validate_session(&self.session)?;
            if !self.mac.is_empty() || self.addr_type != 0 || self.coded {
                return Err("session and peer connection parameters are mutually exclusive".into());
            }
        }
        validate_timeout(self.timeout_ms)?;
        let target = !matches!(self.operation, Operation::Discover | Operation::Mtu | Operation::Unpair);
        if target && ((self.handle != 0) == !self.uuid.is_empty()) {
            return Err("provide exactly one nonzero handle or characteristic/descriptor UUID".into());
        }
        if !target && (self.handle != 0 || !self.uuid.is_empty()) {
            return Err("this GATT operation does not take a handle or UUID".into());
        }
        if !self.uuid.is_empty() {
            normalize_uuid(&self.uuid)?;
        }
        let writes = matches!(
            self.operation,
            Operation::Write
                | Operation::WriteDescriptor
                | Operation::WriteWithoutResponse
                | Operation::Exchange
                | Operation::Patch
        );
        let maximum = if self.operation == Operation::WriteWithoutResponse {
            58
        } else {
            56
        };
        let bytes = hex_bytes(&self.value, maximum)?;
        if !writes && !bytes.is_empty() {
            return Err("value is only allowed for writes/exchanges".into());
        }
        if matches!(self.operation, Operation::Exchange | Operation::Patch) && bytes.is_empty() {
            return Err("exchange/patch requires a nonempty request value".into());
        }
        if self.mode > 2 {
            return Err("subscription mode must be 0 (disable), 1 (notify), or 2 (indicate)".into());
        }
        if matches!(self.operation, Operation::Exchange | Operation::Patch) && self.mode == 0 {
            return Err("exchange/patch requires notifications or indications".into());
        }
        if !(1..=64).contains(&self.count) {
            return Err("count must be 1-64".into());
        }
        hex_bytes(&self.prefix, 197)?;
        let receives = matches!(
            self.operation,
            Operation::Notifications | Operation::PollNotifications | Operation::Exchange | Operation::Patch
        );
        if !receives && (!self.prefix.is_empty() || self.count != 1) {
            return Err("prefix/count are only allowed for notification operations".into());
        }
        if !self.codec.is_empty() && !receives && !matches!(self.operation, Operation::Read | Operation::ReadDescriptor)
        {
            return Err("codec is only allowed when reading values or notifications".into());
        }
        if self.offset > 197 || self.write_offset > 197 || (self.codec.is_empty() && self.offset != 0) {
            return Err("codec offsets must be 0-197 and offset requires a codec".into());
        }
        if self.operation == Operation::Patch {
            if self.codec.is_empty()
                || self
                    .patch
                    .as_ref()
                    .and_then(Value::as_object)
                    .is_none_or(|patch| patch.is_empty())
            {
                return Err("patch requires a codec and a nonempty JSON patch object".into());
            }
            if self.count != 1 {
                return Err("patch requires exactly one response per exchange".into());
            }
        } else if self.patch.is_some() || self.write_offset != 0 || self.write_prefix.is_some() {
            return Err("patch/write_offset/write_prefix are only allowed for patch operations".into());
        }
        if let Some(prefix) = &self.write_prefix {
            hex_bytes(prefix, 56)?;
        }
        Ok(())
    }

    pub fn validate_spec(&self, spec: &Spec) -> Result<(), String> {
        if !self.codec.is_empty() && spec.structure(&self.codec).is_none() {
            return Err(format!("unknown codec structure {}", self.codec));
        }
        Ok(())
    }
}

fn validate_timeout(timeout: u64) -> Result<(), String> {
    if !(100..=30000).contains(&timeout) {
        return Err("timeout_ms must be 100-30000".into());
    }
    Ok(())
}

pub fn validate_session(session: &str) -> Result<(), String> {
    if session.len() != 32 || !session.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("session must be the 32-digit token returned by gatt-open".into());
    }
    Ok(())
}

pub fn hex_bytes(text: &str, max: usize) -> Result<Vec<u8>, String> {
    let digits: String = text
        .chars()
        .filter(|character| !character.is_ascii_whitespace())
        .collect();
    if !digits.is_ascii() || digits.len() % 2 != 0 || digits.len() / 2 > max {
        return Err(format!("expected hexadecimal byte pairs, at most {max} bytes"));
    }
    (0..digits.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&digits[index..index + 2], 16).map_err(|_| "invalid hexadecimal data".into()))
        .collect()
}

fn normalize_uuid(text: &str) -> Result<String, String> {
    if text.len() == 36 && ![8, 13, 18, 23].iter().all(|index| text.as_bytes()[*index] == b'-') {
        return Err("invalid UUID separators".into());
    }
    let digits = if text.len() == 36 {
        text.replace('-', "")
    } else {
        text.to_string()
    };
    if !digits.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("UUID must contain hexadecimal digits".into());
    }
    let full = match digits.len() {
        4 => format!("0000{digits}00001000800000805F9B34FB"),
        8 => format!("{digits}00001000800000805F9B34FB"),
        32 => digits,
        _ => return Err("UUID must be 16, 32 or 128 bits".into()),
    }
    .to_uppercase();
    Ok(format!(
        "{}-{}-{}-{}-{}",
        &full[..8],
        &full[8..12],
        &full[12..16],
        &full[16..20],
        &full[20..]
    ))
}

fn wire_uuid(bytes: &[u8]) -> Result<String, String> {
    if !matches!(bytes.len(), 2 | 4 | 16) {
        return Err("malformed discovery UUID length".into());
    }
    normalize_uuid(&value::hex(&bytes.iter().rev().copied().collect::<Vec<_>>()))
}

#[derive(Clone, Serialize)]
struct Attribute {
    #[serde(rename = "type")]
    kind: u8,
    data: String,
    uuid: String,
    handle: u16,
    #[serde(skip_serializing_if = "Option::is_none")]
    end_handle: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    primary: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    properties: Option<u8>,
    #[serde(skip_serializing_if = "Option::is_none")]
    service_handle: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    characteristic_handle: Option<u16>,
}

struct Notification {
    sequence: u64,
    handle: u16,
    opcode: u8,
    value: Vec<u8>,
}

impl Notification {
    fn json(&self, request: &Request, spec: &Spec) -> Result<Value, String> {
        let mut result = json!({"sequence": self.sequence, "handle": self.handle,
            "opcode": self.opcode, "value": value::hex(&self.value)});
        if !request.codec.is_empty() {
            result["codec"] = json!(request.codec);
            result["decoded"] = decode_value(spec, request, &self.value)?;
        }
        Ok(result)
    }
}

fn decode_value(spec: &Spec, request: &Request, bytes: &[u8]) -> Result<Value, String> {
    let bytes = bytes
        .get(request.offset..)
        .ok_or("codec offset exceeds received value")?;
    Decoder::new(spec, bytes)
        .decode_exact(&request.codec)
        .map(|value| value.to_json())
        .map_err(|error| error.to_string())
}

pub struct State {
    pub token: String,
    pub mac: String,
    pub mtu: u16,
    pub expires: Instant,
    idle_timeout: Duration,
    connected: bool,
    sequence: u64,
    notifications: VecDeque<Notification>,
    attributes: Vec<Attribute>,
    discovered: bool,
    subscriptions: BTreeMap<u16, u8>,
}

impl State {
    pub fn new(open: &Open) -> Result<Self, String> {
        let mut random = [0; 16];
        std::fs::File::open("/dev/urandom")
            .and_then(|mut file| file.read_exact(&mut random))
            .map_err(|error| format!("cannot create GATT session token: {error}"))?;
        let mut state = Self::empty(open);
        state.token = value::hex(&random);
        Ok(state)
    }

    fn empty(open: &Open) -> Self {
        Self {
            token: String::new(),
            mac: open.mac.clone(),
            mtu: 23,
            expires: Instant::now() + Duration::from_millis(open.idle_timeout_ms),
            idle_timeout: Duration::from_millis(open.idle_timeout_ms),
            connected: false,
            sequence: 0,
            notifications: VecDeque::new(),
            attributes: Vec::new(),
            discovered: false,
            subscriptions: BTreeMap::new(),
        }
    }

    pub fn touch(&mut self) {
        self.expires = Instant::now() + self.idle_timeout;
    }

    pub fn snapshot(&self) -> Value {
        json!({"mac": self.mac, "mtu": self.mtu, "pending_notifications": self.notifications.len(),
            "remaining_ms": self.expires.saturating_duration_since(Instant::now()).as_millis(),
            "idle_timeout_ms": self.idle_timeout.as_millis(), "subscriptions": self.subscriptions})
    }

    pub fn observe(&mut self, event: &Event) -> Result<bool, String> {
        match event {
            Event::Spontaneous {
                cmd: 0x0E,
                sub,
                payload,
                ..
            } if matches!(sub, 0x1B | 0x1D) => {
                if payload.len() < 3 || payload.len() != 3 + usize::from(payload[2]) || payload[2] > 197 {
                    return Err("malformed RXDATA notification".into());
                }
                if self.notifications.len() >= 128 {
                    return Err("GATT notification queue overflow (128 events); session closed".into());
                }
                self.sequence += 1;
                self.notifications.push_back(Notification {
                    sequence: self.sequence,
                    handle: u16::from_le_bytes([payload[0], payload[1]]),
                    opcode: *sub,
                    value: payload[3..].to_vec(),
                });
                Ok(true)
            }
            Event::Response {
                cmd: 0x0C,
                status,
                payload,
                ..
            } => {
                if !status.is_ok() {
                    return Err(format!("CONN: {}", status.as_str()));
                }
                if payload.len() == 6 && payload[0] <= 2 && payload[1] <= 1 {
                    if payload[0] == 0 && self.connected {
                        return Err("BLE peer disconnected unexpectedly".into());
                    }
                    self.connected = payload[0] == 2;
                }
                Ok(true)
            }
            Event::Spontaneous {
                cmd: 0x0C,
                sub: 4,
                payload,
                ..
            } if payload.first() == Some(&(ConnOp::ExchangeMtu as u8)) => {
                let mtu = completion_result(payload, ConnOp::ExchangeMtu, 0)?;
                self.set_mtu(mtu)?;
                Ok(true)
            }
            Event::Spontaneous { cmd: 0x0C, .. } => Ok(true),
            _ => Ok(false),
        }
    }

    fn set_mtu(&mut self, bytes: &[u8]) -> Result<(), String> {
        if bytes.len() != 2 {
            return Err("malformed MTU completion".into());
        }
        let mtu = u16::from_le_bytes([bytes[0], bytes[1]]);
        if !(23..=517).contains(&mtu) {
            return Err(format!("invalid negotiated MTU {mtu}"));
        }
        self.mtu = mtu;
        Ok(())
    }
}

struct Wire<'a> {
    link: &'a mut Link,
    state: &'a mut State,
    deferred: Vec<Event>,
    deadline: Instant,
    cancellable: bool,
}

impl Drop for Wire<'_> {
    fn drop(&mut self) {
        self.deferred.append(&mut self.link.pending);
        self.link.pending = std::mem::take(&mut self.deferred);
    }
}

impl Wire<'_> {
    fn check_deadline(&self) -> Result<(), String> {
        if self.cancellable && crate::STOP_REQUESTED.load(std::sync::atomic::Ordering::Relaxed) {
            return Err("command cancelled: gateway is stopping".into());
        }
        if Instant::now() >= self.deadline {
            return Err("GATT operation timed out".into());
        }
        Ok(())
    }

    fn send(&mut self, op: ConnOp, parameters: &[u8]) -> Result<(), String> {
        self.check_deadline()?;
        let mut payload = vec![op as u8];
        payload.extend_from_slice(parameters);
        self.link.send(&link::build_command(Cmd::Conn, [0; 6], &payload))
    }

    fn defer(&mut self, event: Event) -> Result<(), String> {
        if self.state.observe(&event)? {
            return Ok(());
        }
        match event {
            Event::Adv(_) | Event::Spontaneous { .. } => self.deferred.push(event),
            Event::Debug(text) => log::debug!("firmware: {text}"),
            other => log::debug!("GATT: unrelated event {other:?}"),
        }
        if self.deferred.len() > 1024 {
            return Err("too many unrelated events during GATT operation".into());
        }
        Ok(())
    }

    fn drain(&mut self) -> Result<(), String> {
        while let Some(event) = self.link.try_next() {
            self.defer(event)?;
        }
        Ok(())
    }

    fn next(&mut self) -> Result<Event, String> {
        loop {
            if self.cancellable && crate::STOP_REQUESTED.load(std::sync::atomic::Ordering::Relaxed) {
                return Err("command cancelled: gateway is stopping".into());
            }
            let remaining = self.deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return Err("GATT operation timed out".into());
            }
            if let Some(event) = self.link.next(remaining.min(Duration::from_millis(100)))? {
                return Ok(event);
            }
        }
    }

    fn wait<T>(&mut self, mut accept: impl FnMut(&Event) -> Option<Result<T, String>>) -> Result<T, String> {
        loop {
            let event = self.next()?;
            if let Some(result) = accept(&event) {
                return result;
            }
            self.defer(event)?;
        }
    }

    fn connection_state(&mut self, expected: Option<u8>) -> Result<u8, String> {
        let state = self.wait(|event| match event {
            Event::Response {
                cmd: 0x0C,
                status,
                payload,
                ..
            } if payload.len() == 6 && payload[0] <= 2 && payload[1] <= 1 => {
                if !status.is_ok() {
                    Some(Err(format!("CONN: {}", status.as_str())))
                } else if expected.is_none_or(|state| state == payload[0]) {
                    Some(Ok(payload[0]))
                } else if expected == Some(2) && payload[0] == 0 {
                    Some(Err("BLE connection closed before open completed".into()))
                } else {
                    None
                }
            }
            _ => None,
        })?;
        self.state.connected = state == 2;
        Ok(state)
    }

    fn completion(&mut self, op: ConnOp, handle: u16) -> Result<Vec<u8>, String> {
        self.wait(|event| match event {
            Event::Spontaneous {
                cmd: 0x0C,
                sub: 4,
                payload,
                ..
            } if payload.len() >= 3 && payload[0] == op as u8 && payload[1..3] == handle.to_le_bytes() => {
                Some(completion_result(payload, op, handle).map(Vec::from))
            }
            _ => None,
        })
    }

    fn discover(&mut self) -> Result<Value, String> {
        self.send(ConnOp::DiscoverServices, &[])?;
        let mut entries: Vec<Attribute> = Vec::new();
        let mut service = None;
        let mut characteristic = None;
        self.wait(|event| match event {
            Event::Spontaneous {
                cmd: 0x0C,
                sub,
                payload,
                ..
            } if *sub <= 3 => {
                if *sub == 3 {
                    return Some(if payload.as_slice() == [0] {
                        Ok(())
                    } else {
                        Err(format!("GATT discovery failed: {}", value::hex(payload)))
                    });
                }
                if entries.len() >= 512 {
                    return Some(Err("GATT discovery exceeds 512 entries".into()));
                }
                let parsed = (|| {
                    let (header, handle, end_handle, primary, properties) = match *sub {
                        0 if payload.len() >= 7 => (
                            5,
                            u16::from_le_bytes([payload[1], payload[2]]),
                            Some(u16::from_le_bytes([payload[3], payload[4]])),
                            Some(payload[0] != 0),
                            None,
                        ),
                        1 if payload.len() >= 5 && service.is_some() => (
                            3,
                            u16::from_le_bytes([payload[0], payload[1]]),
                            None,
                            None,
                            Some(payload[2]),
                        ),
                        2 if payload.len() >= 4 && characteristic.is_some() => {
                            (2, u16::from_le_bytes([payload[0], payload[1]]), None, None, None)
                        }
                        _ => return Err("malformed or unordered GATT discovery event".into()),
                    };
                    if handle == 0 {
                        return Err("discovery returned a zero handle".into());
                    }
                    let uuid = wire_uuid(&payload[header..])?;
                    if *sub == 0 {
                        service = Some(handle);
                        characteristic = None;
                    }
                    if *sub == 1 {
                        characteristic = Some(handle);
                    }
                    entries.push(Attribute {
                        kind: *sub,
                        data: value::hex(payload),
                        uuid,
                        handle,
                        end_handle,
                        primary,
                        properties,
                        service_handle: service,
                        characteristic_handle: characteristic,
                    });
                    Ok(())
                })();
                parsed.err().map(Err)
            }
            _ => None,
        })?;
        self.state.attributes = entries;
        self.state.discovered = true;
        Ok(json!({"entries": self.state.attributes, "confirmation": "discovery-complete"}))
    }

    fn handle(&mut self, request: &Request) -> Result<u16, String> {
        if request.handle != 0 {
            return Ok(request.handle);
        }
        if !self.state.discovered {
            self.discover()?;
        }
        let uuid = normalize_uuid(&request.uuid)?;
        let kind = if matches!(
            request.operation,
            Operation::ReadDescriptor | Operation::WriteDescriptor
        ) {
            2
        } else {
            1
        };
        let handles: Vec<_> = self
            .state
            .attributes
            .iter()
            .filter(|attribute| attribute.kind == kind && attribute.uuid == uuid)
            .map(|attribute| attribute.handle)
            .collect();
        match handles.as_slice() {
            [handle] => Ok(*handle),
            [] => Err(format!("GATT UUID {uuid} was not found")),
            _ => Err(format!("GATT UUID {uuid} is ambiguous; use an explicit handle")),
        }
    }

    fn subscribe(&mut self, handle: u16, mode: u8) -> Result<(), String> {
        let mut parameters = vec![0];
        parameters.extend_from_slice(&handle.to_le_bytes());
        parameters.push(mode);
        self.send(ConnOp::Subscribe, &parameters)?;
        let result = self.completion(ConnOp::Subscribe, handle)?;
        if result != [mode] {
            return Err("malformed subscription completion".into());
        }
        if mode == 0 {
            self.state.subscriptions.remove(&handle);
        } else {
            self.state.subscriptions.insert(handle, mode);
        }
        Ok(())
    }

    fn write(&mut self, handle: u16, bytes: &[u8], op: Operation) -> Result<Value, String> {
        self.check_deadline()?;
        let limit = usize::from(self.state.mtu - 3).min(if op == Operation::WriteWithoutResponse { 58 } else { 56 });
        if bytes.len() > limit {
            return Err(format!(
                "write exceeds negotiated MTU/firmware limit ({limit} bytes); no data sent"
            ));
        }
        if op == Operation::WriteWithoutResponse {
            self.link.send(&link::tx_data_command(handle, bytes)?)?;
            self.wait(|event| match event {
                Event::Response {
                    cmd: 0x0D,
                    status,
                    payload,
                    ..
                } if payload.len() == 6
                    && payload[..2] == handle.to_le_bytes()
                    && usize::from(payload[2]) == bytes.len() =>
                {
                    Some(if status.is_ok() && payload[3] == 0 {
                        Ok(json!({"confirmation": "stack-accepted", "att_confirmed": false}))
                    } else {
                        Err(format!("TXDATA: {}, stack status {}", status.as_str(), payload[3]))
                    })
                }
                _ => None,
            })
        } else {
            let operation = if op == Operation::WriteDescriptor {
                ConnOp::WriteDescriptor
            } else {
                ConnOp::WriteCharacteristic
            };
            if operation == ConnOp::WriteCharacteristic {
                self.link.send(&link::conn_write_command(handle, bytes)?)?;
            } else {
                let mut parameters = vec![0];
                parameters.extend_from_slice(&handle.to_le_bytes());
                parameters.push(bytes.len() as u8);
                parameters.extend_from_slice(bytes);
                self.send(operation, &parameters)?;
            }
            let result = self.completion(operation, handle)?;
            if !result.is_empty() {
                return Err("malformed ATT write completion".into());
            }
            Ok(json!({"confirmation": "att-write-complete", "att_confirmed": true, "application_confirmed": false}))
        }
    }

    fn notifications(
        &mut self,
        handle: u16,
        prefix: &[u8],
        count: u8,
        after: u64,
    ) -> Result<Vec<Notification>, String> {
        let mut result = Vec::new();
        while result.len() < usize::from(count) {
            if let Some(index) = self.state.notifications.iter().position(|notification| {
                notification.handle == handle && notification.sequence > after && notification.value.starts_with(prefix)
            }) {
                result.push(self.state.notifications.remove(index).expect("existing notification"));
            } else {
                let event = self.next()?;
                self.defer(event)?;
            }
        }
        Ok(result)
    }

    fn exchange(&mut self, handle: u16, bytes: &[u8], request: &Request) -> Result<Vec<Notification>, String> {
        if self.state.subscriptions.get(&handle) != Some(&request.mode) {
            self.subscribe(handle, request.mode)?;
        }
        self.drain()?;
        let after = self.state.sequence;
        self.write(handle, bytes, Operation::Write)?;
        self.notifications(handle, &hex_bytes(&request.prefix, 197)?, request.count, after)
    }
}

fn completion_result(payload: &[u8], op: ConnOp, handle: u16) -> Result<&[u8], String> {
    if payload.len() < 4 || payload[0] != op as u8 || payload[1..3] != handle.to_le_bytes() {
        return Err("malformed GATT operation completion".into());
    }
    if payload[3] != 0 {
        return Err(format!(
            "ATT operation {} on handle {handle} failed: status 0x{:02X}",
            op as u8, payload[3]
        ));
    }
    Ok(&payload[4..])
}

pub fn open(link: &mut Link, state: &mut State, open: &Open) -> (Result<Value, String>, bool) {
    let mut wire = Wire {
        link,
        state,
        deferred: Vec::new(),
        deadline: Instant::now() + Duration::from_millis(open.timeout_ms),
        cancellable: true,
    };
    let mut owns_connection = false;
    let result = (|| {
        wire.drain()?;
        wire.send(ConnOp::StatusQuery, &[])?;
        if wire.connection_state(None)? != 0 {
            return Err("adapter already has a GATT connection; it was not taken over".into());
        }
        let mut address = crate::config::parse_mac(&open.mac)?;
        address.reverse();
        owns_connection = true;
        wire.link
            .send(&link::conn_open_managed_command(open.addr_type, &address, open.coded))?;
        wire.connection_state(Some(2))?;
        let mtu = wire.completion(ConnOp::ExchangeMtu, 0)?;
        wire.state.set_mtu(&mtu)?;
        wire.state.touch();
        Ok(json!({"session": wire.state.token, "connection": wire.state.snapshot(),
            "confirmation": "connected", "host_managed": true}))
    })();
    (result, owns_connection)
}

pub fn recover_connection(link: &mut Link, timeout: Duration) -> Result<(), String> {
    let open = Open {
        mac: String::new(),
        addr_type: 0,
        coded: false,
        timeout_ms: 1000,
        idle_timeout_ms: 1000,
    };
    let mut state = State::empty(&open);
    let mut wire = Wire {
        link,
        state: &mut state,
        deferred: Vec::new(),
        deadline: Instant::now() + timeout,
        cancellable: false,
    };
    while let Some(event) = wire.link.try_next() {
        match event {
            Event::Response { cmd: 0x0C, .. } | Event::Spontaneous { cmd: 0x0C | 0x0E, .. } => {}
            other => wire.defer(other)?,
        }
    }
    wire.send(ConnOp::StatusQuery, &[])?;
    let state = wire.connection_state(None)?;
    if state != 0 {
        wire.send(
            if state == 1 {
                ConnOp::CancelOpen
            } else {
                ConnOp::Disconnect
            },
            &[],
        )?;
        wire.connection_state(Some(0))?;
    }
    Ok(())
}

pub fn execute(link: &mut Link, state: &mut State, request: &Request, spec: &Spec) -> Result<Value, String> {
    let mut wire = Wire {
        link,
        state,
        deferred: Vec::new(),
        deadline: Instant::now() + Duration::from_millis(request.timeout_ms),
        cancellable: true,
    };
    wire.check_deadline()?;
    wire.drain()?;
    let result = match request.operation {
        Operation::Discover => wire.discover()?,
        Operation::Mtu => {
            wire.send(ConnOp::ExchangeMtu, &[])?;
            let result = wire.completion(ConnOp::ExchangeMtu, 0)?;
            wire.state.set_mtu(&result)?;
            json!({"mtu": wire.state.mtu, "confirmation": "mtu-result"})
        }
        Operation::Unpair => {
            wire.send(ConnOp::Unpair, &[])?;
            wire.connection_state(Some(0))?;
            json!({"confirmation": "disconnected", "security_confirmed": false})
        }
        operation => {
            let handle = wire.handle(request)?;
            match operation {
                Operation::Read | Operation::ReadDescriptor => {
                    let op = if operation == Operation::Read {
                        ConnOp::ReadCharacteristic
                    } else {
                        ConnOp::ReadDescriptor
                    };
                    let mut parameters = vec![0];
                    parameters.extend_from_slice(&handle.to_le_bytes());
                    wire.send(op, &parameters)?;
                    let bytes = wire.completion(op, handle)?;
                    let mut result =
                        json!({"handle": handle, "value": value::hex(&bytes), "confirmation": "read-result"});
                    if !request.codec.is_empty() {
                        result["decoded"] = decode_value(spec, request, &bytes)?;
                    }
                    result
                }
                Operation::Write | Operation::WriteDescriptor | Operation::WriteWithoutResponse => {
                    wire.write(handle, &hex_bytes(&request.value, 58)?, operation)?
                }
                Operation::Subscribe => {
                    wire.subscribe(handle, request.mode)?;
                    json!({"handle": handle, "mode": request.mode, "confirmation": "subscription-complete"})
                }
                Operation::PollNotifications => {
                    let prefix = hex_bytes(&request.prefix, 197)?;
                    let mut notifications = Vec::new();
                    while notifications.len() < usize::from(request.count) {
                        let Some(index) = wire.state.notifications.iter().position(|notification| {
                            notification.handle == handle && notification.value.starts_with(&prefix)
                        }) else { break; };
                        notifications.push(wire.state.notifications.remove(index).expect("existing notification"));
                    }
                    notification_result(&notifications, request, spec)?
                }
                Operation::Notifications | Operation::Exchange => {
                    let notifications = if operation == Operation::Exchange {
                        wire.exchange(handle, &hex_bytes(&request.value, 56)?, request)?
                    } else {
                        wire.notifications(handle, &hex_bytes(&request.prefix, 197)?, request.count, 0)?
                    };
                    notification_result(&notifications, request, spec)?
                }
                Operation::Patch => {
                    let before = wire.exchange(handle, &hex_bytes(&request.value, 56)?, request)?;
                    let raw = &before[0].value;
                    let mut decoded = decode_value(spec, request, raw)?;
                    let original = decoded.clone();
                    let encoded = Encoder::new(spec).encode(&request.codec, &value::Value::from_json(&decoded))?;
                    if raw.get(request.offset..) != Some(encoded.as_slice()) {
                        return Err("codec is not byte-exact for this configuration; patch refused without writing. Use a firmware-matched codec or an explicit raw write".into());
                    }
                    merge_patch(&mut decoded, request.patch.as_ref().expect("validated patch"), "")?;
                    let updated = Encoder::new(spec).encode(&request.codec, &value::Value::from_json(&decoded))?;
                    if updated.len() != encoded.len()
                        || request.write_offset > updated.len()
                        || updated[..request.write_offset] != encoded[..request.write_offset]
                    {
                        return Err("patch changes the layout or response-only bytes; write refused".into());
                    }
                    let check = Decoder::new(spec, &updated)
                        .decode_exact(&request.codec)
                        .map_err(|error| error.to_string())?
                        .to_json();
                    if !patch_matches(&check, request.patch.as_ref().expect("validated patch")) {
                        return Err(
                            "patch contains a computed/read-only or unrepresentable field; write refused".into(),
                        );
                    }
                    let mut bytes = hex_bytes(request.write_prefix.as_deref().unwrap_or(&request.value), 56)?;
                    bytes.extend_from_slice(&updated[request.write_offset..]);
                    let after = wire.exchange(handle, &bytes, request)?;
                    let response = decode_value(spec, request, &after[0].value)?;
                    if !patch_matches(&response, request.patch.as_ref().expect("validated patch")) {
                        return Err(
                            "application response does not confirm the requested patch; device may have changed".into(),
                        );
                    }
                    let mut result = notification_result(&after, request, spec)?;
                    result["before"] = original;
                    result["written"] = json!(value::hex(&bytes));
                    result["patch_verified"] = json!(true);
                    result
                }
                _ => unreachable!(),
            }
        }
    };
    wire.state.touch();
    Ok(result)
}

fn notification_result(notifications: &[Notification], request: &Request, spec: &Spec) -> Result<Value, String> {
    let values: Result<Vec<_>, _> = notifications
        .iter()
        .map(|notification| notification.json(request, spec))
        .collect();
    Ok(json!({"confirmation": "application-notification", "notifications": values?}))
}

fn merge_patch(value: &mut Value, patch: &Value, path: &str) -> Result<(), String> {
    if let Value::Object(fields) = patch {
        let object = value
            .as_object_mut()
            .ok_or_else(|| format!("patch {path}: expected an object"))?;
        for (name, patch) in fields {
            let path = format!("{path}/{name}");
            let field = object
                .get_mut(name)
                .ok_or_else(|| format!("unknown patch field {path}"))?;
            merge_patch(field, patch, &path)?;
        }
    } else if patch.is_null()
        || value.is_object()
        || value.is_array() != patch.is_array()
        || value.is_boolean() != patch.is_boolean()
        || value.is_number() != patch.is_number()
        || value.is_string() != patch.is_string()
    {
        return Err(format!("patch {path}: value type does not match the codec"));
    } else {
        *value = patch.clone();
    }
    Ok(())
}

fn patch_matches(value: &Value, patch: &Value) -> bool {
    if let Value::Object(fields) = patch {
        fields
            .iter()
            .all(|(name, patch)| value.get(name).is_some_and(|value| patch_matches(value, patch)))
    } else if value.is_number() && patch.is_number() {
        value.as_f64() == patch.as_f64()
    } else {
        value == patch
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(extra: Value) -> Request {
        let mut input = json!({"mac":"AABBCCDDEEFF","operation":"exchange","uuid":"1F1F","value":"55","prefix":"55"});
        input
            .as_object_mut()
            .unwrap()
            .extend(extra.as_object().unwrap().clone());
        serde_json::from_value(input).unwrap()
    }

    fn state() -> State {
        State::empty(&Open {
            mac: "AABBCCDDEEFF".into(),
            addr_type: 0,
            coded: false,
            timeout_ms: 1000,
            idle_timeout_ms: 1000,
        })
    }

    #[test]
    fn full_discovery_uuids_use_ble_little_endian_and_short_uuid_aliases() {
        let uuid = "00001F1F-0000-1000-8000-00805F9B34FB";
        assert_eq!(normalize_uuid("1f1f").unwrap(), uuid);
        assert_eq!(normalize_uuid("00001f1f").unwrap(), uuid);
        assert_eq!(wire_uuid(&[0x1F, 0x1F]).unwrap(), uuid);
        assert_eq!(wire_uuid(&[0x1F, 0x1F, 0, 0]).unwrap(), uuid);
        assert_eq!(
            wire_uuid(&hex_bytes("FB349B5F80000080001000001F1F0000", 16).unwrap()).unwrap(),
            uuid
        );
        assert_eq!(
            wire_uuid(&hex_bytes("1032547698BADCFE1032547698BADCFE", 16).unwrap()).unwrap(),
            "FEDCBA98-7654-3210-FEDC-BA9876543210"
        );
        for invalid in [
            "",
            "1Ｆ1F",
            "00001F1F0000-1000-8000-00805F9B34FB",
            "00-001F1F00001000800000805F9B34FB",
            "x1F1F",
        ] {
            assert!(normalize_uuid(invalid).is_err(), "{invalid}");
        }
    }

    #[test]
    fn gatt_limits_and_operation_fields_are_checked_before_radio_access() {
        assert!(request(json!({})).validate().is_ok());
        for extra in [
            json!({"handle":42}),
            json!({"uuid":""}),
            json!({"mode":3}),
            json!({"mode":0}),
            json!({"count":0}),
            json!({"count":65}),
            json!({"timeout_ms":99}),
            json!({"codec":"","offset":1}),
            json!({"value":"AB".repeat(57)}),
            json!({"operation":"read","value":"55"}),
            json!({"write_offset":1}),
            json!({"operation":"patch","codec":"cfg","patch":{}}),
            json!({"operation":"patch","codec":"cfg","patch":{"flg2":{"bt5phy":true}},"count":2}),
            json!({"session":"A".repeat(32)}),
        ] {
            assert!(request(extra.clone()).validate().is_err(), "{extra}");
        }
        assert!(
            request(json!({"operation":"patch","codec":"cfg","offset":1,"write_offset":1,
                "patch":{"flg2":{"bt5phy":true,"longrange":true}}}))
            .validate()
            .is_ok()
        );
        assert!(
            request(json!({"operation":"write-without-response","value":"AB".repeat(58),"prefix":""}))
                .validate()
                .is_ok()
        );
    }

    #[test]
    fn codec_config_patch_preserves_other_fields_and_omits_firmware_version_on_write() {
        let spec = Spec::embedded().unwrap();
        let raw = hex_bytes("43851000002804A9313104B4", 12).unwrap();
        let mut parsed = Decoder::new(&spec, &raw).decode_exact("cfg").unwrap().to_json();
        assert_eq!(
            Encoder::new(&spec)
                .encode("cfg", &value::Value::from_json(&parsed))
                .unwrap(),
            raw
        );
        merge_patch(&mut parsed, &json!({"flg2":{"bt5phy":true,"longrange":true}}), "").unwrap();
        let encoded = Encoder::new(&spec)
            .encode("cfg", &value::Value::from_json(&parsed))
            .unwrap();
        let mut expected = raw.clone();
        expected[2] |= 0x60;
        assert_eq!(encoded, expected);
        assert_eq!(encoded[0], 0x43);
        let mut write = vec![0x55];
        write.extend_from_slice(&encoded[1..]);
        assert_eq!(write.len(), 12);
        assert_eq!(&write[..3], &[0x55, 0x85, 0x70]);
        assert!(merge_patch(&mut parsed, &json!({"flg2":{"typo":true}}), "").is_err());
        assert!(merge_patch(&mut parsed, &json!({"flg2":{"longrange":"true"}}), "").is_err());
        assert!(merge_patch(&mut parsed, &json!({"flg2":null}), "").is_err());
    }

    #[test]
    fn strict_gatt_decoding_rejects_unknown_tails_and_missing_configuration_bytes() {
        let spec = Spec::embedded().unwrap();
        let request = request(json!({"codec":"cfg","offset":1}));
        let mut raw = hex_bytes("5543851000002804A9313104B4", 13).unwrap();
        assert!(decode_value(&spec, &request, &raw).is_ok());
        raw.push(0);
        assert!(decode_value(&spec, &request, &raw)
            .unwrap_err()
            .contains("consumed 12 of 13"));
        raw.truncate(3);
        assert!(decode_value(&spec, &request, &raw).is_err());
    }

    #[test]
    fn complete_notifications_and_indications_are_bounded_without_truncation() {
        let mut state = state();
        let mut payload = vec![42, 0, 197];
        payload.extend(0..197);
        for index in 0..128 {
            state
                .observe(&Event::Spontaneous {
                    cmd: 14,
                    sub: if index % 2 == 0 { 0x1B } else { 0x1D },
                    data: [0; 6],
                    payload: payload.clone(),
                })
                .unwrap();
        }
        assert_eq!(
            state.notifications.front().unwrap().value,
            (0..197).collect::<Vec<u8>>()
        );
        assert_eq!(state.notifications.back().unwrap().sequence, 128);
        assert!(state
            .observe(&Event::Spontaneous {
                cmd: 14,
                sub: 0x1B,
                data: [0; 6],
                payload
            })
            .unwrap_err()
            .contains("overflow"));
        assert_eq!(state.notifications.len(), 128);
        assert!(state
            .observe(&Event::Spontaneous {
                cmd: 14,
                sub: 0x1B,
                data: [0; 6],
                payload: vec![42, 0, 3, 0x55]
            })
            .is_err());
    }

    #[test]
    fn att_completions_match_operation_handle_status_and_full_value() {
        assert_eq!(
            completion_result(&[6, 42, 0, 0, 0xAB, 0xCD], ConnOp::ReadCharacteristic, 42).unwrap(),
            [0xAB, 0xCD]
        );
        assert!(completion_result(&[6, 42, 0, 5], ConnOp::ReadCharacteristic, 42)
            .unwrap_err()
            .contains("0x05"));
        assert!(completion_result(&[6, 42, 0, 0], ConnOp::WriteCharacteristic, 42).is_err());
        assert!(completion_result(&[6, 43, 0, 0], ConnOp::ReadCharacteristic, 42).is_err());
        assert!(completion_result(&[6, 42, 0], ConnOp::ReadCharacteristic, 42).is_err());
    }
}
