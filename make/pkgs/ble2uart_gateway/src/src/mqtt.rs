use crate::config::{DeviceMetadata, MqttConfig};
use rumqttc::{Client, Event, Incoming, MqttOptions, QoS};
use std::collections::BTreeMap;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::time::Duration;

fn domoticz_discovery(prefix: &str, base: &str, mac: &str, metadata: &DeviceMetadata, name: &str, measurement: &serde_json::Value) -> (String, serde_json::Value, String, Vec<u8>) {
    let key = if name.bytes().all(|byte| byte.is_ascii_alphanumeric() || byte == b'_') {format!("a_{name}")} else {format!("h_{}",crate::codec::value::hex(name.as_bytes()))};
    let identifier=format!("ble2uart_{mac}_{key}");
    let value=&measurement["value"];
    let binary=value.is_boolean();
    let domain=if binary {"binary_sensor"} else {"sensor"};
    let state_topic=format!("{base}/{mac}/attributes/{key}");
    let mut config=serde_json::json!({
        "unique_id":identifier,"name":DeviceMetadata::measurement_name(name),"state_topic":state_topic,
        "device":{"identifiers":[format!("ble2uart_{mac}")],"name":metadata.name},
    });
    for (field, value) in [("manufacturer", &metadata.manufacturer), ("model", &metadata.model), ("sw_version", &metadata.firmware_version)] {
        if !value.is_empty() {config["device"][field]=value.as_str().into();}
    }
    let class=match name {"temperature"=>Some("temperature"),"humidity"=>Some("humidity"),"battery"|"battery_level"=>Some("battery"),"battery_v"|"voltage"=>Some("voltage"),"pressure"=>Some("pressure"),"illuminance"|"lux"=>Some("illuminance"),"opened"|"contact"|"door" if binary=>Some("opening"),"motion" if binary=>Some("motion"),_=>None};
    if let Some(class)=class {config["device_class"]=class.into();}
    if class==Some("battery") && value.is_number() {config["entity_category"]="diagnostic".into();}
    if !binary {
        if let Some(unit)=measurement["unit"].as_str().filter(|unit|!unit.is_empty()) {config["unit_of_measurement"]=unit.into();}
    } else {
        config["payload_on"]="ON".into();config["payload_off"]="OFF".into();
    }
    let payload=if binary {if value.as_bool().unwrap() {b"ON".to_vec()} else {b"OFF".to_vec()}} else if let Some(text)=value.as_str() {text.as_bytes().to_vec()} else {serde_json::to_vec(value).expect("JSON measurement serialization")};
    (format!("{prefix}/{domain}/{identifier}/config"),config,state_topic,payload)
}

#[derive(Default)]
struct Publications {
    latest: BTreeMap<String, Vec<u8>>,
    pending: BTreeMap<String, Vec<u8>>,
}

pub struct MqttPublisher {
    state: Arc<Mutex<Publications>>,
    stopped: Arc<AtomicBool>,
    prefix: String,
    discovery: Option<String>,
    _broker: Option<crate::managed_process::ManagedProcess>,
}

impl MqttPublisher {
    pub fn start(config: &MqttConfig, devices: usize) -> Result<Self, String> {
        if config.host.trim().is_empty() || config.port == 0 || config.client_id.is_empty() {
            return Err("MQTT requires host, port and client_id".into());
        }
        let broker=if config.local_broker {
            use std::io::Write;
            use std::os::unix::fs::OpenOptionsExt;
            let check=std::net::TcpListener::bind((std::net::Ipv4Addr::LOCALHOST,config.port)).map_err(|error|format!("managed MQTT broker port unavailable: {error}"))?;drop(check);
            let path=std::env::temp_dir().join(format!("{}-mqtt-{}.conf",crate::profile::NAME,std::process::id()));
            let mut file=std::fs::OpenOptions::new().write(true).create_new(true).mode(0o600).open(&path).map_err(|error|error.to_string())?;
            write!(file,"user nobody\nlistener {} 127.0.0.1\nallow_anonymous true\npersistence false\n",config.port).map_err(|error|error.to_string())?;
            file.sync_all().map_err(|error|error.to_string())?;drop(file);
            let binary=crate::profile::find_helper("mosquitto").ok_or("local_broker requires the mosquitto package")?;
            let child=std::process::Command::new(binary).arg("-c").arg(&path).spawn().map_err(|error|format!("cannot start local MQTT broker: {error}"))?;
            Some(crate::managed_process::ManagedProcess::new(child,Some(path)))
        } else {None};
        let mut options = MqttOptions::new(&config.client_id, &config.host, config.port);
        options.set_keep_alive(Duration::from_secs(15));
        options.set_max_packet_size(1024 * 1024, 1024 * 1024);
        if !config.username.is_empty() {
            options.set_credentials(&config.username, &config.password);
        }
        let (client, mut connection) =
            Client::new(options, devices.saturating_mul(2).saturating_add(8).max(16));
        let state = Arc::new(Mutex::new(Publications::default()));
        let stopped = Arc::new(AtomicBool::new(false));
        let worker_state = Arc::clone(&state);
        let worker_stopped = Arc::clone(&stopped);
        let retain = config.retain;
        let discovery=config.domoticz_discovery.then(||config.discovery_prefix.trim_matches('/').to_string());
        let worker_discovery=discovery.as_ref().map(|prefix|format!("{prefix}/"));
        std::thread::Builder::new()
            .name("ble-mqtt".into())
            .spawn(move || {
                let mut connected = false;
                let mut failures = 0u32;
                while !worker_stopped.load(Ordering::Relaxed) {
                    let timeout = if connected {
                        Duration::from_millis(100)
                    } else {
                        Duration::from_secs(5)
                    };
                    match connection.recv_timeout(timeout) {
                        Ok(Ok(Event::Incoming(Incoming::ConnAck(_)))) => {
                            connected = true;
                            failures = 0;
                            let mut state = worker_state.lock().unwrap();
                            state.pending = state.latest.clone();
                            log::info!("MQTT connected; replaying latest device states");
                        }
                        Ok(Err(_)) => {
                            connected = false;
                            if failures % 30 == 0 {
                                log::warn!(
                                    "MQTT unavailable; latest states retained for reconnect"
                                );
                            }
                            failures = failures.saturating_add(1);
                            std::thread::sleep(Duration::from_secs(1));
                        }
                        Err(rumqttc::RecvTimeoutError::Disconnected) => {
                            connected = false;
                        }
                        _ => {}
                    }
                    if !connected {
                        continue;
                    }
                    let pending = std::mem::take(&mut worker_state.lock().unwrap().pending);
                    let mut pending:Vec<_>=pending.into_iter().collect();
                    pending.sort_by_key(|(topic,_)|if worker_discovery.as_ref().is_some_and(|prefix|topic.starts_with(prefix)){0}else{1});
                    for (topic, payload) in pending {
                        let retained=retain||worker_discovery.as_ref().is_some_and(|prefix|topic.starts_with(prefix));
                        if client
                            .try_publish(&topic, QoS::AtLeastOnce, retained, payload.clone())
                            .is_err()
                        {
                            worker_state
                                .lock()
                                .unwrap()
                                .pending
                                .entry(topic)
                                .or_insert(payload);
                        }
                    }
                }
            })
            .map_err(|error| error.to_string())?;
        Ok(Self {
            state,
            stopped,
            prefix: config.base_topic.trim_end_matches('/').into(),
            discovery,
            _broker: broker,
        })
    }

    pub fn publish(&self, mac: &str, state: &serde_json::Value) {
        let topic = format!("{}/{mac}/state", self.prefix);
        let mut publications = self.state.lock().unwrap();
        let mut state = state.clone();
        let previous = publications
            .latest
            .get(&topic)
            .and_then(|bytes| serde_json::from_slice(bytes).ok());
        crate::pipeline::merge_latest_values(previous.as_ref(), &mut state);
        let payload = serde_json::to_vec(&state).expect("JSON state serialization");
        publications.latest.insert(topic.clone(), payload.clone());
        publications.pending.insert(topic, payload);
        if let Some(prefix)=&self.discovery {
            let mut metadata: DeviceMetadata = state.get("device").and_then(|value|serde_json::from_value(value.clone()).ok()).unwrap_or_default();
            if metadata.name.is_empty() {metadata.name=state["label"].as_str().unwrap_or(mac).to_string();}
            if let Some(values)=state["latest_values"].as_object() {
                for (name,measurement) in values {
                    if measurement["value"].is_null(){continue;}
                    let (config_topic,config,state_topic,payload)=domoticz_discovery(prefix,&self.prefix,mac,&metadata,name,measurement);
                    let config=serde_json::to_vec(&config).expect("MQTT discovery serialization");
                    if publications.latest.get(&config_topic)!=Some(&config) {
                        publications.latest.insert(config_topic.clone(),config.clone());
                        publications.pending.insert(config_topic,config);
                    }
                    publications.latest.insert(state_topic.clone(),payload.clone());
                    publications.pending.insert(state_topic,payload);
                }
            }
        }
    }
}

impl Drop for MqttPublisher {
    fn drop(&mut self) {
        self.stopped.store(true, Ordering::Relaxed);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_domoticz_discovery_uses_canonical_fields_and_scalar_states() {
        let metadata=DeviceMetadata {name:"Room".into(),manufacturer:"Xiaomi".into(),model:"LYWSD03MMC".into(),firmware_version:"custom build".into()};
        let measurement=serde_json::json!({"value":21.3456,"unit":"\u{00b0}C"});
        let (topic,config,state,payload)=domoticz_discovery("homeassistant","ble","AABBCCDDEEFF",&metadata,"temperature",&measurement);
        assert!(topic.starts_with("homeassistant/sensor/"));
        assert_eq!(config["unique_id"],"ble2uart_AABBCCDDEEFF_a_temperature");
        assert_eq!(config["state_topic"],state);
        assert_eq!(config["device_class"],"temperature");
        assert_eq!(config["unit_of_measurement"],"\u{00b0}C");
        assert_eq!(config["name"],"temperature");
        assert_eq!(config["device"]["name"],"Room");
        assert_eq!(config["device"]["manufacturer"],"Xiaomi");
        assert_eq!(config["device"]["model"],"LYWSD03MMC");
        assert_eq!(config["device"]["sw_version"],"custom build");
        assert_eq!(payload,b"21.3456");
        assert!(config.get("value_template").is_none());
        let renamed=DeviceMetadata {name:"Renamed".into(), ..Default::default()};
        let (updated_topic,updated,updated_state,_)=domoticz_discovery("homeassistant","ble","AABBCCDDEEFF",&renamed,"temperature",&measurement);
        assert_eq!(updated_topic,topic);assert_eq!(updated_state,state);
        assert_eq!(updated["unique_id"],config["unique_id"]);
        assert!(updated["device"].get("manufacturer").is_none());
        assert!(updated["device"].get("model").is_none());
        assert!(updated["device"].get("sw_version").is_none());
        let (_,config,_,payload)=domoticz_discovery("homeassistant","ble","AABBCCDDEEFF",&metadata,"battery_level",&serde_json::json!({"value":84,"unit":"%"}));
        assert_eq!(config["device_class"],"battery");
        assert_eq!(config["entity_category"],"diagnostic");
        assert_eq!(payload,b"84");
        let (topic,config,_,payload)=domoticz_discovery("homeassistant","ble","AABBCCDDEEFF",&metadata,"opened",&serde_json::json!({"value":true,"unit":""}));
        assert!(topic.contains("/binary_sensor/"));
        assert_eq!(config["payload_on"],"ON");assert_eq!(payload,b"ON");
    }

    #[test]
    fn domoticz_mode_keeps_full_state_and_does_not_repeat_unchanged_discovery() {
        let publisher=MqttPublisher {state:Arc::new(Mutex::new(Publications::default())),stopped:Arc::new(AtomicBool::new(false)),prefix:"ble".into(),discovery:Some("homeassistant".into()),_broker:None};
        let state=serde_json::json!({"label":"Room","received_at":"one","decoded":{"temperature":21.3456,"vendor":[null,true,12]},"measurements":[{"name":"temperature","value":21.3456,"unit":"\u{00b0}C"},{"name":"opened","value":true,"unit":""}]});
        publisher.publish("AABBCCDDEEFF",&state);
        let mut stored=publisher.state.lock().unwrap();
        assert_eq!(stored.pending.len(),5);
        let full:serde_json::Value=serde_json::from_slice(&stored.latest["ble/AABBCCDDEEFF/state"]).unwrap();
        assert_eq!(full["decoded"],state["decoded"]);
        assert_eq!(stored.latest["ble/AABBCCDDEEFF/attributes/a_temperature"],b"21.3456");
        assert_eq!(stored.latest["ble/AABBCCDDEEFF/attributes/a_opened"],b"ON");
        stored.pending.clear();drop(stored);
        publisher.publish("AABBCCDDEEFF",&state);
        let stored=publisher.state.lock().unwrap();
        assert_eq!(stored.pending.len(),3);
        assert!(!stored.pending.keys().any(|topic|topic.starts_with("homeassistant/")));
    }

    fn read_packet(stream: &mut std::net::TcpStream) -> (u8, Vec<u8>) {
        use std::io::Read;
        let mut header = [0];
        stream.read_exact(&mut header).unwrap();
        let mut remaining = 0usize;
        let mut multiplier = 1;
        loop {
            let mut length = [0];
            stream.read_exact(&mut length).unwrap();
            remaining += usize::from(length[0] & 127) * multiplier;
            if length[0] & 128 == 0 {
                break;
            }
            multiplier *= 128;
        }
        let mut payload = vec![0; remaining];
        stream.read_exact(&mut payload).unwrap();
        (header[0], payload)
    }

    #[test]
    fn mqtt_delivers_qos1_retained_state_and_replays_after_reconnect() {
        use std::io::Write;
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let config = MqttConfig {
            host: "127.0.0.1".into(),
            port: listener.local_addr().unwrap().port(),
            base_topic: "regression".into(),
            ..MqttConfig::default()
        };
        let (first_sent, first_received) = std::sync::mpsc::channel();
        let broker = std::thread::spawn(move || {
            for round in 1..=2 {
                let (mut stream, _) = listener.accept().unwrap();
                stream
                    .set_read_timeout(Some(Duration::from_secs(8)))
                    .unwrap();
                assert_eq!(read_packet(&mut stream).0 >> 4, 1);
                stream.write_all(&[0x20, 2, 0, 0]).unwrap();
                loop {
                    let (header, payload) = read_packet(&mut stream);
                    if header >> 4 == 12 {
                        stream.write_all(&[0xD0, 0]).unwrap();
                        continue;
                    }
                    if header >> 4 != 3 {
                        continue;
                    }
                    assert_eq!(header & 7, 3);
                    let length = usize::from(u16::from_be_bytes([payload[0], payload[1]]));
                    assert_eq!(&payload[2..2 + length], b"regression/AABBCCDDEEFF/state");
                    let value: serde_json::Value =
                        serde_json::from_slice(&payload[4 + length..]).unwrap();
                    assert_eq!(value["revision"], round);
                    assert_eq!(value["decoded"]["new_value"], 12.3456789);
                    stream
                        .write_all(&[0x40, 2, payload[2 + length], payload[3 + length]])
                        .unwrap();
                    if round == 1 {
                        first_sent.send(()).unwrap();
                    }
                    break;
                }
            }
        });
        let publisher = MqttPublisher::start(&config, 1).unwrap();
        publisher.publish("AABBCCDDEEFF",&serde_json::json!({"revision":1,"decoded":{"new_value":12.3456789,"all_types":[true,null,"value"]}}));
        first_received
            .recv_timeout(Duration::from_secs(10))
            .unwrap();
        publisher.publish("AABBCCDDEEFF",&serde_json::json!({"revision":2,"decoded":{"new_value":12.3456789,"all_types":[true,null,"value"]}}));
        broker.join().unwrap();
    }

    #[test]
    fn alternating_packets_keep_previous_measurements() {
        let publisher = MqttPublisher {
            state: Arc::new(Mutex::new(Publications::default())),
            stopped: Arc::new(AtomicBool::new(false)),
            prefix: "test".into(),
            discovery: None,
            _broker: None,
        };
        publisher.publish("AABBCCDDEEFF",&serde_json::json!({"received_at":"one","decoded":{"temperature":20.1234},"measurements":[{"name":"temperature","value":20.1234,"unit":"C"}]}));
        publisher.publish("AABBCCDDEEFF",&serde_json::json!({"received_at":"two","decoded":{"switch":false},"measurements":[{"name":"switch","value":false,"unit":""}]}));
        let stored = publisher.state.lock().unwrap();
        let actual: serde_json::Value =
            serde_json::from_slice(&stored.latest["test/AABBCCDDEEFF/state"]).unwrap();
        assert_eq!(actual["latest_values"]["temperature"]["value"], 20.1234);
        assert_eq!(actual["latest_values"]["switch"]["value"], false);
        assert_eq!(actual["decoded"], serde_json::json!({"switch":false}));
    }

    #[test]
    fn mqtt_snapshot_preserves_arbitrary_json_and_latest_per_mac() {
        let publisher = MqttPublisher {
            state: Arc::new(Mutex::new(Publications::default())),
            stopped: Arc::new(AtomicBool::new(false)),
            prefix: "test".into(),
            discovery: None,
            _broker: None,
        };
        let first = serde_json::json!({"decoded":{"new_sensor":12.3456789,"flags":[true,false,null],"raw":"ABCD"}});
        publisher.publish("AABBCCDDEEFF", &first);
        let stored = publisher.state.lock().unwrap();
        assert_eq!(
            serde_json::from_slice::<serde_json::Value>(&stored.latest["test/AABBCCDDEEFF/state"])
                .unwrap(),
            first
        );
        drop(stored);
        publisher.publish("AABBCCDDEEFF", &serde_json::json!({"new_sensor":99}));
        let stored = publisher.state.lock().unwrap();
        assert_eq!(stored.latest.len(), 1);
        assert_eq!(stored.pending.len(), 1);
    }
}
