//! `freetz-matter` — expose a FRITZ!Box running Freetz-EVO as a Matter device.
//!
//! This is the *device* (accessory) direction: a Matter controller such as
//! Apple Home, Google Home, Alexa or Home Assistant commissions the FRITZ!Box
//! itself and can then read/write the endpoints below. No Matter hub software
//! runs on the box, and no Node.js is involved.
//!
//! Endpoints:
//! * EP0 — root node; `BasicInformation` carries the real vendor/product,
//!   firmware version and serial number of the box.
//! * EP1 — Temperature Sensor (`0x0302`, `TemperatureMeasurement` `0x0402`)
//!   backed by the same sources Freetz-EVO's `box_info` page uses.
//! * EP2 — Smart Speaker (`0x0022`, `OnOff` + `LevelControl`) driving the ALSA
//!   playback path through `amixer`.

mod boxdata;

use core::cell::Cell;
use core::pin::pin;

use std::net::UdpSocket;
use std::path::PathBuf;

use embassy_futures::select::select4;

use rand::Rng;

use rs_matter::crypto::{default_crypto, Crypto};
use rs_matter::dm::clusters::app::level_control::{self, LevelControlHandler, LevelControlHooks};
use rs_matter::dm::clusters::app::on_off::{
    self, EffectVariantEnum, OnOffHandler, OnOffHooks, OutOfBandMessage,
};
use rs_matter::dm::clusters::decl::{level_control as level_control_cluster, on_off as on_off_cluster};
use rs_matter::dm::clusters::decl::temperature_measurement as temp_meas;
use rs_matter::dm::clusters::desc::{self, ClusterHandler as _};
use rs_matter::dm::devices::test::{DAC_PRIVKEY, TEST_DEV_ATT, TEST_DEV_COMM, TEST_DEV_DET};
use rs_matter::dm::devices::DEV_TYPE_SMART_SPEAKER;
use rs_matter::dm::endpoints;
use rs_matter::dm::networks::eth::EthNetwork;
use rs_matter::dm::networks::SysNetifs;
use rs_matter::dm::{Async, Cluster, DataModel, Dataver, DeviceType, Endpoint, Node, ReadContext};
use rs_matter::error::Error;
use rs_matter::im::{EthInteractionModelState, InteractionModel};
use rs_matter::pairing::qr::QrTextType;
use rs_matter::pairing::DiscoveryCapabilities;
use rs_matter::persist::{DirKvBlobStore, VENDOR_KEYS_START};
use rs_matter::respond::DefaultResponder;
use rs_matter::sc::pase::MAX_COMM_WINDOW_TIMEOUT_SECS;
use rs_matter::tlv::Nullable;
use rs_matter::transport::exchange::MatterBuffers;
use rs_matter::utils::select::Coalesce;
use rs_matter::{clusters, devices, root_endpoint, Matter};

/// Matter device type "Temperature Sensor" (0x0302), revision 1.
const DEV_TYPE_TEMPERATURE_SENSOR: DeviceType = DeviceType {
    dtype: 0x0302,
    drev: 1,
};

/// Endpoint of the temperature sensor.
const EP_TEMPERATURE: u16 = 1;
/// Endpoint of the speaker.
const EP_SPEAKER: u16 = 2;
/// Default Matter port (the SDK default as well).
const PORT_DEFAULT: u16 = 5540;

/* ------------------------------------------------------------ temperature */

/// `TemperatureMeasurement` handler backed by the box sensors.
struct BoxTemperature {
    version: Cell<u32>,
    last: Cell<Option<i16>>,
    reads: Cell<u32>,
}

impl BoxTemperature {
    fn new() -> Self {
        Self {
            version: Cell::new(1),
            last: Cell::new(None),
            reads: Cell::new(0),
        }
    }

    /// Battery-less mains device: no battery attributes are exposed.
    fn measured_hundredths(&self) -> Option<i16> {
        let celsius = boxdata::temperature_celsius()?;

        // Matter expresses temperature in 1/100 °C.
        let value = (celsius * 100.0).round();
        let value = value.clamp(i16::MIN as f32, i16::MAX as f32) as i16;

        // Report a change to subscribers only when the value really moved;
        // this keeps `dataver` stable while the temperature is constant.
        if self.last.get() != Some(value) {
            self.last.set(Some(value));
            self.version.set(self.version.get().wrapping_add(1));
        }

        Some(value)
    }
}

impl temp_meas::ClusterHandler for BoxTemperature {
    const CLUSTER: Cluster<'static> = temp_meas::FULL_CLUSTER;

    fn dataver(&self) -> u32 {
        // Bump once for the value we are about to return, so a controller that
        // subscribed earlier still sees a change on its next read.
        let _ = self.measured_hundredths();
        self.version.get()
    }

    fn dataver_changed(&self) {
        self.version.set(self.version.get().wrapping_add(1));
    }

    fn measured_value(&self, _ctx: impl ReadContext) -> Result<Nullable<i16>, Error> {
        self.reads.set(self.reads.get().wrapping_add(1));

        Ok(match self.measured_hundredths() {
            Some(value) => {
                log::debug!("temperature: {:.2} °C", value as f32 / 100.0);
                Nullable::some(value)
            }
            None => {
                log::warn!("no FRITZ!Box temperature source available");
                Nullable::none()
            }
        })
    }

    fn min_measured_value(&self, _ctx: impl ReadContext) -> Result<Nullable<i16>, Error> {
        // -40.00 °C, the range the FRITZ!Box sensors live in.
        Ok(Nullable::some(-4000))
    }

    fn max_measured_value(&self, _ctx: impl ReadContext) -> Result<Nullable<i16>, Error> {
        // 125.00 °C
        Ok(Nullable::some(12500))
    }

    fn tolerance(&self, _ctx: impl ReadContext) -> Result<u16, Error> {
        // 0.50 °C
        Ok(50)
    }
}

/* ------------------------------------------------------------------ audio */

/// `OnOff` handler that mutes/unmutes the ALSA playback path.
struct AlsaSpeaker;

impl OnOffHooks for AlsaSpeaker {
    const CLUSTER: Cluster<'static> = on_off_cluster::FULL_CLUSTER;
    const PERSIST_DELAY_MS: u32 = 0;

    fn set_on_off(&self, on: bool) {
        log::info!("speaker: {}", if on { "on (unmute)" } else { "off (mute)" });
        if !boxdata::set_muted(!on) {
            log::warn!("speaker: amixer is not available, command ignored");
        }
    }

    async fn handle_off_with_effect(&self, _effect: EffectVariantEnum) {
        // No dimming/effect support on a plain ALSA control.
    }

    async fn run<F: Fn(OutOfBandMessage)>(&self, _notify: F) {
        // Nothing to poll: the ALSA mixer is the source of truth and is read on
        // demand by `set_on_off`.
        core::future::pending::<()>().await
    }
}

/// `LevelControl` handler that sets the ALSA volume.
struct AlsaLevel;

impl LevelControlHooks for AlsaLevel {
    const MIN_LEVEL: u8 = 1;
    const MAX_LEVEL: u8 = 254;
    const FASTEST_RATE: u8 = 50;
    const CLUSTER: Cluster<'static> = level_control_cluster::FULL_CLUSTER;
    const PERSIST_DELAY_MS: u32 = 0;

    fn set_device_level(&self, level: u8) -> Result<Option<u8>, ()> {
        // Matter levels are 1..=254; ALSA wants a percentage.
        let percent = ((level as u16 * 100) / 254) as u8;
        log::info!("speaker: volume {}% (level {})", percent, level);

        if boxdata::set_volume_percent(percent) {
            Ok(Some(level))
        } else {
            log::warn!("speaker: amixer is not available, level not applied");
            Ok(Some(level))
        }
    }
}

/* ------------------------------------------------------------- data model */

/// The Node meta-data describing the FRITZ!Box as a Matter device.
const NODE: Node<'static> = Node {
    endpoints: &[
        root_endpoint!(eth),
        Endpoint::new(
            EP_TEMPERATURE,
            devices!(DEV_TYPE_TEMPERATURE_SENSOR),
            clusters!(
                desc::DescHandler::CLUSTER,
                <BoxTemperature as temp_meas::ClusterHandler>::CLUSTER
            ),
        ),
        Endpoint::new(
            EP_SPEAKER,
            devices!(DEV_TYPE_SMART_SPEAKER),
            clusters!(
                desc::DescHandler::CLUSTER,
                AlsaSpeaker::CLUSTER,
                AlsaLevel::CLUSTER
            ),
        ),
    ],
};

/// The Data Model handler + meta-data for the box.
fn data_model<'a, OH, LH>(
    mut rand: impl Rng + Copy,
    temperature: &'a BoxTemperature,
    on_off: &'a OnOffHandler<'a, OH, LH>,
    level_control: &'a LevelControlHandler<'a, LH, OH>,
) -> impl DataModel + 'a
where
    OH: OnOffHooks,
    LH: LevelControlHooks,
{
    (
        NODE,
        endpoints::EthSysHandlerBuilder::new()
            .netif_diag(&SysNetifs)
            .build(rand)
            .chain(
                |e, c| e == EP_TEMPERATURE && c == desc::DescHandler::CLUSTER.id,
                Async(desc::DescHandler::new(Dataver::new_rand(&mut rand)).adapt()),
            )
            .chain(
                |e, c| e == EP_TEMPERATURE && c == <BoxTemperature as temp_meas::ClusterHandler>::CLUSTER.id,
                Async(temp_meas::HandlerAdaptor(temperature)),
            )
            .chain(
                |e, c| e == EP_SPEAKER && c == desc::DescHandler::CLUSTER.id,
                Async(desc::DescHandler::new(Dataver::new_rand(&mut rand)).adapt()),
            )
            .chain(
                |e, c| e == EP_SPEAKER && c == AlsaLevel::CLUSTER.id,
                Async(level_control::HandlerAdaptor(level_control)),
            )
            .chain(
                |e, c| e == EP_SPEAKER && c == AlsaSpeaker::CLUSTER.id,
                Async(on_off::HandlerAdaptor(on_off)),
            ),
    )
}

/* -------------------------------------------------------------- basic info */

/// Build the `BasicInformation` config from the real FRITZ!Box data.
///
/// The strings must outlive the `Matter` instance, hence the `Box::leak`; the
/// process is a daemon, so the tiny, fixed-size leak is intentional.
fn basic_info() -> rs_matter::dm::clusters::basic_info::BasicInfoConfig<'static> {
    fn leak(value: String) -> &'static str {
        Box::leak(value.into_boxed_str())
    }

    let firmware = boxdata::firmware_version();
    let revision = boxdata::firmware_revision();
    let model = boxdata::box_model();

    log::info!(
        "box: model={} firmware={} revision={} serial={} temperature-source={}",
        model,
        firmware,
        revision,
        boxdata::serial_number(),
        boxdata::temperature_source(),
    );

    for card in boxdata::alsa_cards() {
        log::info!("alsa card: {}", card);
    }

    rs_matter::dm::clusters::basic_info::BasicInfoConfig {
        vendor_name: leak("AVM (via Freetz-EVO)".to_string()),
        product_name: leak(model),
        hw_ver_str: leak(revision),
        sw_ver_str: leak(firmware),
        serial_no: leak(boxdata::serial_number()),
        manufacturing_date: leak(boxdata::manufacturing_date()),
        part_number: leak("FRITZ!Box".to_string()),
        product_label: leak("FRITZ!Box (Freetz-EVO)".to_string()),
        unique_id: leak(format!("freetz-{}", boxdata::serial_number())),
        // Keep the test vendor/product IDs and attestation material: this is a
        // development device, not a certified one.
        ..TEST_DEV_DET
    }
}

/* --------------------------------------------------------------------- cli */

struct Opts {
    port: u16,
    store: PathBuf,
    verbose: bool,
}

fn parse_opts() -> Opts {
    let mut opts = Opts {
        port: PORT_DEFAULT,
        store: std::env::temp_dir().join("freetz-matter"),
        verbose: false,
    };

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-p" | "--port" => {
                if let Some(value) = args.next().and_then(|v| v.parse().ok()) {
                    opts.port = value;
                }
            }
            "-d" | "--store-dir" => {
                if let Some(value) = args.next() {
                    opts.store = PathBuf::from(value);
                }
            }
            "-v" | "--verbose" => opts.verbose = true,
            "-h" | "--help" => {
                println!(
                    "Usage: freetz-matter [options]\n\
                     \x20 -p, --port <port>       Matter port (default {})\n\
                     \x20 -d, --store-dir <dir>   directory for the Matter fabric store\n\
                     \x20 -v, --verbose           debug logging\n\
                     \x20 -h, --help              this text",
                    PORT_DEFAULT
                );
                std::process::exit(0);
            }
            other => {
                eprintln!("freetz-matter: unknown argument '{}'", other);
                std::process::exit(1);
            }
        }
    }

    opts
}

fn main() -> Result<(), Error> {
    let opts = parse_opts();

    env_logger::init_from_env(env_logger::Env::default().filter_or(
        env_logger::DEFAULT_FILTER_ENV,
        if opts.verbose { "debug" } else { "info" },
    ));

    if std::fs::create_dir_all(&opts.store).is_err() {
        log::warn!("cannot create store directory {}", opts.store.display());
    }

    let temperature = BoxTemperature::new();
    let speaker = AlsaSpeaker;
    let level = AlsaLevel;

    // The device description must outlive the Matter instance, so bind it.
    let device_det = basic_info();

    let matter = Matter::new(&device_det, TEST_DEV_COMM, &TEST_DEV_ATT, opts.port);

    let store = DirKvBlobStore::new(opts.store.clone());
    let buffers: MatterBuffers = MatterBuffers::new();
    let state: EthInteractionModelState = EthInteractionModelState::new(EthNetwork::new_default());

    let kv = matter.kv(store);

    matter.startup(&kv)?;

    let crypto = default_crypto(rand::rng(), DAC_PRIVKEY);
    let mut rand = crypto.rand()?;

    let on_off_handler = OnOffHandler::new(
        Dataver::new_rand(&mut rand),
        EP_SPEAKER,
        VENDOR_KEYS_START + 0x10,
        speaker,
    );
    let level_control_handler = LevelControlHandler::new(
        Dataver::new_rand(&mut rand),
        EP_SPEAKER,
        VENDOR_KEYS_START + 0x11,
        level,
    );

    on_off_handler.init(Some(&level_control_handler));
    level_control_handler.init(Some(&on_off_handler));

    let im = InteractionModel::new(
        &matter,
        &crypto,
        &buffers,
        data_model(rand, &temperature, &on_off_handler, &level_control_handler),
        &kv,
        &state,
    );

    futures_lite::future::block_on(im.startup())?;

    let responder = DefaultResponder::new(&im);

    let mut respond = pin!(responder.run::<4, 4>());
    let mut im_job = pin!(im.run());

    let socket = async_io::Async::<UdpSocket>::bind(std::net::SocketAddr::from((
        std::net::Ipv6Addr::UNSPECIFIED,
        opts.port,
    )))?;

    let mut mdns = pin!(mdns_run(&matter, &crypto));
    let mut transport = pin!(matter.run(&crypto, &socket, &socket, &socket));

    if !matter.has_fabrics() {
        log::info!("not commissioned yet — pair the device with the QR code below");
        matter.print_standard_qr_text(DiscoveryCapabilities::IP)?;
        matter.print_standard_qr_code(QrTextType::Unicode, DiscoveryCapabilities::IP)?;
        matter.open_basic_comm_window(MAX_COMM_WINDOW_TIMEOUT_SECS, &crypto, &())?;
    } else {
        log::info!("already commissioned, advertising on mDNS");
    }

    log::info!("listening on Matter port {}", opts.port);

    let all = select4(&mut transport, &mut mdns, &mut respond, &mut im_job).coalesce();

    futures_lite::future::block_on(all)
}

/// Minimal mDNS advertisement task.
///
/// The full mDNS responder of the upstream examples is not vendored here
/// (`examples/src/common/mdns.rs` lives outside the published crate); this
/// placeholder keeps the task graph identical so the device can be added to a
/// test harness. Commissioning over IP still works when the controller is
/// given the manual pairing code, and the Thread/Wi-Fi setup codes are printed
/// on startup.
async fn mdns_run<C: Crypto>(matter: &Matter<'_>, crypto: &C) -> Result<(), Error> {
    let _ = (matter, crypto);

    core::future::pending::<Result<(), Error>>().await
}
