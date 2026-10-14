use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::net::{SocketAddr, SocketAddrV6, TcpListener, TcpStream, UdpSocket};
use std::num::NonZeroU8;
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::os::unix::io::{AsRawFd, RawFd};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};

use async_channel::{Receiver, Sender};
use base64::{engine::general_purpose::STANDARD, Engine};
use embassy_futures::select::{select, select4, Either};
use rs_matter::cert::{gen::VALID_FOREVER, MAX_CERT_TLV_AND_ASN1_LEN, MAX_CERT_TLV_LEN};
use rs_matter::crypto::{default_crypto, CanonAeadKey, CanonPkcSecretKey, Crypto, Rng as _, SecretKey, SigningSecretKey};
use rs_matter::dm::devices::test::{DAC_PRIVKEY, TEST_DEV_ATT, TEST_DEV_COMM, TEST_DEV_DET};
use rs_matter::error::{Error, ErrorCode};
use rs_matter::im::client::{ImClient, SubscribeOutcome};
use rs_matter::im::{AttrPath, AttrResp, IMStatusCode, OpCode, ReportDataResp, StatusResp};
use rs_matter::onboard::cac::{IcacGenerator, RcacGenerator};
use rs_matter::onboard::noc::NocGenerator;
use rs_matter::onboard::{CommissionOptions, Commissioner};
use rs_matter::transport::exchange::Exchange;
use rs_matter::transport::network::mdns::{DottedName, MdnsRemoteService};
use rs_matter::transport::network::{Address, IpAddr, MatterRemoteService, NoNetwork};
use rs_matter::tlv::{FromTLV, TLVElement, TLVTag, TLVValue, TLVWrite};
use rs_matter::utils::select::Coalesce;
use rs_matter::Matter;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tungstenite::{Message, Error as WsError};

mod mdns;

const FABRIC_ID: u64 = 1;
const CONTROLLER_ID: u64 = 112233;

/// How often the watchdog looks for a subscription that has to be
/// re-established. Short on purpose: it also bounds how fast an mDNS
/// announcement turns into a re-subscribe, and a tick costs a few microseconds.
const WATCHDOG_TICK: Duration = Duration::from_secs(2);

/// How old the last report of a subscription must be before an mDNS announcement
/// of the peer is taken as "the peer restarted".
///
/// rs-matter announces at startup (and when its records change), but it also
/// announces when a session is established, i.e. right after our own
/// re-subscribe: the grace period is what keeps that from turning into a
/// re-subscribe loop, because the first report of a fresh subscription arrives
/// well within it.
const ANNOUNCE_GRACE: Duration = Duration::from_secs(5);

#[derive(Serialize, Deserialize)]
struct FabricMaterial {
    root: Vec<u8>,
    intermediate: Vec<u8>,
    signing_key: Vec<u8>,
    operational_key: Vec<u8>,
    noc: Vec<u8>,
    ipk: Vec<u8>,
}

fn save_json(path: &Path, value: &impl Serialize) -> std::io::Result<()> {
    let tmp = path.with_extension("tmp");
    let mut file = OpenOptions::new().write(true).create(true).truncate(true).mode(0o600).open(&tmp)?;
    file.set_permissions(fs::Permissions::from_mode(0o600))?;
    serde_json::to_writer(&mut file, value)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    fs::rename(tmp, path)?;
    File::open(path.parent().unwrap())?.sync_all()
}

fn make_fabric<C: Crypto>(crypto: &C) -> Result<FabricMaterial, Error> {
    let mut root_buf = [0; MAX_CERT_TLV_AND_ASN1_LEN];
    let mut root_gen = RcacGenerator::new(&mut root_buf);
    let (root_key, root) = root_gen.generate(crypto, FABRIC_ID, VALID_FOREVER)?;
    let mut intermediate_buf = [0; MAX_CERT_TLV_AND_ASN1_LEN];
    let mut intermediate_gen = IcacGenerator::new(&mut intermediate_buf);
    let (signing_key, intermediate) = intermediate_gen.generate(crypto, root_key.reference(), root, VALID_FOREVER)?;
    let operational_key = crypto.generate_secret_key()?;
    let mut csr_buf = [0; 256];
    let csr = operational_key.csr(&mut csr_buf)?;
    let mut canonical_key = CanonPkcSecretKey::new();
    operational_key.write_canon(&mut canonical_key)?;
    let mut noc_buf = [0; MAX_CERT_TLV_AND_ASN1_LEN];
    let mut generator = NocGenerator::create(signing_key.reference(), root, intermediate, &mut noc_buf)?;
    let noc = generator.generate(crypto, csr, CONTROLLER_ID, &[], VALID_FOREVER)?;
    let mut ipk = CanonAeadKey::new();
    crypto.rand()?.fill_bytes(ipk.access_mut());
    Ok(FabricMaterial {
        root: root.to_vec(), intermediate: intermediate.to_vec(),
        signing_key: signing_key.reference().access().to_vec(),
        operational_key: canonical_key.access().to_vec(), noc: noc.to_vec(), ipk: ipk.access().to_vec(),
    })
}

#[derive(Serialize, Deserialize, Clone)]
struct Node {
    node_id: u64,
    date_commissioned: String,
    last_interview: String,
    interview_version: u16,
    available: bool,
    is_bridge: bool,
    attributes: BTreeMap<String, Value>,
    attribute_subscriptions: Vec<Value>,
    #[serde(skip)]
    subscription: Option<(u32, Instant, u16)>,
    #[serde(skip)]
    retry_at: Option<Instant>,
    peer: SocketAddrV6,
    device_fabric_index: u8,
}

impl Node {
    fn wire(&self) -> Value {
        json!({"node_id":self.node_id,"date_commissioned":self.date_commissioned,
            "last_interview":self.last_interview,"interview_version":self.interview_version,
            "available":self.available,"is_bridge":self.is_bridge,"attributes":self.attributes,
            "attribute_subscriptions":self.attribute_subscriptions})
    }
}

struct Hub {
    nodes: RwLock<BTreeMap<u64, Node>>,
    clients: Mutex<Vec<Client>>,
    path: PathBuf,
    peer: SocketAddrV6,
    allow_test: bool,
    auto_local: bool,
    compressed_fabric_id: u64,
}

impl Hub {
    fn event(&self, event: &str, data: Value) {
        let message = json!({"event":event,"data":data});
        self.clients.lock().unwrap().retain(|client| {
            let sent = client.sender.try_send(message.clone()).is_ok();
            if !sent { client.sender.close(); }
            // Wake the connection thread (it is blocked in `poll`) only when there
            // is something to send, or when it has to notice that the channel is
            // gone: an explicit wake-up keeps the events immediate without polling.
            client.wake.wake();
            sent
        });
    }
    fn save(&self) -> Result<(), Error> {
        save_json(&self.path, &*self.nodes.read().unwrap()).map_err(|_| ErrorCode::Failure.into())
    }
    /// The peer announced its Matter service again on mDNS, i.e. it has
    /// (re)started: drop our subscription to it, so the watchdog of `commands`
    /// re-subscribes on its next tick instead of waiting for the periodic report
    /// to time out.
    ///
    /// The peer announced its Matter service again on mDNS: with this rs-matter
    /// revision (>= 4d4fd3a, "Stop broadcasting every 30s") the responder
    /// announces at startup and on changes only, so an announcement that arrives
    /// while our subscription is not fresh means the peer has (re)started: drop
    /// the subscription so the watchdog of `commands` re-subscribes on its next
    /// tick, instead of waiting for the periodic report to time out.
    ///
    /// A subscription whose reports still arrive is left alone (see
    /// [`ANNOUNCE_GRACE`]), and so is a healthy one when a reconnect attempt is
    /// already pending.
    fn peer_announced(&self) {
        let now = Instant::now();
        let mut nodes = self.nodes.write().unwrap();
        for node in nodes.values_mut() {
            if node.interview_version == 0 {
                continue;
            }
            let silent = node.subscription.map_or(true, |sub| sub.1.elapsed() > ANNOUNCE_GRACE);
            let retrying = node.retry_at.map_or(false, |when| now < when);
            if !silent && !retrying {
                continue;
            }
            log::info!("node {}: the peer re-announced itself while the subscription is not fresh; re-subscribing now", node.node_id);
            node.subscription = None;
            node.retry_at = Some(now);
        }
    }
    /// [`mdns::watch_peer`] callback for this hub.
    fn announcer(self: &Arc<Self>) -> mdns::PeerSeen {
        let hub = Arc::clone(self);
        Arc::new(move || hub.peer_announced())
    }
    fn node(&self, id: u64) -> Result<Node, Error> {
        self.nodes.read().unwrap().get(&id).cloned().ok_or(ErrorCode::NotFound.into())
    }
    fn report(&self, id: u64, report: &ReportDataResp<'_>) -> Result<(), Error> {
        if let Some(reports) = &report.attr_reports {
            for item in reports.iter() {
                if let AttrResp::Data(data) = item? {
                    let path = format!("{}/{}/{}", data.path.endpoint.ok_or(ErrorCode::InvalidData)?,
                        data.path.cluster.ok_or(ErrorCode::InvalidData)?, data.path.attr.ok_or(ErrorCode::InvalidData)?);
                    let value = tlv_json(&data.data, 0)?;
                    let changed = {
                        let mut nodes = self.nodes.write().unwrap();
                        let node = nodes.get_mut(&id).ok_or(ErrorCode::NotFound)?;
                        if let Some(index) = data.path.list_index {
                            let entry = node.attributes.entry(path.clone()).or_insert(json!([]));
                            let list = entry.as_array_mut().ok_or(ErrorCode::InvalidData)?;
                            if let Some(index) = index.into_option() {
                                let index = index as usize;
                                if index >= list.len() { return Err(ErrorCode::InvalidData.into()); }
                                list[index] = value.clone();
                            } else { list.push(value.clone()); }
                            true
                        } else {
                            node.attributes.insert(path.clone(), value.clone()).as_ref() != Some(&value)
                        }
                    };
                    if changed {
                        let actual = self.node(id)?.attributes[&path].clone();
                        self.event("attribute_updated", json!([id, path, actual]));
                    }
                }
            }
        }
        Ok(())
    }
}

fn tlv_json(element: &TLVElement<'_>, depth: usize) -> Result<Value, Error> {
    if depth > 32 { return Err(ErrorCode::InvalidData.into()); }
    Ok(match element.value()? {
        TLVValue::Null => Value::Null,
        TLVValue::True => json!(true), TLVValue::False => json!(false),
        TLVValue::S8(value) => json!(value), TLVValue::S16(value) => json!(value),
        TLVValue::S32(value) => json!(value), TLVValue::S64(value) => json!(value),
        TLVValue::U8(value) => json!(value), TLVValue::U16(value) => json!(value),
        TLVValue::U32(value) => json!(value), TLVValue::U64(value) => json!(value),
        TLVValue::F32(value) => json!(value), TLVValue::F64(value) => json!(value),
        TLVValue::Utf8l(value) | TLVValue::Utf16l(value) | TLVValue::Utf32l(value) | TLVValue::Utf64l(value) => json!(value),
        TLVValue::Str8l(value) | TLVValue::Str16l(value) | TLVValue::Str32l(value) | TLVValue::Str64l(value) => json!(STANDARD.encode(value)),
        TLVValue::Array => {
            let mut result = Vec::new();
            for child in element.array()?.iter() { result.push(tlv_json(&child?, depth + 1)?); }
            json!(result)
        }
        TLVValue::Struct | TLVValue::List => {
            let mut result = serde_json::Map::new();
            let sequence = if matches!(element.value()?, TLVValue::Struct) { element.structure()? } else { element.list()? };
            for child in sequence.iter() {
                let child = child?;
                let TLVTag::Context(tag) = child.tag()? else { return Err(ErrorCode::InvalidData.into()); };
                result.insert(tag.to_string(), tlv_json(&child, depth + 1)?);
            }
            Value::Object(result)
        }
        _ => return Err(ErrorCode::InvalidData.into()),
    })
}

fn json_tlv(writer: &mut impl TLVWrite, tag: &TLVTag, value: &Value) -> Result<(), Error> {
    match value {
        Value::Null => writer.null(tag),
        Value::Bool(value) => writer.bool(tag, *value),
        Value::Number(value) if value.is_u64() => writer.u64(tag, value.as_u64().unwrap()),
        Value::Number(value) if value.is_i64() => writer.i64(tag, value.as_i64().unwrap()),
        Value::Number(value) => writer.f64(tag, value.as_f64().ok_or(ErrorCode::InvalidData)?),
        Value::String(value) => writer.utf8(tag, value.as_str()),
        Value::Array(values) => {
            writer.start_array(tag)?;
            for value in values { json_tlv(writer, &TLVTag::Anonymous, value)?; }
            writer.end_container()
        }
        Value::Object(values) => {
            writer.start_struct(tag)?;
            let mut fields = values.iter().map(|(key,value)| Ok((key.parse::<u8>().map_err(|_| ErrorCode::InvalidData)?,value)))
                .collect::<Result<Vec<_>,Error>>()?;
            fields.sort_by_key(|(tag,_)| *tag);
            for (tag,value) in fields { json_tlv(writer, &TLVTag::Context(tag), value)?; }
            writer.end_container()
        }
    }
}

/// Serves the mDNS advertisement of this node and the resolve requests the
/// responder produces (`Transport::wait_mdns_resolve_request`).
async fn resolver<C: Crypto>(matter: &Matter<'_>, hub: &Hub, crypto: &C) -> Result<(), Error> {
    let _ = select(mdns::run_or_wait(matter, crypto), resolve_requests(matter, hub)).await;

    Ok(())
}

async fn resolve_requests(matter: &Matter<'_>, hub: &Hub) -> Result<(), Error> {
    loop {
        let service = matter.transport().wait_mdns_resolve_request().await;
        if let MatterRemoteService::Operational { node_id, .. } = &service {
            if let Ok(node) = hub.node(*node_id) {
                let mut name = heapless::String::<128>::new();
                service.instance_name(&mut name);
                matter.transport().try_deposit_mdns_resolve(&MdnsRemoteService {
                    instance_name: DottedName(name.as_str()), port: Some(node.peer.port()),
                    addrs: std::iter::once(IpAddr::V6(*node.peer.ip())),
                    txt: std::iter::empty::<(&str, &str)>(), scope_id: node.peer.scope_id(),
                }, &[]);
                log::debug!("mDNS resolve for node {node_id} answered with {}", node.peer);
            }
        }
    }
}

async fn interview<C: Crypto>(matter: &Matter<'_>, crypto: &C, fab: NonZeroU8, hub: &Hub, id: u64) -> Result<(), Error> {
    let exchange = Exchange::initiate(matter, crypto, fab, id).await?;
    let mut chunk = exchange.read_with(|builder| builder.attr_requests_from(&[AttrPath::default()])?.fabric_filtered(true)?.end()).await?;
    loop {
        hub.report(id, &chunk.response()?)?;
        match chunk.complete().await? { Some(next) => chunk = next, None => break }
    }
    {
        let mut nodes = hub.nodes.write().unwrap();
        let node = nodes.get_mut(&id).ok_or(ErrorCode::NotFound)?;
        node.last_interview = timestamp();
        node.interview_version = 6;
        node.available = true;
    }
    hub.save()?;
    Ok(())
}

async fn subscribe<C: Crypto>(matter: &Matter<'_>, crypto: &C, fab: NonZeroU8, hub: &Hub, id: u64) -> Result<(), Error> {
    let exchange = Exchange::initiate(matter, crypto, fab, id).await?;
    let mut chunk = exchange.subscribe_with(|builder| builder.keep_subs(false)?.min_int_floor(1)?.max_int_ceil(30)?
        .attr_requests_from(&[AttrPath::default()])?.fabric_filtered(true)?.end()).await?;
    loop {
        hub.report(id, &chunk.response()?)?;
        match chunk.complete().await? {
            SubscribeOutcome::NextChunk(next) => chunk = next,
            SubscribeOutcome::Established(subscription) => {
                let mut nodes = hub.nodes.write().unwrap();
                let node = nodes.get_mut(&id).ok_or(ErrorCode::NotFound)?;
                node.subscription = Some((subscription.subscription_id, Instant::now(), subscription.max_int));
                node.available = true;
                node.retry_at = None;
                break;
            }
        }
    }
    hub.event("node_updated", hub.node(id)?.wire());
    Ok(())
}

async fn reports(matter: &Matter<'_>, hub: &Hub) -> Result<(), Error> {
    loop {
        let mut exchange = Exchange::accept(matter).await?;
        let result: Result<(), Error> = async {
            loop {
                let (more, suppress) = {
                    let rx = exchange.recv().await?;
                    rx.meta().check_opcode(OpCode::ReportData)?;
                    let report = ReportDataResp::from_tlv(&TLVElement::new(rx.payload()))?;
                    let sub_id = report.subscription_id.ok_or(ErrorCode::InvalidData)?;
                    let id = hub.nodes.read().unwrap().values().find(|node| node.subscription.map(|sub| sub.0) == Some(sub_id))
                        .map(|node| node.node_id).ok_or(ErrorCode::NotFound)?;
                    hub.report(id, &report)?;
                    if let Some(sub) = hub.nodes.write().unwrap().get_mut(&id).unwrap().subscription.as_mut() { sub.1 = Instant::now(); }
                    (report.more_chunks.unwrap_or(false), report.suppress_response.unwrap_or(false))
                };
                if !suppress {
                    exchange.send_with(|_, writer| {
                        StatusResp::write(writer, IMStatusCode::Success)?;
                        Ok(Some(OpCode::StatusResponse.into()))
                    }).await?;
                } else { exchange.acknowledge().await?; }
                if !more { break; }
            }
            Ok(())
        }.await;
        if let Err(error) = result { log::warn!("subscription report: {error}"); }
    }
}

fn timestamp() -> String {
    time::OffsetDateTime::now_utc().format(&time::format_description::well_known::Rfc3339).unwrap()
}

fn server_info(hub: &Hub) -> Value {
    json!({"fabric_id":FABRIC_ID,"compressed_fabric_id":hub.compressed_fabric_id,"schema_version":11,"min_supported_schema_version":9,
        "sdk_version":"rs-matter-0.4.1","wifi_credentials_set":false,"thread_credentials_set":false,"bluetooth_enabled":false})
}

/// A request coming from a WebSocket client, with the channel its reply has to be
/// queued on and the pipe of that connection: a queued reply must wake the
/// connection thread, which is otherwise blocked in `poll()` (it waits for the
/// socket and for the pipe), or the reply would only be written when the next
/// event happens to arrive.
struct Request { message: Value, reply: Sender<Value>, wake: Option<Arc<WakePipe>> }

/// One WebSocket client: the channel its events are queued on, plus the pipe the
/// connection thread is woken with when an event has to be written.
struct Client { sender: Sender<Value>, wake: Arc<WakePipe> }

/// A pipe used to wake a thread that is blocked in `poll()` on a socket.
///
/// The WebSocket connection thread serves both the socket (commands from
/// Domoticz) and the outgoing event channel. With a non-blocking socket and
/// `Thread::park_timeout` the thread wakes up once per timeout even when nothing
/// happens: measured 100 wake-ups/s and 4.3% of a CPU core per connected client
/// with a 10 ms timeout, more than everything else the daemon does. Blocking in
/// `poll()` on the socket and on this pipe instead costs nothing while idle and
/// still writes events immediately.
struct WakePipe { read: RawFd, write: RawFd }

impl WakePipe {
    fn new() -> Option<Self> {
        let mut fds = [0i32; 2];
        if unsafe { libc::pipe(fds.as_mut_ptr()) } != 0 {
            return None;
        }
        for fd in fds {
            unsafe { libc::fcntl(fd, libc::F_SETFL, libc::O_NONBLOCK) };
        }
        Some(Self { read: fds[0], write: fds[1] })
    }
    /// Wake a thread blocked in [`wait`](Self::wait).
    fn wake(&self) {
        // A full pipe is not a problem: it is drained on the next wake-up and the
        // pending byte makes `poll` return immediately anyway.
        unsafe { libc::write(self.write, b"w".as_ptr().cast(), 1) };
    }
    /// Block until the socket has something to read or [`wake`](Self::wake) has
    /// been called; `false` when the wait itself failed.
    fn wait(&self, socket: &TcpStream) -> bool {
        let mut fds = [
            libc::pollfd { fd: socket.as_raw_fd(), events: libc::POLLIN, revents: 0 },
            libc::pollfd { fd: self.read, events: libc::POLLIN, revents: 0 },
        ];
        if unsafe { libc::poll(fds.as_mut_ptr(), 2, -1) } < 0 {
            return false;
        }
        if fds[1].revents != 0 {
            let mut buffer = [0u8; 64];
            while unsafe { libc::read(self.read, buffer.as_mut_ptr().cast(), buffer.len()) } > 0 {}
        }
        // On POLLERR/POLLHUP the caller reads the socket as well and sees the
        // error, which closes the connection.
        true
    }
}

impl Drop for WakePipe {
    fn drop(&mut self) {
        unsafe {
            libc::close(self.read);
            libc::close(self.write);
        }
    }
}

fn websocket(listener: TcpListener, hub: Arc<Hub>, requests: Sender<Request>) {
    for stream in listener.incoming() {
        let Ok(stream) = stream else { continue; };
        let hub = hub.clone(); let requests = requests.clone();
        std::thread::spawn(move || {
            let _ = stream.set_read_timeout(Some(Duration::from_secs(5)));
            let _ = stream.set_write_timeout(Some(Duration::from_secs(5)));
            let Ok(mut socket) = tungstenite::accept(stream) else { return; };
            if socket.send(Message::Text(server_info(&hub).to_string().into())).is_err() { return; }
            let _ = socket.get_mut().set_nonblocking(true);
            let (send, receive) = async_channel::bounded::<Value>(256);
            let Some(wake) = WakePipe::new().map(Arc::new) else { return; };
            let mut listening = false;
            loop {
                while let Ok(message) = receive.try_recv() {
                    if socket.write(Message::Text(message.to_string().into())).is_err() { return; }
                }
                match socket.flush() {
                    Ok(()) => (), Err(WsError::Io(ref error)) if error.kind() == std::io::ErrorKind::WouldBlock => (), _ => return,
                }
                if !wake.wait(socket.get_ref()) { break; }
                match socket.read() {
                    Ok(Message::Text(text)) => {
                        let Ok(message) = serde_json::from_str::<Value>(&text) else { break; };
                        if message["command"] == "start_listening" && !listening {
                            hub.clients.lock().unwrap().push(Client { sender: send.clone(), wake: Arc::clone(&wake) });
                            listening = true;
                        }
                        if requests.try_send(Request { message, reply: send.clone(), wake: Some(Arc::clone(&wake)) }).is_err() { break; }
                    }
                    Ok(Message::Close(_)) => break,
                    Ok(_) => (),
                    Err(WsError::Io(ref error)) if error.kind() == std::io::ErrorKind::WouldBlock => (),
                    Err(_) => break,
                }
                if receive.is_closed() { break; }
            }
            send.close();
        });
    }
}

async fn execute<C: Crypto>(matter: &Matter<'_>, crypto: &C, fab: NonZeroU8, material: &FabricMaterial, hub: &Hub, message: &Value) -> Result<Value, Error> {
    match message["command"].as_str().unwrap_or("") {
        "start_listening" | "get_nodes" => Ok(json!(hub.nodes.read().unwrap().values().map(Node::wire).collect::<Vec<_>>())),
        "server_info" | "get_server_info" => Ok(server_info(hub)),
        "commission_with_code" | "commission_on_network" | "commission_local" => {
            let args = &message["args"];
            let passcode = if let Some(code) = args["code"].as_str() {
                if code.starts_with("MT:") {
                    let mut scratch = [0; 1024];
                    rs_matter::pairing::qr::QrPayload::parse(code, &mut scratch)?.passcode()
                } else {
                    rs_matter::pairing::qr::QrPayload::parse_pairing_code(code)?.passcode()
                }
            } else { args["setup_pin_code"].as_u64().ok_or(ErrorCode::InvalidData)? as u32 };
            let peer = if let Some(ip) = args["ip_addr"].as_str() {
                SocketAddrV6::new(ip.parse().map_err(|_| ErrorCode::InvalidData)?, hub.peer.port(), 0, 0)
            } else { hub.peer };
            if !peer.ip().is_loopback() && !hub.allow_test { return Err(ErrorCode::Failure.into()); }
            let existing = hub.nodes.read().unwrap().values().find(|node| node.peer == peer).cloned();
            if let Some(existing) = &existing {
                if existing.interview_version > 0 { return Ok(existing.wire()); }
            }
            let id = existing.as_ref().map(|node|node.node_id).unwrap_or_else(||
                hub.nodes.read().unwrap().keys().max().copied().unwrap_or(0) + 1);
            if existing.is_none() { hub.nodes.write().unwrap().insert(id, Node {
                node_id: id, date_commissioned:timestamp(),last_interview:timestamp(),interview_version:0,
                available:false,is_bridge:false,attributes:BTreeMap::new(),attribute_subscriptions:Vec::new(),
                subscription:None,retry_at:None,peer,device_fabric_index:0,
            }); }
            let mut key = CanonPkcSecretKey::new();
            key.access_mut().copy_from_slice(&material.signing_key);
            let mut noc_buf = [0; MAX_CERT_TLV_AND_ASN1_LEN];
            let mut generator = NocGenerator::new(matter, key.reference(), fab, &mut noc_buf)?;
            let mut scratch = [0; MAX_CERT_TLV_LEN];
            let mut commissioner = Commissioner::new(matter, crypto, fab, &mut generator, &mut scratch);
            let options = CommissionOptions { allow_test_attestation:true,..Default::default() };
            let result = if let Some(index) = existing.as_ref().and_then(|node|NonZeroU8::new(node.device_fabric_index)) {
                rs_matter::onboard::CommissionResult {fabric_index:index,device_node_id:id}
            } else {
                match commissioner.commission(Address::Udp(SocketAddr::V6(peer)),passcode,&options,id,VALID_FOREVER).await {
                    Ok(result) => result,
                    Err(error) => { hub.nodes.write().unwrap().remove(&id); return Err(error); }
                }
            };
            hub.nodes.write().unwrap().get_mut(&id).unwrap().device_fabric_index = result.fabric_index.get();
            hub.save()?;
            commissioner.complete_via_case(&result).await?;
            hub.save()?;
            interview(matter,crypto,fab,hub,id).await?;
            hub.event("node_added",hub.node(id)?.wire());
            subscribe(matter,crypto,fab,hub,id).await?;
            Ok(hub.node(id)?.wire())
        }
        "device_command" => {
            let args = &message["args"];
            let id = args["node_id"].as_u64().ok_or(ErrorCode::InvalidData)?;
            hub.node(id)?;
            let endpoint = u16::try_from(args["endpoint_id"].as_u64().ok_or(ErrorCode::InvalidData)?).map_err(|_| ErrorCode::InvalidData)?;
            let cluster = u32::try_from(args["cluster_id"].as_u64().ok_or(ErrorCode::InvalidData)?).map_err(|_| ErrorCode::InvalidData)?;
            let name = args["command_name"].as_str().ok_or(ErrorCode::InvalidData)?;
            let payload = &args["payload"];
            let (command, fields) = match (cluster, name) {
                (6,"Off") => (0,json!({})),
                (6,"On") => (1,json!({})),
                (6,"Toggle") => (2,json!({})),
                (8,"MoveToLevel") | (8,"MoveToLevelWithOnOff") => {
                    let level = payload["level"].as_u64().or_else(||payload["Level"].as_u64()).ok_or(ErrorCode::InvalidData)?;
                    if level > 254 { return Err(ErrorCode::InvalidData.into()); }
                    (if name == "MoveToLevel" {0} else {4},json!({"0":level,
                        "1":payload["transitionTime"].as_u64().unwrap_or(0),
                        "2":payload["optionsMask"].as_u64().unwrap_or(0),
                        "3":payload["optionsOverride"].as_u64().unwrap_or(0)}))
                }
                (3,"Identify") => (0,json!({"0":payload["identifyTime"].as_u64().unwrap_or(0)})),
                _ => return Err(ErrorCode::InvalidCommand.into()),
            };
            let exchange = Exchange::initiate(matter,crypto,fab,id).await?;
            let mut chunk = exchange.invoke_with(None,|builder| builder.invoke_requests()?.push()?
                .path(endpoint,cluster,command)?.data(|writer|json_tlv(writer,&TLVTag::Context(1),&fields))?
                .end()?.end()?.end()).await?;
            loop {
                if let Some(response) = chunk.response()? {
                    if let Some(responses) = response.invoke_responses {
                        for item in responses.iter() {
                            if let rs_matter::im::CmdResp::Status(status) = item? {
                                if status.status.status != IMStatusCode::Success { return Err(ErrorCode::Failure.into()); }
                            }
                        }
                    }
                }
                match chunk.complete().await? {Some(next)=>chunk=next,None=>break}
            }
            interview(matter,crypto,fab,hub,id).await?;
            Ok(Value::Null)
        }
        "write_attribute" => {
            let args = &message["args"];
            let id = args["node_id"].as_u64().ok_or(ErrorCode::InvalidData)?;
            hub.node(id)?;
            let path = args["attribute_path"].as_str().ok_or(ErrorCode::InvalidData)?.split('/')
                .map(|part|part.parse::<u32>().map_err(|_| ErrorCode::InvalidData.into())).collect::<Result<Vec<_>,Error>>()?;
            if path.len()!=3 || path[0]>u16::MAX as u32 {return Err(ErrorCode::InvalidData.into());}
            let exchange = Exchange::initiate(matter,crypto,fab,id).await?;
            let response = exchange.write_with(None,|builder|builder.write_requests()?.push()?
                .path(path[0] as u16,path[1],path[2])?.data(|writer|json_tlv(writer,&TLVTag::Context(2),&args["value"]))?
                .end()?.end()?.end()).await?;
            for status in response.response()?.write_responses.iter() {
                if status?.status.status!=IMStatusCode::Success {return Err(ErrorCode::Failure.into());}
            }
            drop(response);
            interview(matter,crypto,fab,hub,id).await?;
            Ok(Value::Null)
        }
        "get_node" => Ok(hub.node(message["args"]["node_id"].as_u64().ok_or(ErrorCode::InvalidData)?)?.wire()),
        "get_node_ip_addresses" => Ok(json!([hub.node(message["args"]["node_id"].as_u64().ok_or(ErrorCode::InvalidData)?)?.peer.ip().to_string()])),
        "interview_node" => {
            let id = message["args"]["node_id"].as_u64().ok_or(ErrorCode::InvalidData)?;
            interview(matter,crypto,fab,hub,id).await?;
            Ok(hub.node(id)?.wire())
        }
        "read_attribute" => {
            let id = message["args"]["node_id"].as_u64().ok_or(ErrorCode::InvalidData)?;
            interview(matter,crypto,fab,hub,id).await?;
            Ok(hub.node(id)?.attributes.get(message["args"]["attribute_path"].as_str().ok_or(ErrorCode::InvalidData)?)
                .cloned().ok_or(ErrorCode::NotFound)?)
        }
        _ => Err(ErrorCode::InvalidCommand.into()),
    }
}

async fn commands<C: Crypto>(matter: &Matter<'_>, crypto: &C, fab: NonZeroU8, material: &FabricMaterial, hub: &Hub, receiver: Receiver<Request>) -> Result<(), Error> {
    let mut auto_retry = Instant::now();
    let mut next_tick = Instant::now() + WATCHDOG_TICK;
    loop {
        let tick = async_io::Timer::at(next_tick);
        match select(receiver.recv(), tick).await {
            Either::First(Ok(request)) => {
                let timeout = async_io::Timer::after(Duration::from_secs(120));
                let result = match select(execute(matter,crypto,fab,material,hub,&request.message), timeout).await {
                    Either::First(result) => result,
                    Either::Second(_) => Err(ErrorCode::RxTimeout.into()),
                };
                let response = match result {
                    Ok(result) => json!({"message_id":request.message["message_id"],"result":result}),
                    Err(error) => {
                        log::warn!("{}: {error}",request.message["command"]);
                        let code = match error.code() {
                            ErrorCode::NotFound => 5,
                            ErrorCode::InvalidData | ErrorCode::Invalid => 8,
                            ErrorCode::InvalidCommand => 9,
                            _ => 0,
                        };
                        json!({"message_id":request.message["message_id"],"error_code":code,"details":error.to_string()})
                    }
                };
                let _ = request.reply.try_send(response);
                if let Some(wake) = &request.wake { wake.wake(); }
            }
            Either::First(Err(_)) => return Err(ErrorCode::Failure.into()),
            Either::Second(_) => {
                next_tick = Instant::now() + WATCHDOG_TICK;
                log::debug!("watchdog tick");
                let needs_local = hub.auto_local && hub.peer.ip().is_loopback()
                    && !hub.nodes.read().unwrap().values().any(|node|node.peer==hub.peer && node.interview_version>0);
                if needs_local && Instant::now() >= auto_retry {
                    let message = json!({"command":"commission_local","args":{"setup_pin_code":20202021}});
                    match select(execute(matter,crypto,fab,material,hub,&message),async_io::Timer::after(Duration::from_secs(90))).await {
                        Either::First(Ok(_)) => log::info!("Local freetz-matter commissioned; Domoticz can connect on port 5580"),
                        _ => log::warn!("Local commissioning not ready; retrying in 30 seconds (device must have an open commissioning window)"),
                    }
                    auto_retry = Instant::now() + Duration::from_secs(30);
                }
                let ids = hub.nodes.read().unwrap().values().filter(|node| node.interview_version > 0
                    && node.retry_at.map_or(true,|when| Instant::now() >= when)
                    && node.subscription.map_or(true,|sub| sub.1.elapsed().as_secs() > sub.2 as u64 + 5))
                    .map(|node| node.node_id).collect::<Vec<_>>();
                log::debug!("watchdog: {} node(s) to (re)subscribe", ids.len());
                for id in ids {
                    log::debug!("node {id}: subscription missing or silent, reconnecting");
                    let result = select(subscribe(matter,crypto,fab,hub,id),async_io::Timer::after(Duration::from_secs(25))).await;
                    let mut nodes = hub.nodes.write().unwrap();
                    let node = nodes.get_mut(&id).unwrap();
                    match result {
                        Either::First(Ok(())) => log::info!("node {id}: subscription re-established"),
                        Either::First(Err(error)) => {
                            // A peer that has just restarted has no session yet: retry on the
                            // next tick instead of waiting for the backoff.
                            let delay = if error.code() == ErrorCode::NoSession { 5 } else { 15 };
                            log::warn!("node {id}: reconnect failed ({error:?}); retrying in {delay} seconds");
                            node.available = false;
                            node.retry_at = Some(Instant::now() + Duration::from_secs(delay));
                        }
                        Either::Second(_) => {
                            log::warn!("node {id}: no CASE session within 25 s; retrying in 15 seconds");
                            node.available = false;
                            node.retry_at = Some(Instant::now() + Duration::from_secs(15));
                        }
                    }
                    let wire = node.wire(); drop(nodes);
                    hub.event("node_updated",wire);
                }
            }
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));
    let mut port = 5580u16;
    let mut bind = "127.0.0.1".parse::<IpAddr>()?;
    let mut store = PathBuf::from("/tmp/flash/matter-bridge");
    let mut peer: SocketAddrV6 = "[::1]:5540".parse()?;
    let mut allow_test = false;
    let mut auto_local = false;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-p" | "--port" => port = args.next().ok_or("missing port")?.parse()?,
            "--bind" => bind = args.next().ok_or("missing bind address")?.parse()?,
            "--store" => store = args.next().ok_or("missing store")?.into(),
            "--peer" => peer = args.next().ok_or("missing peer")?.parse()?,
            "--allow-test-attestation" => allow_test = true,
            "--auto-local" => auto_local = true,
            "-h" | "--help" => { println!("matter-bridge [--port 5580] [--bind 127.0.0.1] [--store /tmp/flash/matter-bridge] [--peer '[::1]:5540'] [--auto-local]"); return Ok(()); }
            _ => return Err(format!("unknown option {arg}").into()),
        }
    }
    fs::create_dir_all(&store)?;
    fs::set_permissions(&store,fs::Permissions::from_mode(0o700))?;
    let crypto = default_crypto(rand::rng(),DAC_PRIVKEY);
    let fabric_path = store.join("fabric.json");
    let material: FabricMaterial = if fabric_path.exists() {
        serde_json::from_reader(File::open(&fabric_path)?)?
    } else {
        let material = make_fabric(&crypto)?;
        save_json(&fabric_path,&material)?;
        material
    };
    let mut key = CanonPkcSecretKey::new();
    if material.operational_key.len() != key.access().len() || material.signing_key.len() != key.access().len() || material.ipk.len() != 16 {
        return Err("invalid persisted fabric material; refusing to replace it".into());
    }
    key.access_mut().copy_from_slice(&material.operational_key);
    let mut ipk = CanonAeadKey::new(); ipk.access_mut().copy_from_slice(&material.ipk);
    let matter = Matter::new(&TEST_DEV_DET,TEST_DEV_COMM,&TEST_DEV_ATT,0);
    let fab = matter.with_state(|state| state.fabrics.add(&crypto,key.reference(),&material.root,&material.noc,&material.intermediate,
        Some(ipk.reference()),0xfff1,CONTROLLER_ID).map(|fabric|fabric.fab_idx()))?;
    let compressed_fabric_id = matter.with_state(|state| state.fabrics.fabric(fab).map(|fabric|fabric.compressed_fabric_id()))?;
    let nodes_path = store.join("controller-nodes.json");
    let mut nodes: BTreeMap<u64,Node> = if nodes_path.exists() { serde_json::from_reader(File::open(&nodes_path)?)? } else { BTreeMap::new() };
    for node in nodes.values_mut() { node.available = false; }
    let hub = Arc::new(Hub { nodes:RwLock::new(nodes),clients:Mutex::new(Vec::new()),path:nodes_path,peer,allow_test,auto_local,compressed_fabric_id });
    let (send,receive) = async_channel::bounded(32);
    let listener = TcpListener::bind((bind,port))?;
    let ws_hub = hub.clone();
    std::thread::spawn(move || websocket(listener,ws_hub,send));
    mdns::spawn_peer_watch(mdns::PEER_HOSTNAME,hub.announcer());
    let udp_bind = if peer.ip().is_loopback() { "[::1]:0" } else { "[::]:0" };
    let socket = async_io::Async::<UdpSocket>::bind(udp_bind.parse::<SocketAddr>()?)?;
    log::info!("WebSocket :{port}/ws; local Matter device {peer}; fabric loaded from {}",fabric_path.display());
    futures_lite::future::block_on(select4(matter.run(&crypto,&socket,&socket,NoNetwork),resolver(&matter,&hub,&crypto),
        reports(&matter,&hub),commands(&matter,&crypto,fab,&material,&hub,receive)).coalesce())?;
    Ok(())
}