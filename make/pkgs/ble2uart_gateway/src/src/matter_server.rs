use crate::config::{DeviceConfig, MatterConfig};
use crate::matter::{
    endpoint_ids, MatterPublisher, SharedStates, Standard, JSON_CHUNK_BYTES, VENDOR_CLUSTER,
};
use rs_matter::crypto::{default_crypto, Crypto};
use rs_matter::dm::clusters::desc::{self, ClusterHandler as _};
use rs_matter::dm::devices::test::{DAC_PRIVKEY, TEST_DEV_ATT, TEST_DEV_COMM, TEST_DEV_DET};
use rs_matter::dm::networks::{eth::EthNetwork, SysNetifs};
use rs_matter::dm::{
    Access, Async, Attribute, Cluster, Dataver, DeviceType, Endpoint, Handler, HandlerContext,
    MatchContext, Node, NonBlockingHandler, Quality, ReadContext, ReadReply, Reply,
};
use rs_matter::error::{Error, ErrorCode};
use rs_matter::im::{EthInteractionModelState, InteractionModel};
use rs_matter::pairing::{qr::QrTextType, DiscoveryCapabilities};
use rs_matter::persist::DirKvBlobStore;
use rs_matter::respond::DefaultResponder;
use rs_matter::sc::pase::MAX_COMM_WINDOW_TIMEOUT_SECS;
use rs_matter::tlv::{Nullable, OctetStr, TLVTag, TLVWrite};
use rs_matter::transport::exchange::MatterBuffers;
use rs_matter::utils::select::Coalesce;
use rs_matter::{attributes, root_endpoint, Matter};
use std::collections::BTreeMap;
use std::net::UdpSocket;
use std::path::Path;
use std::pin::pin;
use std::sync::{Arc, Mutex};
use std::time::Duration;

const ROOT_ENDPOINT: Endpoint<'static> = root_endpoint!(eth);

#[derive(Clone)]
struct Entry {
    endpoint: u16,
    parent: u16,
    mac: String,
    label: String,
    metadata: crate::config::DeviceMetadata,
    attribute: Option<String>,
    standard: Option<Standard>,
}

fn permanent<T: 'static>(values: Vec<T>) -> &'static [T] {
    Box::leak(values.into_boxed_slice())
}

fn cluster(id: u32, attributes: &[Attribute]) -> Cluster<'static> {
    Cluster::new(
        id,
        1,
        0,
        permanent(attributes.to_vec()),
        &[],
        &[],
        |_, _, _| true,
        |_, _, _| false,
        |_, _, _| false,
    )
}

fn value_cluster(kind: Standard) -> Cluster<'static> {
    if matches!(kind, Standard::BatteryPercent | Standard::BatteryVoltage) {
        cluster(
            kind.cluster(),
            attributes!(
                Attribute::new(0, Access::RV, Quality::NONE),
                Attribute::new(1, Access::RV, Quality::NONE),
                Attribute::new(2, Access::RV, Quality::NONE),
                Attribute::new(11, Access::RV, Quality::NONE),
                Attribute::new(12, Access::RV, Quality::NONE),
                Attribute::new(14, Access::RV, Quality::NONE),
                Attribute::new(15, Access::RV, Quality::NONE),
                Attribute::new(16, Access::RV, Quality::NONE),
                Attribute::new(17, Access::RV, Quality::NONE),
                Attribute::new(31, Access::RV, Quality::A)
            ),
        )
        .with_features(2)
    } else if kind == Standard::Boolean {
        cluster(
            kind.cluster(),
            attributes!(Attribute::new(0, Access::RV, Quality::NONE)),
        )
    } else {
        cluster(
            kind.cluster(),
            attributes!(
                Attribute::new(0, Access::RV, Quality::NONE),
                Attribute::new(1, Access::RV, Quality::NONE),
                Attribute::new(2, Access::RV, Quality::NONE)
            ),
        )
    }
}

fn vendor_cluster() -> Cluster<'static> {
    cluster(
        VENDOR_CLUSTER,
        attributes!(
            Attribute::new(0, Access::RV, Quality::NONE),
            Attribute::new(1, Access::RV, Quality::NONE),
            Attribute::new(2, Access::RV, Quality::NONE),
            Attribute::new(3, Access::RV, Quality::A),
            Attribute::new(4, Access::RV, Quality::NONE)
        ),
    )
}

fn bridged_info(metadata: &crate::config::DeviceMetadata) -> Cluster<'static> {
    let mut attributes = attributes!(
        Attribute::new(5, Access::RV, Quality::NONE),
        Attribute::new(0x11, Access::RV, Quality::NONE),
        Attribute::new(0x12, Access::RV, Quality::NONE)
    ).to_vec();
    for (id, value) in [(1, &metadata.manufacturer), (3, &metadata.model), (10, &metadata.firmware_version)] {
        if !value.is_empty() {
            attributes.push(Attribute::new(id, Access::RV, Quality::NONE));
        }
    }
    cluster(0x0039, &attributes)
}

fn info_text(entry: &Entry, attribute: u32) -> Option<&str> {
    let (text, limit) = match attribute {
        1 if !entry.metadata.manufacturer.is_empty() => (&entry.metadata.manufacturer, 32),
        3 if !entry.metadata.model.is_empty() => (&entry.metadata.model, 32),
        5 => (&entry.label, 32),
        10 if !entry.metadata.firmware_version.is_empty() => (&entry.metadata.firmware_version, 64),
        _ => return None,
    };
    Some(crate::config::truncate_utf8(text, limit))
}

fn model(
    config: &MatterConfig,
    devices: &[DeviceConfig],
) -> Result<(Node<'static>, Vec<Entry>), String> {
    let mut keys = Vec::new();
    for device in devices {
        let mac = crate::pipeline::normalize_mac(&device.mac);
        keys.push(mac.clone());
        for expose in &device.expose {
            if Standard::for_attribute(&expose.attribute).is_some() {
                keys.push(format!("{mac}/{}", expose.attribute));
            }
        }
    }
    let ids = endpoint_ids(Path::new(&config.store), &keys)?;
    let mut entries = Vec::new();
    let mut endpoints = vec![
        ROOT_ENDPOINT,
        Endpoint::new(
            1,
            permanent(vec![DeviceType {
                dtype: 0x000E,
                drev: 1,
            }]),
            permanent(vec![desc::DescHandler::CLUSTER]),
        ),
    ];
    for device in devices.iter().filter(|device| device.enabled) {
        let mac = crate::pipeline::normalize_mac(&device.mac);
        let parent = ids[&mac];
        let metadata = device.metadata();
        let label = metadata.name.clone();
        entries.push(Entry {
            endpoint: parent,
            parent: 1,
            mac: mac.clone(),
            label: label.clone(),
            metadata: metadata.clone(),
            attribute: None,
            standard: None,
        });
        endpoints.push(Endpoint::new(
            parent,
            permanent(vec![DeviceType {
                dtype: 0x0013,
                drev: 1,
            }]),
            permanent(vec![
                desc::DescHandler::CLUSTER,
                bridged_info(&metadata),
                vendor_cluster(),
            ]),
        ));
        let mut seen = std::collections::HashSet::new();
        for expose in &device.expose {
            let Some(kind) = Standard::for_attribute(&expose.attribute) else {
                continue;
            };
            if !seen.insert(expose.attribute.clone()) {
                continue;
            }
            let endpoint = ids[&format!("{mac}/{}", expose.attribute)];
            let device_type = match kind {
                Standard::Temperature => 0x0302,
                Standard::Humidity => 0x0307,
                Standard::Pressure => 0x0305,
                Standard::Illuminance => 0x0106,
                Standard::Occupancy => 0x0107,
                Standard::Boolean
                    if matches!(expose.attribute.as_str(), "opened" | "contact" | "door") =>
                {
                    0x0015
                }
                Standard::Boolean => 0x0013,
                Standard::BatteryPercent | Standard::BatteryVoltage => 0x0011,
            };
            entries.push(Entry {
                endpoint,
                parent,
                mac: mac.clone(),
                label: metadata.resource_name(&expose.attribute),
                metadata: metadata.clone(),
                attribute: Some(expose.attribute.clone()),
                standard: Some(kind),
            });
            endpoints.push(Endpoint::new(
                endpoint,
                permanent(vec![
                    DeviceType {
                        dtype: 0x0013,
                        drev: 1,
                    },
                    DeviceType {
                        dtype: device_type,
                        drev: 1,
                    },
                ]),
                permanent(vec![
                    desc::DescHandler::CLUSTER,
                    bridged_info(&metadata),
                    value_cluster(kind),
                ]),
            ));
        }
    }
    Ok((
        Node {
            endpoints: permanent(endpoints),
        },
        entries,
    ))
}

#[derive(Debug)]
struct Parts(BTreeMap<u16, u16>);
impl rs_matter::utils::sync::DynBase for Parts {}
impl desc::PartsMatcher for Parts {
    fn matches(&self, parent: u16, endpoint: u16) -> bool {
        if parent == 0 {
            endpoint == 1
        } else {
            self.0.get(&endpoint) == Some(&parent)
        }
    }
}

struct BleHandler {
    states: SharedStates,
    entries: Vec<Entry>,
    node: Node<'static>,
    epoch: u32,
}

impl NonBlockingHandler for BleHandler {}

fn write_json_chunks(
    mut reply: impl Reply,
    index: Option<&Nullable<u16>>,
    data: &[u8],
) -> Result<(), Error> {
    match index.map(|index| index.as_opt_ref()) {
        Some(Some(index)) => reply.set(OctetStr::new(
            data.chunks(JSON_CHUNK_BYTES)
                .nth(usize::from(*index))
                .ok_or(ErrorCode::ConstraintError)?,
        )),
        index => {
            let tag = reply.tag().clone();
            let mut writer = reply.writer();
            writer.start_array(&tag)?;
            if index.is_none() {
                for chunk in data.chunks(JSON_CHUNK_BYTES) {
                    writer.str(&TLVTag::Anonymous, chunk)?;
                }
            }
            writer.end_container()?;
            drop(writer);
            reply.complete()
        }
    }
}

impl Handler for BleHandler {
    fn read(&self, ctx: impl ReadContext, reply: impl ReadReply) -> Result<(), Error> {
        let attr = ctx.attr();
        let entry = self
            .entries
            .iter()
            .find(|entry| entry.endpoint == attr.endpoint_id)
            .ok_or(ErrorCode::AttributeNotFound)?;
        let states = self.states.lock().unwrap();
        let snapshot = states.get(&entry.mac);
        let version = self
            .epoch
            .wrapping_add(snapshot.map(|snapshot| snapshot.version).unwrap_or(0));
        let Some(mut reply) = reply.with_dataver(version)? else {
            return Ok(());
        };
        if attr.is_system() {
            return self
                .node
                .endpoint(attr.endpoint_id)
                .and_then(|endpoint| endpoint.cluster(attr.cluster_id))
                .ok_or(ErrorCode::ClusterNotFound)?
                .read(attr, reply);
        }
        if attr.cluster_id == 0x0039 {
            if let Some(text) = info_text(entry, attr.attr_id) {
                return reply.set(text);
            }
            return match attr.attr_id {
                0x11 => reply.set(snapshot.is_some_and(|snapshot| {
                    match (&entry.attribute, entry.standard) {
                        (Some(name), Some(kind)) => snapshot.value["latest_values"]
                            .get(name)
                            .and_then(|measurement| {
                                kind.convert_unit(
                                    &measurement["value"],
                                    measurement["unit"].as_str().unwrap_or(""),
                                )
                            })
                            .is_some(),
                        _ => true,
                    }
                })),
                0x12 => reply.set(format!("ble-{}-{}", entry.mac, entry.endpoint).as_str()),
                _ => Err(ErrorCode::AttributeNotFound.into()),
            };
        }
        if attr.cluster_id == VENDOR_CLUSTER {
            let data = snapshot
                .map(|snapshot| snapshot.json.as_slice())
                .unwrap_or(b"{}");
            return match attr.attr_id {
                0 => reply.set(1u16),
                1 => reply.set(version),
                2 => reply.set(data.len() as u32),
                4 => reply.set(entry.mac.as_str()),
                3 => write_json_chunks(reply, attr.list_index.as_ref(), data),
                _ => Err(ErrorCode::AttributeNotFound.into()),
            };
        }
        let kind = entry.standard.ok_or(ErrorCode::ClusterNotFound)?;
        let name = entry
            .attribute
            .as_deref()
            .ok_or(ErrorCode::AttributeNotFound)?;
        let value = snapshot
            .and_then(|snapshot| snapshot.value["latest_values"].get(name))
            .and_then(|measurement| {
                kind.convert_unit(
                    &measurement["value"],
                    measurement["unit"].as_str().unwrap_or(""),
                )
            });
        if matches!(kind, Standard::BatteryPercent | Standard::BatteryVoltage) {
            let percent = snapshot
                .and_then(|snapshot| {
                    snapshot.value["latest_values"]
                        .get("battery_level")
                        .or_else(|| snapshot.value["latest_values"].get("battery"))
                })
                .and_then(|value| {
                    Standard::BatteryPercent
                        .convert_unit(&value["value"], value["unit"].as_str().unwrap_or(""))
                })
                .and_then(|value| value.as_u64());
            let voltage = snapshot
                .and_then(|snapshot| {
                    snapshot.value["latest_values"]
                        .get("battery_v")
                        .or_else(|| snapshot.value["latest_values"].get("voltage"))
                })
                .and_then(|value| {
                    Standard::BatteryVoltage
                        .convert_unit(&value["value"], value["unit"].as_str().unwrap_or(""))
                })
                .and_then(|value| value.as_u64());
            return match attr.attr_id {
                0 => reply.set(if snapshot.is_some() { 1u8 } else { 0u8 }),
                1 => reply.set(0u8),
                2 => reply.set("BLE device battery"),
                11 => reply.set(
                    voltage
                        .map(|number| Nullable::some(number as u32))
                        .unwrap_or(Nullable::none()),
                ),
                12 => reply.set(
                    percent
                        .map(|number| Nullable::some(number as u8))
                        .unwrap_or(Nullable::none()),
                ),
                14 => reply.set(if percent.is_some_and(|number| number <= 10) {
                    2u8
                } else if percent.is_some_and(|number| number <= 40) {
                    1
                } else {
                    0
                }),
                15 => reply.set(false),
                16 => reply.set(0u8),
                17 => reply.set(snapshot.is_some()),
                31 => {
                    let tag = reply.tag().clone();
                    let mut writer = reply.writer();
                    writer.start_array(&tag)?;
                    writer.u16(&TLVTag::Anonymous, entry.parent)?;
                    writer.end_container()?;
                    drop(writer);
                    reply.complete()
                }
                _ => Err(ErrorCode::AttributeNotFound.into()),
            };
        }
        match (kind, attr.attr_id) {
            (Standard::Boolean, 0) => {
                let mut value = value
                    .and_then(|value| value.as_bool())
                    .ok_or(ErrorCode::Invalid)?;
                if matches!(name, "opened" | "contact" | "door") {
                    value = !value;
                }
                reply.set(value)
            }
            (Standard::Occupancy, 0) => reply.set(
                value
                    .and_then(|value| value.as_u64())
                    .ok_or(ErrorCode::Invalid)? as u8,
            ),
            (Standard::Occupancy, 1) => reply.set(0u8),
            (Standard::Occupancy, 2) => reply.set(1u8),
            (Standard::Temperature | Standard::Pressure, 0) => reply.set(
                value
                    .and_then(|value| value.as_i64())
                    .map(|number| Nullable::some(number as i16))
                    .unwrap_or(Nullable::none()),
            ),
            (Standard::Humidity | Standard::Illuminance, 0) => reply.set(
                value
                    .and_then(|value| value.as_i64())
                    .map(|number| Nullable::some(number as u16))
                    .unwrap_or(Nullable::none()),
            ),
            (Standard::Temperature, 1) => reply.set(Nullable::some(-27315i16)),
            (Standard::Temperature | Standard::Pressure, 2) => reply.set(Nullable::some(32767i16)),
            (Standard::Pressure, 1) => reply.set(Nullable::some(-32767i16)),
            (Standard::Humidity | Standard::Illuminance, 1) => reply.set(Nullable::some(0u16)),
            (Standard::Humidity, 2) => reply.set(Nullable::some(10000u16)),
            (Standard::Illuminance, 2) => reply.set(Nullable::some(65534u16)),
            _ => Err(ErrorCode::AttributeNotFound.into()),
        }
    }

    fn bump_dataver(&self, _ctx: impl MatchContext) {}

    async fn run(&self, ctx: impl HandlerContext) -> Result<(), Error> {
        let mut previous = BTreeMap::new();
        loop {
            async_io::Timer::after(Duration::from_millis(250)).await;
            let versions: BTreeMap<_, _> = self
                .states
                .lock()
                .unwrap()
                .iter()
                .map(|(mac, state)| (mac.clone(), state.version))
                .collect();
            for entry in &self.entries {
                if previous.get(&entry.mac) != versions.get(&entry.mac) {
                    ctx.notify_cluster_changed(entry.endpoint, 0x0039);
                    ctx.notify_cluster_changed(
                        entry.endpoint,
                        entry
                            .standard
                            .map(Standard::cluster)
                            .unwrap_or(VENDOR_CLUSTER),
                    );
                }
            }
            previous = versions;
        }
    }
}

pub fn start(config: &MatterConfig, devices: &[DeviceConfig]) -> Result<MatterPublisher, String> {
    if config.store.is_empty()
        || !Path::new(&config.store).is_absolute()
        || Path::new(&config.store).parent().is_none()
    {
        return Err("Matter requires a dedicated absolute persistent store directory".into());
    }
    let (node, entries) = model(config, devices)?;
    let address = config
        .bind
        .parse::<std::net::IpAddr>()
        .map_err(|_| "invalid Matter bind IP")?;
    let socket = UdpSocket::bind((address, config.port))
        .map_err(|error| format!("Matter UDP bind failed: {error}"))?;
    let mut publisher = MatterPublisher::default();
    let worker = Arc::clone(&publisher.states);
    let stopped = Arc::clone(&publisher.stopped);
    let worker_config = config.clone();
    let (ready, receiver) = std::sync::mpsc::sync_channel(1);
    let handle = std::thread::Builder::new()
        .name("ble-matter".into())
        .spawn(move || {
            if let Err(error) = run(worker_config, node, entries, worker, socket, ready, stopped) {
                log::error!("Matter server stopped: {error:?}");
            }
        })
        .map_err(|error| error.to_string())?;
    receiver
        .recv_timeout(Duration::from_secs(30))
        .map_err(|_| "Matter server startup failed; see service log")??;
    publisher.worker = Some(handle);
    if config.domoticz_port != 0 {
        let binary=crate::profile::find_helper("matter-bridge").ok_or("Domoticz Matter integration requires the matter-bridge package")?;
        let check=std::net::TcpListener::bind((std::net::Ipv4Addr::LOCALHOST,config.domoticz_port)).map_err(|error|format!("Domoticz Matter controller port unavailable: {error}"))?;
        drop(check);
        let store=Path::new(&config.store).join("domoticz-controller");
        let mut bridge=std::process::Command::new(binary)
            .args(["--bind","127.0.0.1","--port",&config.domoticz_port.to_string(),"--peer",&format!("[::1]:{}",config.port),"--store"])
            .arg(store).arg("--auto-local").env("MATTER_MDNS_INTERFACE","lo")
            .spawn().map_err(|error|format!("cannot start dedicated Domoticz Matter controller: {error}"))?;
        if bridge.try_wait().map_err(|error|error.to_string())?.is_some(){return Err("dedicated Domoticz Matter controller exited at startup".into());}
        publisher.domoticz_bridge=Some(crate::managed_process::ManagedProcess::new(bridge,None));
        log::info!("Domoticz Matter controller listening on 127.0.0.1:{}",config.domoticz_port);
    }
    Ok(publisher)
}

fn run(
    config: MatterConfig,
    node: Node<'static>,
    entries: Vec<Entry>,
    states: SharedStates,
    socket: UdpSocket,
    ready: std::sync::mpsc::SyncSender<Result<(), String>>,
    stopped: Arc<std::sync::atomic::AtomicBool>,
) -> Result<(), Error> {
    let info = rs_matter::dm::clusters::basic_info::BasicInfoConfig {
        vendor_name: crate::profile::MATTER_VENDOR_NAME,
        product_name: "BLE gateway",
        product_label: "BLE gateway",
        unique_id: crate::profile::NAME,
        ..TEST_DEV_DET
    };
    let matter = Matter::new(&info, TEST_DEV_COMM, &TEST_DEV_ATT, config.port);
    let fabric = Path::new(&config.store).join("fabric");
    std::fs::create_dir_all(&fabric).map_err(|_| ErrorCode::StdIoError)?;
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(&fabric, std::fs::Permissions::from_mode(0o700))
        .map_err(|_| ErrorCode::StdIoError)?;
    let kv = matter.kv(DirKvBlobStore::new(fabric));
    matter.startup(&kv)?;
    let crypto = default_crypto(rand::rng(), DAC_PRIVKEY);
    let mut random = crypto.rand()?;
    let epoch = Dataver::new_rand(&mut random).get();
    let parts = Parts(
        entries
            .iter()
            .map(|entry| (entry.endpoint, entry.parent))
            .collect(),
    );
    let handler = BleHandler {
        states,
        entries,
        node: Node {
            endpoints: node.endpoints,
        },
        epoch,
    };
    let data_model = (
        node,
        rs_matter::dm::endpoints::EthSysHandlerBuilder::new()
            .netif_diag(&SysNetifs)
            .build(random)
            .chain(
                |endpoint, cluster| endpoint > 0 && cluster == desc::DescHandler::CLUSTER.id,
                Async(
                    desc::DescHandler::new_matching(Dataver::new_rand(&mut random), &parts).adapt(),
                ),
            )
            .chain(
                |endpoint, cluster| endpoint > 1 && cluster != desc::DescHandler::CLUSTER.id,
                Async(&handler),
            ),
    );
    let buffers: MatterBuffers = MatterBuffers::new();
    let state: EthInteractionModelState = EthInteractionModelState::new(EthNetwork::new_default());
    let im = InteractionModel::new(&matter, &crypto, &buffers, data_model, &kv, &state);
    futures_lite::future::block_on(im.startup())?;
    let responder = DefaultResponder::new(&im);
    let socket = async_io::Async::new(socket)?;
    if !matter.has_fabrics() {
        log::warn!(
            "Matter uses development attestation credentials; pair this BLE gateway separately"
        );
        matter.print_standard_qr_text(DiscoveryCapabilities::IP)?;
        matter.print_standard_qr_code(QrTextType::Unicode, DiscoveryCapabilities::IP)?;
        matter.open_basic_comm_window(MAX_COMM_WINDOW_TIMEOUT_SECS, &crypto, &())?;
    }
    let _ = ready.send(Ok(()));
    log::info!(
        "Matter BLE server listening on port {}; vendor cluster 0x{VENDOR_CLUSTER:08X}",
        config.port
    );
    let mut transport = pin!(matter.run(&crypto, &socket, &socket, &socket));
    let mut respond = pin!(responder.run::<4, 4>());
    let mut interaction = pin!(im.run());
    let mut discovery = pin!(async {
        if config.effective_mdns_backend() != crate::config::MdnsBackend::Disabled {
            let mut demoted = Vec::new();
            loop {
                if let Err(error) =
                    crate::matter_mdns::run(&matter, &crypto, &config, &mut demoted).await
                {
                    log::warn!("Matter mDNS unavailable: {error:?}; retrying in 10 seconds; direct IP remains available");
                }
                embassy_time::Timer::after(embassy_time::Duration::from_secs(10)).await;
            }
        }
        core::future::pending::<Result<(), Error>>().await
    });
    let all = embassy_futures::select::select4(
        &mut transport,
        &mut respond,
        &mut interaction,
        &mut discovery,
    )
    .coalesce();
    let shutdown = async {
        while !stopped.load(std::sync::atomic::Ordering::Relaxed) {
            async_io::Timer::after(Duration::from_millis(100)).await;
        }
        Ok::<(), Error>(())
    };
    futures_lite::future::block_on(embassy_futures::select::select(all, shutdown).coalesce())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn physical_metadata_uses_standard_attributes_and_preserves_endpoint_identity() {
        let directory = std::env::temp_dir().join(format!("ble-metadata-matter-{}", std::process::id()));
        let config = MatterConfig { store: directory.to_string_lossy().into(), ..Default::default() };
        let mut device: DeviceConfig = serde_yaml::from_str("mac: AABBCCDDEEFF\nmanufacturer: Xiaomi\nmodel: LYWSD03MMC\nfirmware_version: custom-build\nexpose:\n- {attribute: temperature}\n- {attribute: battery_level}\n").unwrap();
        let (node, entries) = model(&config, &[device.clone()]).unwrap();
        let parent = &entries[0];
        assert_eq!(info_text(parent, 1), Some("Xiaomi"));
        assert_eq!(info_text(parent, 3), Some("LYWSD03MMC"));
        assert_eq!(info_text(parent, 5), Some("LYWSD03MMC"));
        assert_eq!(info_text(parent, 10), Some("custom-build"));
        assert!(node.endpoint(parent.endpoint).unwrap().cluster(0x0039).unwrap().attributes.iter().any(|attribute| attribute.id == 1));
        assert_eq!(entries[1].label, "LYWSD03MMC temperature");
        device.label = "é".repeat(20);
        device.manufacturer.clear();
        device.model = "Updated model".into();
        let (updated_node, updated) = model(&config, &[device]).unwrap();
        assert_eq!(info_text(&updated[0], 5).unwrap().len(), 32);
        assert!(info_text(&updated[0], 1).is_none());
        assert!(!updated_node.endpoint(updated[0].endpoint).unwrap().cluster(0x0039).unwrap().attributes.iter().any(|attribute| attribute.id == 1));
        let identities = |entries: &[Entry]| entries.iter().map(|entry| (entry.endpoint, entry.parent, entry.mac.clone(), entry.attribute.clone())).collect::<Vec<_>>();
        assert_eq!(identities(&entries), identities(&updated));
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn real_matter_server_starts_and_releases_loopback_socket() {
        let probe = UdpSocket::bind((std::net::Ipv6Addr::LOCALHOST, 0)).unwrap();
        let port = probe.local_addr().unwrap().port();
        drop(probe);
        let directory =
            std::env::temp_dir().join(format!("ble-matter-startup-{}", std::process::id()));
        let config = MatterConfig {
            enabled: true,
            bind: "::1".into(),
            advertise: false,
            port,
            store: directory.to_string_lossy().into(),
            ..MatterConfig::default()
        };
        let devices=vec![serde_yaml::from_str("mac: AABBCCDDEEFF\nexpose:\n- {attribute: temperature}\n- {attribute: battery_level}\n- {attribute: new_value}\n").unwrap()];
        let publisher = start(&config, &devices).unwrap();
        let state = serde_json::json!({"decoded":{"new_value":[true,null,1.23456789]},"measurements":[{"name":"temperature","value":22.1234,"unit":"C"}]});
        publisher.publish("AABBCCDDEEFF", &state);
        assert_eq!(
            publisher.states.lock().unwrap()["AABBCCDDEEFF"].value["decoded"],
            state["decoded"]
        );
        assert!(UdpSocket::bind((std::net::Ipv6Addr::LOCALHOST, port)).is_err());
        drop(publisher);
        assert!(UdpSocket::bind((std::net::Ipv6Addr::LOCALHOST, port)).is_ok());
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn vendor_json_reassembles_from_actual_matter_tlv_reads() {
        use rs_matter::dm::{AttrDetails, ReadReplyInstance};
        use rs_matter::im::encoding::{AttrDataTag, AttrRespTag};
        use rs_matter::tlv::get_root_node_struct;
        use rs_matter::utils::storage::WriteBuf;
        let original=serde_json::to_vec(&serde_json::json!({"unicode":"\u{00e9}".repeat(400),"unknown":[true,null,1.23456789],"raw":"ABCD".repeat(500)})).unwrap();
        let mut reassembled = Vec::new();
        for index in 0..original.chunks(JSON_CHUNK_BYTES).len() {
            let attr = AttrDetails {
                endpoint_id: 2,
                cluster_id: VENDOR_CLUSTER,
                attr_id: 3,
                list_index: Some(Nullable::some(index as u16)),
                list_chunked: true,
                fab_idx: 1,
                fab_filter: false,
                dataver: None,
                wildcard: false,
                array: true,
                cluster_status: std::cell::Cell::new(None),
            };
            let mut bytes = [0u8; 600];
            let mut writer = WriteBuf::new(&mut bytes);
            let reply = ReadReplyInstance::new(&attr, &mut writer)
                .with_dataver(1)
                .unwrap()
                .unwrap();
            write_json_chunks(reply, attr.list_index.as_ref(), &original).unwrap();
            let root = get_root_node_struct(writer.as_slice()).unwrap();
            let value = root
                .structure()
                .unwrap()
                .find_ctx(AttrRespTag::Data as u8)
                .unwrap()
                .structure()
                .unwrap()
                .find_ctx(AttrDataTag::Data as u8)
                .unwrap();
            reassembled.extend_from_slice(value.str().unwrap());
        }
        assert_eq!(reassembled, original);
        assert_eq!(
            serde_json::from_slice::<serde_json::Value>(&reassembled).unwrap()["unknown"][1],
            serde_json::Value::Null
        );
        let attr = AttrDetails {
            endpoint_id: 2,
            cluster_id: VENDOR_CLUSTER,
            attr_id: 3,
            list_index: Some(Nullable::some(u16::MAX)),
            list_chunked: true,
            fab_idx: 1,
            fab_filter: false,
            dataver: None,
            wildcard: false,
            array: true,
            cluster_status: std::cell::Cell::new(None),
        };
        let mut bytes = [0u8; 600];
        let mut writer = WriteBuf::new(&mut bytes);
        let reply = ReadReplyInstance::new(&attr, &mut writer)
            .with_dataver(1)
            .unwrap()
            .unwrap();
        assert_eq!(
            write_json_chunks(reply, attr.list_index.as_ref(), &original)
                .unwrap_err()
                .code(),
            ErrorCode::ConstraintError
        );
    }
}
