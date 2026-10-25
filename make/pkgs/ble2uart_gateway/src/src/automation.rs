use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::Path;
use std::collections::{BTreeMap,VecDeque};
use std::fs::{File,OpenOptions};
use std::io::{Read,Write};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;
use std::time::{Duration,Instant,SystemTime,UNIX_EPOCH};
use std::sync::{Arc,Mutex,atomic::{AtomicBool,Ordering}};
use std::thread::JoinHandle;
use std::hash::{Hash,Hasher};

#[derive(Debug, Clone, Deserialize)]
#[serde(default)]
pub struct LegacyAutomationConfig {
    pub enabled: bool,
    pub state_file: String,
    pub webhook: WebhookConfig,
    pub rules: Vec<LegacyAutomationRule>,
}

impl Default for LegacyAutomationConfig {
    fn default() -> Self {
        Self {enabled:false,state_file:String::new(),webhook:WebhookConfig::default(),rules:vec![LegacyAutomationRule::default()]}
    }
}

#[derive(Debug, Clone, Deserialize)]
#[serde(default)]
pub struct LegacyAutomationRule {
    pub id: String,
    pub enabled: bool,
    pub mac: String,
    pub attribute: String,
    pub stale_after_s: u64,
    pub notify_recovery: bool,
}

impl Default for LegacyAutomationRule {
    fn default() -> Self {
        Self {id:"temperature_missing".into(),enabled:true,mac:String::new(),attribute:"temperature".into(),stale_after_s:600,notify_recovery:true}
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all="snake_case")]
pub enum Provider {
    #[default]
    Ntfy,
    Gotify,
    /// Generic HTTPS endpoint: method, content type and body are configurable.
    Rest,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct WebhookConfig {
    #[serde(skip_serializing)]
    pub enabled: bool,
    pub provider: Provider,
    pub url: String,
    pub token: String,
    pub ca_file: String,
    pub priority: u8,
    pub tags: String,
    pub ipv4_only: bool,
    pub timeout_ms: u64,
    pub max_attempts: u32,
    pub retry_s: u64,
    /// REST only: HTTP method (POST, PUT, PATCH or GET).
    pub method: String,
    /// REST only: request content type.
    pub content_type: String,
    /// REST only: request body template, `{event}`, `{message}`, `{device}`,
    /// `{attribute}`, `{value}`, `{unit}`, `{title}` are substituted.
    pub body: String,
    /// REST only: one extra header written as `Name: value`.
    pub header: String,
}

impl std::fmt::Debug for WebhookConfig {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.debug_struct("WebhookConfig").field("enabled",&self.enabled)
            .field("provider",&self.provider).field("token_present",&!self.token.is_empty()).finish_non_exhaustive()
    }
}

impl Default for WebhookConfig {
    fn default() -> Self {
        Self { enabled:false,provider:Provider::Ntfy,url:String::new(),token:String::new(),ca_file:String::new(),priority:4,tags:"thermometer".into(),ipv4_only:false,
            timeout_ms:5000,max_attempts:1,retry_s:60,method:"POST".into(),content_type:"application/json".into(),
            body:r#"{"event":"{event}","device":"{device}","attribute":"{attribute}","value":"{value}","unit":"{unit}","message":"{message}"}"#.into(),
            header:String::new() }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct AutomationRule {
    pub id: String,
    pub enabled: bool,
    pub attribute: String,
    pub stale_after_s: u64,
    pub startup_grace_s: u64,
    pub notify_recovery: bool,
    pub message: String,
    /// Text sent when a notified outage ends; empty keeps the automatic text.
    pub recovery_message: String,
    pub tgs: String,
    pub webhook: WebhookConfig,
}

impl Default for AutomationRule {
    fn default() -> Self {
        Self { id:"temperature_missing".into(),enabled:false,attribute:"temperature".into(),
            stale_after_s:600,startup_grace_s:600,notify_recovery:true,message:String::new(),
            recovery_message:String::new(),tgs:String::new(),webhook:WebhookConfig::default() }
    }
}

impl WebhookConfig {
    pub fn validate(&self,required: bool) -> Result<(),String> {
        let webhook=self;
        if !(100..=10000).contains(&webhook.timeout_ms) || !(1..=10).contains(&webhook.max_attempts)
            || !(1..=86400).contains(&webhook.retry_s) {
            return Err("automation webhook timeout/attempt/retry limits are invalid".into());
        }
        if !webhook.token.is_ascii() || webhook.token.len()>8192 || webhook.token.bytes().any(|byte|byte.is_ascii_control()) {
            return Err("automation webhook token contains invalid header characters".into());
        }
        if !(1..=5).contains(&webhook.priority) || webhook.tags.len()>256 || !webhook.tags.is_ascii()
            || webhook.tags.bytes().any(|byte|byte.is_ascii_control()) {
            return Err("webhook priority must be 1-5 and tags must be bounded ASCII header text".into());
        }
        if !webhook.ca_file.is_empty() && (!Path::new(&webhook.ca_file).is_absolute() || webhook.ca_file.chars().any(char::is_control)) {
            return Err("automation CA file must be an absolute PEM file path".into());
        }
        if required || !webhook.url.is_empty() {
            let uri: ureq::http::Uri=webhook.url.parse().map_err(|_|"automation webhook URL is invalid")?;
            let generic=webhook.provider==Provider::Rest;
            if uri.scheme_str()!=Some("https") || uri.host().is_none() || uri.authority().is_some_and(|value|value.as_str().contains('@'))
                || webhook.url.contains('#')
                || (!generic && (uri.query().is_some() || uri.path()=="/")) {
                return Err("automation webhook requires HTTPS, a topic or /message path, and no URL credentials/query/fragment".into());
            }
            if webhook.provider==Provider::Gotify && (!uri.path().ends_with("/message") || webhook.token.is_empty()) {
                return Err("Gotify requires a /message endpoint and an application token".into());
            }
            if generic {
                let method=webhook.method.to_ascii_uppercase();
                if !matches!(method.as_str(),"POST"|"PUT"|"PATCH"|"GET") {
                    return Err("REST webhook method must be POST, PUT, PATCH or GET".into());
                }
                if webhook.content_type.len()>128 || !webhook.content_type.is_ascii()
                    || webhook.content_type.bytes().any(|byte|byte.is_ascii_control()) {
                    return Err("REST webhook content type must be bounded ASCII header text".into());
                }
                if webhook.body.len()>8192 || webhook.body.contains('\0') {
                    return Err("REST webhook body must be at most 8192 bytes without NUL".into());
                }
                if !webhook.header.trim().is_empty() {
                    let (name,value)=webhook.header.split_once(':').ok_or("REST webhook header must be written as 'Name: value'")?;
                    if name.trim().is_empty()
                        || !name.trim().bytes().all(|byte|byte.is_ascii_alphanumeric()||b"-_".contains(&byte))
                        || value.bytes().any(|byte|byte.is_ascii_control()) {
                        return Err("REST webhook header must be written as 'Name: value' with a simple ASCII name".into());
                    }
                }
            }
        }
        Ok(())
    }
}

impl AutomationRule {
    pub fn validate(&self) -> Result<(),String> {
        if self.id.is_empty() || self.id.len()>64 || !self.id.bytes().all(|byte|byte.is_ascii_alphanumeric()||b"_-".contains(&byte))
            || self.attribute.is_empty() || self.attribute.len()>128 || self.attribute.chars().any(char::is_control)
            || !(1..=31536000).contains(&self.stale_after_s) || self.startup_grace_s>86400 {
            return Err("availability rules require a stable ID, an attribute and a positive timeout".into());
        }
        if self.message.len()>4096 || self.message.chars().any(|character|character.is_control()&&!matches!(character,'\n'|'\r'|'\t')) {
            return Err("availability message must be at most 4096 bytes without unsupported control characters".into());
        }
        if self.recovery_message.len()>4096 || self.recovery_message.chars().any(|character|character.is_control()&&!matches!(character,'\n'|'\r'|'\t')) {
            return Err("availability recovery message must be at most 4096 bytes without unsupported control characters".into());
        }
        if self.tgs.len()>256 || !self.tgs.is_ascii() || self.tgs.bytes().any(|byte|byte.is_ascii_control()) {
            return Err("availability tgs must be bounded ASCII header text".into());
        }
        self.webhook.validate(self.enabled)
    }

    fn effective_webhook(&self) -> WebhookConfig {
        let mut webhook=self.webhook.clone();
        if !self.tgs.trim().is_empty() {webhook.tags=self.tgs.clone();}
        webhook
    }

    fn notification_message(&self,action: &str,default: impl FnOnce()->String) -> String {
        let custom=if action=="recovery" {&self.recovery_message} else {&self.message};
        if custom.trim().is_empty() {default()} else {custom.clone()}
    }
}

pub fn deserialize_rules<'de,D:serde::Deserializer<'de>>(deserializer:D)->Result<Vec<AutomationRule>,D::Error> {
    let values=Vec::<Value>::deserialize(deserializer)?;
    values.into_iter().enumerate().map(|(index,value)|{
        if value.get("source").is_some() && value.get("webhook").is_none() {
            let mut rule=AutomationRule::default();
            rule.id=format!("availability_{}",index+1);
            rule.attribute=value["source"].as_str().filter(|text|!text.trim().is_empty()).unwrap_or("temperature").into();
            rule.stale_after_s=value["after_s"].as_u64().filter(|seconds|*seconds>0).unwrap_or(600);
            Ok(rule)
        } else {serde_json::from_value(value).map_err(serde::de::Error::custom)}
    }).collect()
}

fn evaluate(age_s: u64,timeout_s: u64,active: bool) -> Option<&'static str> {
    match (age_s>=timeout_s,active) {
        (true,false)=>Some("stale"),
        (false,true)=>Some("recovery"),
        _=>None,
    }
}

#[derive(Debug,Clone,Serialize,Deserialize,Default)]
#[serde(default,deny_unknown_fields)]
struct WatchState {
    fingerprint: u64,
    rule_id: String,
    mac: String,
    attribute: String,
    label: String,
    last_seen_s: Option<u64>,
    last_value: Option<Value>,
    active: bool,
    stale_delivered: bool,
    episode: u64,
}

#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
#[derive(Default)]
struct Notification {
    id: String,
    key: String,
    kind: String,
    message: String,
    #[serde(default)]
    device: String,
    #[serde(default)]
    attribute: String,
    #[serde(default)]
    value: String,
    #[serde(default)]
    unit: String,
    attempts: u32,
    next_attempt_s: u64,
}

#[derive(Debug,Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
struct Persistent {
    version: u32,
    watches: BTreeMap<String,WatchState>,
    pending: VecDeque<Notification>,
    last_error: String,
}

impl Default for Persistent {
    fn default() -> Self {
        Self {version:1,watches:BTreeMap::new(),pending:VecDeque::new(),last_error:String::new()}
    }
}

const STATE_LIMIT: u64=1024*1024;

fn load_state(path: &Path) -> Result<Persistent,String> {
    let file=match OpenOptions::new().read(true).custom_flags(libc::O_NOFOLLOW).open(path) {
        Ok(file)=>file,
        Err(error) if error.kind()==std::io::ErrorKind::NotFound=>return Ok(Persistent::default()),
        Err(error)=>return Err(format!("cannot open automation state: {error}")),
    };
    let mut bytes=Vec::new();file.take(STATE_LIMIT+1).read_to_end(&mut bytes).map_err(|error|error.to_string())?;
    if bytes.len() as u64>STATE_LIMIT {return Err("automation state exceeds 1 MiB".into());}
    let state:Persistent=serde_json::from_slice(&bytes).map_err(|_|"invalid automation state; restore a valid backup rather than resetting deduplication")?;
    if state.version!=1 || state.watches.len()>4096 || state.pending.len()>1024 {
        return Err("unsupported or oversized automation state".into());
    }
    Ok(state)
}

struct StateStore {
    path: std::path::PathBuf,
    _lock: File,
}

impl StateStore {
    fn open(path: &Path) -> Result<Self,String> {
        let lock=OpenOptions::new().read(true).write(true).create(true).truncate(false).mode(0o600)
            .custom_flags(libc::O_NOFOLLOW).open(path.with_extension("json.lock")).map_err(|error|format!("cannot lock automation state: {error}"))?;
        if unsafe {libc::flock(lock.as_raw_fd(),libc::LOCK_EX|libc::LOCK_NB)}!=0 {
            return Err("automation state is already used by another process".into());
        }
        Ok(Self {path:path.to_owned(),_lock:lock})
    }

    fn save(&self,state: &Persistent) -> Result<(),String> {
        let bytes=serde_json::to_vec(state).map_err(|error|error.to_string())?;
        if bytes.len() as u64>STATE_LIMIT {return Err("automation state exceeds 1 MiB".into());}
        let parent=self.path.parent().ok_or("automation state has no parent directory")?;
        let nonce=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|error|error.to_string())?.as_nanos();
        let temporary=parent.join(format!(".automation-{}-{nonce}.tmp",std::process::id()));
        let result=(||->Result<(),String>{
            let mut file=OpenOptions::new().write(true).create_new(true).mode(0o600).open(&temporary).map_err(|error|error.to_string())?;
            file.write_all(&bytes).map_err(|error|error.to_string())?;
            file.sync_all().map_err(|error|error.to_string())?;
            std::fs::rename(&temporary,&self.path).map_err(|error|error.to_string())?;
            File::open(parent).and_then(|directory|directory.sync_all()).map_err(|error|error.to_string())?;
            Ok(())
        })();
        if result.is_err() {let _=std::fs::remove_file(&temporary);}
        result
    }
}

fn now_seconds() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|time|time.as_secs()).unwrap_or(0)
}

fn transition(state: &mut Persistent,key: &str,action: &str,rule: &AutomationRule,capacity: usize,now: u64) -> bool {
    let Some(watch)=state.watches.get_mut(key) else {return false;};
    if action=="stale" && !watch.active {
        if state.pending.len()>=capacity {return false;}
        watch.active=true;watch.stale_delivered=false;watch.episode=watch.episode.saturating_add(1);
    } else if action=="recovery" && watch.active {
        let notify=watch.stale_delivered&&rule.notify_recovery;
        state.pending.retain(|event|event.key!=key||event.kind!="stale");
        if notify&&state.pending.len()>=capacity {return false;}
        watch.active=false;
        if !notify {watch.stale_delivered=false;return true;}
    } else {return false;}
    let message=rule.notification_message(action,||if action=="stale" {
        format!("{} ({}): no {} reading received for at least {} seconds.",watch.label,watch.mac,watch.attribute,rule.stale_after_s)
    } else {
        format!("{} ({}): {} readings resumed.",watch.label,watch.mac,watch.attribute)
    });
    let value=watch.last_value.as_ref().map(render_value).unwrap_or_default();
    log::warn!(target:"ble.automation","{message}");
    state.pending.push_back(Notification {id:format!("{}-{}-{}-{action}",watch.rule_id,watch.mac,watch.episode),
        key:key.into(),kind:action.into(),message,device:watch.label.clone(),attribute:watch.attribute.clone(),
        value,unit:crate::pipeline::default_unit(&watch.attribute).unwrap_or("").to_string(),attempts:0,next_attempt_s:now});
    true
}

/// Compact textual form of the last decoded value, used by REST templates.
fn render_value(value: &Value) -> String {
    match value {
        Value::String(text)=>text.clone(),
        other=>other.to_string(),
    }
}

pub fn status(path: &str,devices: &[crate::config::DeviceConfig]) -> Result<Value,String> {
    let state=load_state(Path::new(path))?;
    Ok(json!({"success":true,"engine":"availability",
        "enabled":devices.iter().any(|device|device.enabled&&device.rules.iter().any(|rule|rule.enabled)),
        "initialized":Path::new(path).exists(),"state_file":path,
        "watches":state.watches.values().collect::<Vec<_>>(),"pending":state.pending.len(),"last_error":state.last_error}))
}

fn http_agent(config: &WebhookConfig) -> Result<ureq::Agent,String> {
    let mut tls=ureq::tls::TlsConfig::builder();
    if !config.ca_file.is_empty() {
        let file=File::open(&config.ca_file).map_err(|_|"cannot open automation CA file")?;
        let mut bytes=Vec::new();file.take(STATE_LIMIT+1).read_to_end(&mut bytes).map_err(|_|"cannot read automation CA file")?;
        if bytes.len() as u64>STATE_LIMIT {return Err("automation CA file exceeds 1 MiB".into());}
        let mut certificates=Vec::new();
        for item in ureq::tls::parse_pem(&bytes) {
            if let ureq::tls::PemItem::Certificate(certificate)=item.map_err(|_|"invalid automation PEM CA file")? {certificates.push(certificate);}
        }
        if certificates.is_empty() {return Err("automation CA file contains no certificates".into());}
        tls=tls.root_certs(ureq::tls::RootCerts::new_with_certs(&certificates));
    }
    let mut builder=ureq::Agent::config_builder().timeout_global(Some(Duration::from_millis(config.timeout_ms)))
        .max_redirects(0).proxy(None).http_status_as_error(false).tls_config(tls.build());
    if config.ipv4_only {builder=builder.ip_family(ureq::config::IpFamily::Ipv4Only);}
    Ok(builder.build().into())
}

/// Substitute `{name}` placeholders in REST URL/body/header templates.
fn expand_template(template: &str,event: &Notification,title: &str) -> String {
    let mut text=template.to_string();
    let values=[("event",event.kind.as_str()),("message",event.message.as_str()),("id",event.id.as_str()),
        ("title",title),("device",event.device.as_str()),("attribute",event.attribute.as_str()),
        ("value",event.value.as_str()),("unit",event.unit.as_str())];
    for (name,value) in values {text=text.replace(&format!("{{{name}}}"),value);}
    text
}

fn split_header(header: &str) -> Option<(&str,&str)> {
    let (name,value)=header.split_once(':')?;
    let name=name.trim();
    if name.is_empty() {return None;}
    Some((name,value.trim()))
}

fn deliver(agent: &ureq::Agent,config: &WebhookConfig,event: &Notification) -> Result<(),String> {
    let title=if event.kind=="recovery" {"BLE gateway: readings resumed"} else {"BLE gateway: missing reading"};
    let outcome = match config.provider {
        Provider::Ntfy|Provider::Gotify=>{
            let mut request=agent.post(&config.url).header("Idempotency-Key",&event.id);
            let body=if config.provider==Provider::Ntfy {
                request=request.header("Content-Type","text/plain; charset=utf-8").header("Title",title)
                    .header("Priority",config.priority.to_string());
                if !config.tags.is_empty() {request=request.header("Tags",&config.tags);}
                if !config.token.is_empty() {request=request.header("Authorization",format!("Bearer {}",config.token));}
                event.message.clone()
            } else {
                request=request.header("Content-Type","application/json").header("X-Gotify-Key",&config.token);
                json!({"title":title,"message":event.message,"priority":config.priority,
                    "extras":{"client::display":{"contentType":"text/plain"}}}).to_string()
            };
            request.send(body)
        }
        Provider::Rest=>{
            let url=expand_template(&config.url,event,title);
            let body=expand_template(&config.body,event,title);
            let mut request=agent.get(&url).header("Idempotency-Key",&event.id)
                .header("Accept",config.content_type.as_str());
            if !config.token.is_empty() {request=request.header("Authorization",format!("Bearer {}",config.token));}
            if let Some((name,value))=split_header(&config.header) {request=request.header(name,value);}
            match config.method.to_ascii_uppercase().as_str() {
                "GET"=>request.call(),
                "PUT"=>{
                    let mut request=agent.put(&url).header("Idempotency-Key",&event.id)
                        .header("Content-Type",config.content_type.as_str());
                    if !config.token.is_empty() {request=request.header("Authorization",format!("Bearer {}",config.token));}
                    if let Some((name,value))=split_header(&config.header) {request=request.header(name,value);}
                    request.send(body)
                }
                "PATCH"=>{
                    let mut request=agent.patch(&url).header("Idempotency-Key",&event.id)
                        .header("Content-Type",config.content_type.as_str());
                    if !config.token.is_empty() {request=request.header("Authorization",format!("Bearer {}",config.token));}
                    if let Some((name,value))=split_header(&config.header) {request=request.header(name,value);}
                    request.send(body)
                }
                _=>{
                    let mut request=agent.post(&url).header("Idempotency-Key",&event.id)
                        .header("Content-Type",config.content_type.as_str());
                    if !config.token.is_empty() {request=request.header("Authorization",format!("Bearer {}",config.token));}
                    if let Some((name,value))=split_header(&config.header) {request=request.header(name,value);}
                    request.send(body)
                }
            }
        }
    };
    match outcome {
        Ok(response) if (200..300).contains(&response.status().as_u16())=>Ok(()),
        Ok(response)=>Err(format!("webhook returned HTTP {}",response.status().as_u16())),
        Err(_)=>Err("HTTPS webhook delivery failed; check connectivity, clock and trusted CA".into()),
    }
}

pub fn test_webhook(config: &WebhookConfig) -> Result<Value,String> {
    send_webhook_test(config,"BLE gateway: explicit webhook configuration test.".into())
}

pub fn test_rule(rule: &AutomationRule) -> Result<Value,String> {
    rule.validate()?;
    send_webhook_test(&rule.effective_webhook(),rule.notification_message("test",||"BLE gateway: explicit webhook configuration test.".into()))
}

fn send_webhook_test(config: &WebhookConfig,message: String) -> Result<Value,String> {
    config.validate(true)?;
    let event=Notification {id:format!("ble-test-{}",now_seconds()),key:String::new(),kind:"test".into(),
        message,device:"test".into(),attribute:"test".into(),value:String::new(),unit:String::new(),
        attempts:0,next_attempt_s:0};
    deliver(&http_agent(config)?,config,&event)?;
    Ok(json!({"success":true,"message":"HTTPS webhook test delivered"}))
}

#[derive(Clone)]
struct Observation {
    received: Instant,
    wall_s: u64,
    value: Value,
}

struct Target {
    key: String,
    observation: String,
    rule: AutomationRule,
    webhook: WebhookConfig,
    agent: ureq::Agent,
    initial_age_s: u64,
}

pub struct Automation {
    observations: Arc<Mutex<BTreeMap<String,Observation>>>,
    watched: std::collections::HashSet<String>,
    stopped: Arc<AtomicBool>,
    worker: Option<JoinHandle<()>>,
}

fn report_error(state: &mut Persistent,error: String) {
    if state.last_error!=error {log::warn!(target:"ble.automation","{error}");state.last_error=error;}
}

fn sender_step(store: &StateStore,state: &mut Persistent,config: &WebhookConfig,now: u64,
    delivery: impl FnOnce(&Notification)->Result<(),String>) -> Result<(),String> {
    let Some(index)=state.pending.iter().position(|event|event.next_attempt_s<=now) else {return Ok(());};
    if state.pending[index].attempts>=config.max_attempts {
        state.pending.remove(index);report_error(state,"webhook attempt limit reached; event suppressed to avoid duplicate notifications".into());
        return store.save(state);
    }
    let previous=state.pending[index].clone();
    state.pending[index].attempts+=1;state.pending[index].next_attempt_s=now.saturating_add(config.retry_s);
    if let Err(error)=store.save(state) {state.pending[index]=previous;return Err(error);}
    let event=state.pending[index].clone();
    match delivery(&event) {
        Ok(())=>{
            state.pending.remove(index);
            if event.kind=="stale" {if let Some(watch)=state.watches.get_mut(&event.key) {watch.stale_delivered=true;}}
            state.last_error.clear();
            log::info!(target:"ble.automation","notification delivered: {}",event.id);
        }
        Err(error)=>{
            report_error(state,error);
            if event.attempts>=config.max_attempts {state.pending.remove(index);}
        }
    }
    store.save(state)
}

impl Automation {
    pub fn start(path: &str,devices: &[crate::config::DeviceConfig]) -> Result<Self,String> {
        let store=StateStore::open(Path::new(path))?;
        let mut state=load_state(Path::new(path))?;
        let mut targets=Vec::new();let mut watched=std::collections::HashSet::new();
        let now=now_seconds();
                for device in devices.iter().filter(|device|device.enabled) {
                    for rule in device.rules.iter().filter(|rule|rule.enabled) {
                        rule.validate()?;
            let mut hasher=std::collections::hash_map::DefaultHasher::new();serde_json::to_vec(rule).map_err(|error|error.to_string())?.hash(&mut hasher);
            let fingerprint=hasher.finish();
                let address=crate::config::parse_mac(&device.mac)?;
                let mac=address.iter().map(|byte|format!("{byte:02X}")).collect::<String>();
                let key=format!("{}|{mac}",rule.id);let observation=format!("{mac}|{}",rule.attribute);
                if !state.watches.get(&key).is_some_and(|watch|watch.attribute==rule.attribute) {
                    state.pending.retain(|event|event.key!=key);
                    state.watches.insert(key.clone(),WatchState {fingerprint,rule_id:rule.id.clone(),mac:mac.clone(),attribute:rule.attribute.clone(),label:device.metadata().name,..Default::default()});
                }
                if let Some(watch)=state.watches.get_mut(&key) {watch.fingerprint=fingerprint;}
                let initial_age_s=state.watches[&key].last_seen_s.map(|seen|now.saturating_sub(seen)).unwrap_or(0);
                let webhook=rule.effective_webhook();
                watched.insert(observation.clone());targets.push(Target {key,observation,rule:rule.clone(),agent:http_agent(&webhook)?,webhook,initial_age_s});
            }
        }
        let keys=targets.iter().map(|target|target.key.clone()).collect::<std::collections::HashSet<_>>();
        state.watches.retain(|key,_|keys.contains(key));
        state.pending.retain(|event|keys.contains(&event.key));
        store.save(&state)?;
        let observations=Arc::new(Mutex::new(BTreeMap::<String,Observation>::new()));
        let worker_observations=Arc::clone(&observations);let stopped=Arc::new(AtomicBool::new(false));let worker_stopped=Arc::clone(&stopped);
        let worker=std::thread::Builder::new().name("ble-automation".into()).spawn(move||{
            let started=Instant::now();let mut last_save=Instant::now();
            while !worker_stopped.load(Ordering::Relaxed) {
                let latest=worker_observations.lock().map(|values|values.clone()).unwrap_or_default();
                let now=now_seconds();let mut changed=false;
                for target in &targets {
                    if worker_stopped.load(Ordering::Relaxed) {break;}
                    let rule=&target.rule;let watch=state.watches.get_mut(&target.key).expect("validated availability watch");
                    let age=if let Some(observation)=latest.get(&target.observation) {
                        watch.last_seen_s=Some(observation.wall_s);watch.last_value=Some(observation.value.clone());observation.received.elapsed().as_secs()
                    } else {target.initial_age_s.saturating_add(started.elapsed().as_secs())};
                    match evaluate(age,rule.stale_after_s,watch.active) {
                        Some(action) if action!="stale"||started.elapsed().as_secs()>=rule.startup_grace_s=>{
                            changed|=transition(&mut state,&target.key,action,rule,256,now);
                        }
                        _=>{}
                    }
                }
                let saved=if changed||last_save.elapsed()>=Duration::from_secs(30) {
                    match store.save(&state) {Ok(())=>{last_save=Instant::now();true},Err(error)=>{report_error(&mut state,error);false}}
                } else {true};
                if saved && !worker_stopped.load(Ordering::Relaxed) {
                    if let Some(event)=state.pending.iter().find(|event|event.next_attempt_s<=now) {
                        if let Some(target)=targets.iter().find(|target|target.key==event.key) {
                            if let Err(error)=sender_step(&store,&mut state,&target.webhook,now,|event|deliver(&target.agent,&target.webhook,event)) {report_error(&mut state,error);}
                        }
                    }
                }
                if !worker_stopped.load(Ordering::Relaxed) {std::thread::park_timeout(Duration::from_secs(1));}
            }
            if let Err(error)=store.save(&state) {log::error!("cannot save final automation state: {error}");}
        }).map_err(|error|error.to_string())?;
        Ok(Self {observations,watched,stopped,worker:Some(worker)})
    }

    pub fn observe(&self,mac: &str,measurements: &[crate::pipeline::Measurement]) {
        let Ok(mut latest)=self.observations.lock() else {return;};
        for measurement in measurements {
            let key=format!("{mac}|{}",measurement.name);
            if !self.watched.contains(&key) {continue;}
            let value=measurement.value.to_json();
            if value.is_null()||value.is_array()||value.is_object()||(measurement.name=="temperature"&&!value.is_number()) {continue;}
            latest.insert(key,Observation {received:Instant::now(),wall_s:now_seconds(),value});
        }
    }
}

impl Drop for Automation {
    fn drop(&mut self) {
        self.stopped.store(true,Ordering::Relaxed);
        if let Some(worker)=self.worker.take() {worker.thread().unpark();if worker.join().is_err(){log::error!("automation worker panicked");}}
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rule_message_and_tgs_override_only_when_filled() {
        let mut rule=AutomationRule::default();
        assert_eq!(rule.notification_message("stale",||"automatic".into()),"automatic");
        assert_eq!(rule.effective_webhook().tags,"thermometer");
        rule.message="Custom reading alert\nSecond line".into();rule.tgs="warning,thermometer".into();rule.validate().unwrap();
        assert_eq!(rule.notification_message("stale",||panic!("default must not replace a compiled message")),rule.message);
        assert_eq!(rule.effective_webhook().tags,"warning,thermometer");
        assert_eq!(rule.webhook.tags,"thermometer");
        let key="temperature_missing|AABBCCDDEEFF";let mut state=Persistent::default();
        state.watches.insert(key.into(),WatchState {rule_id:rule.id.clone(),mac:"AABBCCDDEEFF".into(),attribute:"temperature".into(),..Default::default()});
        assert!(transition(&mut state,key,"stale",&rule,10,1000));assert_eq!(state.pending[0].message,rule.message);
        rule.message=" \n\t".into();rule.tgs="   ".into();rule.validate().unwrap();
        assert_eq!(rule.notification_message("stale",||"automatic".into()),"automatic");assert_eq!(rule.effective_webhook().tags,"thermometer");
        rule.tgs="unsafe\r\nHeader: value".into();assert!(rule.validate().is_err());
    }

    #[test]
    fn recovery_message_overrides_only_the_recovery_notification() {
        let mut rule=AutomationRule::default();
        rule.message="Rilettura mancante".into();
        rule.recovery_message="Rilettura ripresa".into();
        rule.validate().unwrap();
        assert_eq!(rule.notification_message("stale",||panic!("custom stale text")),"Rilettura mancante");
        assert_eq!(rule.notification_message("recovery",||panic!("custom recovery text")),"Rilettura ripresa");
        // A blank recovery text keeps the automatic wording.
        rule.recovery_message="  \n ".into();
        assert_eq!(rule.notification_message("recovery",||"automatic recovery".into()),"automatic recovery");
        // Recovery text is bounded exactly like the stale text.
        rule.recovery_message="x".repeat(4097);assert!(rule.validate().is_err());
    }

    #[test]
    fn rest_provider_validates_and_expands_templates() {
        let mut webhook=WebhookConfig::default();
        webhook.provider=Provider::Rest;webhook.url="https://example.invalid/hook?kind=ble".into();
        webhook.method="post".into();webhook.validate(true).unwrap();
        assert_eq!(webhook.method.to_ascii_uppercase(),"POST");
        webhook.method="DELETE".into();assert!(webhook.validate(true).is_err());
        webhook.method="PUT".into();webhook.validate(true).unwrap();
        webhook.content_type="application/json\r\nX: y".into();assert!(webhook.validate(true).is_err());
        webhook.content_type="application/json".into();
        webhook.header="X-Token: abc".into();webhook.validate(true).unwrap();
        webhook.header="X-Token abc".into();assert!(webhook.validate(true).is_err());
        webhook.header="X-Token: a\r\nb".into();assert!(webhook.validate(true).is_err());
        webhook.header=String::new();
        // Generic REST endpoints may keep a query string, ntfy/gotify may not.
        webhook.provider=Provider::Ntfy;assert!(webhook.validate(true).is_err());
        webhook.url="http://example.invalid/hook".into();webhook.provider=Provider::Rest;
        assert!(webhook.validate(true).is_err());

        let event=Notification {id:"id-1".into(),kind:"stale".into(),message:"m".into(),
            device:"Cucina".into(),attribute:"temperature".into(),value:"21.5".into(),unit:"°C".into(),
            ..Notification::default()};
        let expanded=expand_template(webhook_probe(),&event,"BLE gateway: missing reading");
        assert_eq!(expanded,r#"{"event":"stale","device":"Cucina","attribute":"temperature","value":"21.5","unit":"°C","message":"m","title":"BLE gateway: missing reading"}"#);
    }

    fn webhook_probe() -> &'static str {
        r#"{"event":"{event}","device":"{device}","attribute":"{attribute}","value":"{value}","unit":"{unit}","message":"{message}","title":"{title}"}"#
    }

    #[test]
    fn availability_threshold_has_one_stale_and_one_recovery_transition() {
        let rule=AutomationRule::default();rule.validate().unwrap();
        assert!(!rule.enabled);assert_eq!(rule.stale_after_s,600);
        for (age,active,expected) in [(599,false,None),(600,false,Some("stale")),(900,true,None),(0,true,Some("recovery")),(0,false,None)] {
            assert_eq!(evaluate(age,600,active),expected);
        }
    }

    #[test]
    fn legacy_global_rules_migrate_to_each_device_without_global_output() {
        let legacy:LegacyAutomationConfig=serde_json::from_value(json!({"enabled":false})).unwrap();
        assert_eq!(legacy.rules.len(),1);
        let mut config:crate::config::Config=serde_json::from_value(json!({
            "automation":{"enabled":true,"state_file":"/tmp/availability-migration.json",
                "webhook":{"enabled":true,"url":"https://ntfy.example.org/synthetic","token":"synthetic-token","ipv4_only":true},
                "rules":[{"id":"temperature_missing","enabled":true,"attribute":"temperature","stale_after_s":600}]},
            "rules":[{"name":"unused","source":"opened","after_s":10}],
            "devices":[{"mac":"AABBCCDDEEFF"},{"mac":"112233445566"}]
        })).unwrap();
        config.prepare_availability(Path::new("/tmp/test/config.yaml")).unwrap();config.validate().unwrap();
        assert_eq!(config.availability_state_file,"/tmp/availability-migration.json");
        for device in &config.devices {
            assert_eq!(device.rules.len(),1);assert!(device.rules[0].enabled);
            assert_eq!(device.rules[0].webhook.token,"synthetic-token");assert_eq!(device.rules[0].stale_after_s,600);
        }
        let serialized=serde_json::to_value(&config).unwrap();
        assert!(serialized.get("automation").is_none());assert!(serialized.get("rules").is_none());
        assert!(serialized["devices"][0]["rules"][0].get("workflows").is_none());
        assert!(serialized["devices"][0]["rules"][0]["webhook"].get("enabled").is_none());
    }

    #[test]
    fn device_rules_have_independent_webhooks_and_enable_switches() {
        let mut config:crate::config::Config=serde_json::from_value(json!({"devices":[
            {"mac":"AABBCCDDEEFF","rules":[
                {"id":"temperature","enabled":true,"attribute":"temperature","stale_after_s":600,
                 "webhook":{"url":"https://ntfy.example.org/first","token":"first-token"}},
                {"id":"humidity","enabled":false,"attribute":"humidity","stale_after_s":300,"webhook":{}}]},
            {"mac":"112233445566","rules":[
                {"id":"temperature","enabled":true,"attribute":"temperature","stale_after_s":1200,
                 "webhook":{"provider":"gotify","url":"https://gotify.example.org/message","token":"second-token"}}]}
        ]})).unwrap();
        config.prepare_availability(Path::new("/tmp/test/config.yaml")).unwrap();config.validate().unwrap();
        assert_ne!(config.devices[0].rules[0].webhook.url,config.devices[1].rules[0].webhook.url);
        assert_ne!(config.devices[0].rules[0].webhook.token,config.devices[1].rules[0].webhook.token);
        config.devices[0].rules[1].enabled=true;assert!(config.validate().is_err());
        config.devices[0].rules[1].enabled=false;
        config.devices[0].rules[1].id="temperature".into();assert!(config.validate().is_err());
    }

    #[test]
    fn migration_keeps_an_existing_active_episode_without_resending() {
        let directory=std::env::temp_dir().join(format!("ble-availability-migration-{}",std::process::id()));std::fs::create_dir_all(&directory).unwrap();
        let path=directory.join("state.json");let key="temperature_missing|AABBCCDDEEFF";
        let store=StateStore::open(&path).unwrap();let mut state=Persistent::default();
        state.watches.insert(key.into(),WatchState {fingerprint:42,rule_id:"temperature_missing".into(),mac:"AABBCCDDEEFF".into(),attribute:"temperature".into(),active:true,stale_delivered:true,episode:8,last_seen_s:Some(now_seconds().saturating_sub(4000)),..Default::default()});
        store.save(&state).unwrap();drop(store);
        let mut device:crate::config::DeviceConfig=serde_json::from_value(json!({"mac":"AABBCCDDEEFF"})).unwrap();
        let mut rule=AutomationRule {enabled:true,..Default::default()};rule.webhook.url="https://127.0.0.1:1/test".into();rule.webhook.timeout_ms=100;device.rules.push(rule);
        let monitor=Automation::start(path.to_str().unwrap(),&[device]).unwrap();drop(monitor);
        let restored=load_state(&path).unwrap();assert!(restored.watches[key].active);assert_eq!(restored.watches[key].episode,8);assert!(restored.pending.is_empty());
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn webhook_validation_requires_https_and_masks_tokens() {
        let mut config=WebhookConfig::default();
        for url in ["http://localhost/topic","https://user:password@example.org/topic","https://example.org/topic?token=secret"] {
            config.url=url.into();assert!(config.validate(true).is_err());
        }
        config.url="https://ntfy.example.org/thermometers".into();config.validate(true).unwrap();
        config.provider=Provider::Gotify;assert!(config.validate(true).is_err());
        config.url="https://gotify.example.org/message".into();config.token="private-token".into();
        config.validate(true).unwrap();assert!(!format!("{config:?}").contains("private-token"));
    }

    #[test]
    fn episodes_are_persistent_and_recovery_cancels_undelivered_alerts() {
        let directory=std::env::temp_dir().join(format!("ble-automation-state-{}",std::process::id()));
        std::fs::create_dir_all(&directory).unwrap();
        let path=directory.join("state.json");
        let store=StateStore::open(&path).unwrap();assert!(StateStore::open(&path).is_err());
        let rule=AutomationRule::default();let key="temperature_missing|AABBCCDDEEFF";
        let mut state=Persistent::default();state.watches.insert(key.into(),WatchState {rule_id:rule.id.clone(),mac:"AABBCCDDEEFF".into(),attribute:"temperature".into(),label:"Outside".into(),..Default::default()});
        assert!(transition(&mut state,key,"stale",&rule,10,1000));
        assert!(!transition(&mut state,key,"stale",&rule,10,1100));
        store.save(&state).unwrap();let mut state=load_state(&path).unwrap();assert_eq!(state.pending.len(),1);
        assert!(!transition(&mut state,key,"stale",&rule,10,1200));
        assert!(transition(&mut state,key,"recovery",&rule,10,1300));assert!(state.pending.is_empty());
        assert!(transition(&mut state,key,"stale",&rule,10,2000));
        state.pending.clear();state.watches.get_mut(key).unwrap().stale_delivered=true;
        assert!(transition(&mut state,key,"recovery",&rule,10,2100));assert_eq!(state.pending.len(),1);
        assert!(!transition(&mut state,key,"recovery",&rule,10,2200));
        assert_eq!(state.pending[0].kind,"recovery");
        drop(store);std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn default_delivery_attempt_is_reserved_before_io_and_never_replayed() {
        let directory=std::env::temp_dir().join(format!("ble-automation-attempt-{}",std::process::id()));std::fs::create_dir_all(&directory).unwrap();
        let path=directory.join("state.json");let store=StateStore::open(&path).unwrap();
        let config=WebhookConfig::default();let mut state=Persistent::default();
        state.pending.push_back(Notification {id:"test-episode".into(),key:"watch".into(),kind:"stale".into(),message:"Test".into(),..Notification::default()});
        sender_step(&store,&mut state,&config,100,|_|{
            assert_eq!(load_state(&path).unwrap().pending[0].attempts,1);
            Err("simulated transport failure".into())
        }).unwrap();
        assert!(state.pending.is_empty());
        state.pending.push_back(Notification {id:"interrupted-episode".into(),key:"watch".into(),kind:"stale".into(),message:"Test".into(),attempts:1,..Notification::default()});
        store.save(&state).unwrap();let mut restarted=load_state(&path).unwrap();
        sender_step(&store,&mut restarted,&config,200,|_|panic!("an interrupted attempt must not be replayed by default")).unwrap();
        assert!(restarted.pending.is_empty());drop(store);std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn worker_tracks_equal_temperature_not_other_attributes_and_deduplicates_restart() {
        let directory=std::env::temp_dir().join(format!("ble-automation-worker-{}",std::process::id()));std::fs::create_dir_all(&directory).unwrap();
        let path=directory.join("state.json");
        let mut rule=AutomationRule {enabled:true,startup_grace_s:0,stale_after_s:2,..Default::default()};
        rule.webhook.url="https://127.0.0.1:1/test".into();rule.webhook.timeout_ms=100;
        let mut device:crate::config::DeviceConfig=serde_json::from_value(json!({"mac":"AABBCCDDEEFF","label":"Test sensor"})).unwrap();
        device.rules.push(rule);
        let temperature=crate::pipeline::Measurement {name:"temperature".into(),value:crate::codec::value::Value::Float(20.0),unit:"C".into()};
        let battery=crate::pipeline::Measurement {name:"battery_level".into(),value:crate::codec::value::Value::Int(90),unit:"%".into()};
        let monitor=Automation::start(path.to_str().unwrap(),&[device.clone()]).unwrap();
        monitor.observe("AABBCCDDEEFF",std::slice::from_ref(&temperature));
        for _ in 0..4 {
            std::thread::sleep(Duration::from_millis(600));
            monitor.observe("AABBCCDDEEFF",std::slice::from_ref(&temperature));
        }
        assert!(load_state(&path).unwrap().pending.is_empty());
        let deadline=Instant::now()+Duration::from_secs(5);
        loop {
            monitor.observe("AABBCCDDEEFF",std::slice::from_ref(&battery));
            if load_state(&path).unwrap().watches.values().any(|watch|watch.active) {break;}
            assert!(Instant::now()<deadline,"battery-only packets incorrectly kept temperature fresh");
            std::thread::sleep(Duration::from_millis(100));
        }
        drop(monitor);
        let before=load_state(&path).unwrap().watches.values().next().unwrap().episode;
        let monitor=Automation::start(path.to_str().unwrap(),&[device]).unwrap();
        std::thread::sleep(Duration::from_millis(1100));assert_eq!(load_state(&path).unwrap().watches.values().next().unwrap().episode,before);
        monitor.observe("AABBCCDDEEFF",&[temperature]);
        let deadline=Instant::now()+Duration::from_secs(3);
        while load_state(&path).unwrap().watches.values().any(|watch|watch.active) {
            assert!(Instant::now()<deadline,"undelivered stale alarm was not cancelled");
            std::thread::sleep(Duration::from_millis(50));
        }
        let stopped=Instant::now();drop(monitor);assert!(stopped.elapsed()<Duration::from_secs(1));
        std::fs::remove_dir_all(directory).unwrap();
    }
}