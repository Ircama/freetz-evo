// SPDX-License-Identifier: GPL-2.0-or-later
//
// Matter controller for Freetz-EVO — `matter-bridge` milestone 2.
//
// A native, in-box Matter **controller** (commissioner + interaction-model
// client) built on rs-matter's controller-side primitives. It is the second
// binary of the `matter-bridge` package: `matter-bridge` is the verified
// WebSocket front end (python-matter-server-compatible JSON API on TCP 5580),
// this program is the Matter protocol engine it drives.
//
// ## What rs-matter already provides on the controller side
//
//   * `onboard::Commissioner` — `commission()` drives the whole PASE phase:
//     `ArmFailSafe` -> `AddTrustedRootCertificate` -> `AddNOC`;
//     `complete_via_case()` drives phase 2: operational discovery + CASE +
//     `CommissioningComplete`.
//   * `onboard::cac::{RcacGenerator, IcacGenerator}` and
//     `onboard::noc::NocGenerator` — the controller's own fabric PKI
//     (RCAC -> ICAC -> controller NOC / device NOC).
//   * `Matter::with_state(|state| state.fabrics.add(..))` — fabric install.
//   * `im::client` (`ImClient`) — read / write / invoke / subscribe
//     transactions with a remote node.
//   * `transport().wait_mdns_resolve_request()` / `try_deposit_mdns_resolve()`
//     — the hook a controller-side mDNS resolver plugs into.
//
// ## Milestone plan
//
//   M2.1 (this file)  controller fabric PKI + PASE commissioning (phase 1) and
//                     CASE finalisation (phase 2) of a device at a known
//                     address.
//   M2.2              real mDNS operational discovery, replacing `--peer`.
//                     NOTE: rs-matter's own resolver backends are D-Bus
//                     (zbus/avahi) or desktop daemons (astro-dnssd, zeroconf)
//                     and are not available in the FRITZ!Box image, so the
//                     resolver has to be written against UDP 5353 directly.
//   M2.3              node interview (BasicInformation, Descriptor, cluster
//                     lists) and persistent subscriptions -> `attribute_updated`
//                     events for the WebSocket front end.
//   M2.4              network commissioning: `set_wifi_credentials`,
//                     `set_thread_dataset` (cluster 0x0031 over PASE).
//   M2.5              stable fabric material (persisted ICAC key so that a
//                     second commissioning after a restart does not need a new
//                     fabric) + IPC with `matter-bridge`.

use core::num::NonZeroU8;
use core::pin::pin;

use std::net::{SocketAddr, SocketAddrV6, UdpSocket};
use std::path::PathBuf;
use std::process::ExitCode;

use embassy_futures::select::{select, Either};
use embassy_time::{Duration, Timer};

use log::{error, info, warn};

use rs_matter::cert::gen::VALID_FOREVER;
use rs_matter::cert::{MAX_CERT_TLV_AND_ASN1_LEN, MAX_CERT_TLV_LEN};
use rs_matter::crypto::{
    default_crypto, CanonAeadKey, CanonPkcSecretKey, Crypto, Rng as _, SecretKey,
    SigningSecretKey,
};
use rs_matter::dm::devices::test::{DAC_PRIVKEY, TEST_DEV_ATT, TEST_DEV_COMM, TEST_DEV_DET};
use rs_matter::error::{Error, ErrorCode};
use rs_matter::onboard::cac::{IcacGenerator, RcacGenerator};
use rs_matter::onboard::noc::NocGenerator;
use rs_matter::onboard::{CommissionOptions, Commissioner};
use rs_matter::persist::DirKvBlobStore;
use rs_matter::transport::network::mdns::{DottedName, MdnsRemoteService};
use rs_matter::transport::network::{Address, IpAddr, MatterRemoteService, NoNetwork};
use rs_matter::utils::init::InitMaybeUninit;
use rs_matter::Matter;

use static_cell::StaticCell;

/// Whole-flow timeout for each phase.
const PHASE_TIMEOUT_SECS: u64 = 60;

/// Conventional administrative identities (same values chip-tool uses).
const FABRIC_ID: u64 = 1;
const CONTROLLER_NODE_ID: u64 = 112233;
const ADMIN_VENDOR_ID: u16 = 0xFFF1;

/// Default device node ID assigned to the commissioned device.
const DEFAULT_DEVICE_NODE_ID: u64 = 112234;

/// Default test passcode (`TEST_DEV_COMM`).
const DEFAULT_PASSCODE: u32 = 20202021;

/// Default peer: the rs-matter test device on loopback.
const DEFAULT_PEER: &str = "[::1]:5540";

static CTRL_MATTER: StaticCell<Matter> = StaticCell::new();

fn main() -> ExitCode {
    let opts = match Opts::parse() {
        Ok(opts) => opts,
        Err(msg) => {
            eprintln!("matter-bridge-ctl: {msg}");
            eprintln!(
                "usage: matter-bridge-ctl commission [--peer <addr:port>] \
                 [--passcode <n>] [--node-id <n>] [--store <dir>] [--json] [--verbose]"
            );
            return ExitCode::FAILURE;
        }
    };

    let level = if opts.verbose { "debug" } else { "info" };
    env_logger::builder()
        .filter_level(match level {
            "debug" => log::LevelFilter::Debug,
            _ => log::LevelFilter::Info,
        })
        .format_timestamp_secs()
        .init();

    match futures_lite::future::block_on(run(&opts)) {
        Ok(summary) => {
            if opts.json {
                println!("{}", summary.to_json());
            } else {
                println!(
                    "matter-bridge-ctl: commissioned device {} on fabric index {} \
                     (device-side fabric slot {})",
                    summary.device_node_id, summary.controller_fab_idx, summary.device_fab_index
                );
            }
            ExitCode::SUCCESS
        }
        Err(e) => {
            error!("matter-bridge-ctl: commissioning FAILED — {e:?}");
            if opts.json {
                println!(
                    "{{\"success\":false,\"error\":\"{}\"}}",
                    escape(&format!("{e:?}"))
                );
            }
            ExitCode::FAILURE
        }
    }
}

/// Command line options.
struct Opts {
    peer: SocketAddr,
    passcode: u32,
    device_node_id: u64,
    store: PathBuf,
    json: bool,
    verbose: bool,
}

impl Opts {
    fn parse() -> Result<Self, String> {
        let mut opts = Self {
            peer: DEFAULT_PEER
                .parse()
                .map_err(|e| format!("bad default peer: {e}"))?,
            passcode: DEFAULT_PASSCODE,
            device_node_id: DEFAULT_DEVICE_NODE_ID,
            store: PathBuf::from("/tmp/matter-bridge-ctl"),
            json: false,
            verbose: false,
        };

        let mut args = std::env::args().skip(1);
        let mut cmd_seen = false;

        while let Some(arg) = args.next() {
            match arg.as_str() {
                // The only sub-command so far; more arrive with M2.3/M2.5.
                "commission" => cmd_seen = true,
                "-h" | "--help" => return Err("help requested".into()),
                "--json" => opts.json = true,
                "-v" | "--verbose" => opts.verbose = true,
                "--peer" => {
                    let value = args.next().ok_or("--peer needs an address")?;
                    opts.peer = value
                        .parse()
                        .map_err(|e| format!("--peer: {value}: {e}"))?;
                }
                "--passcode" => {
                    let value = args.next().ok_or("--passcode needs a number")?;
                    opts.passcode = value
                        .parse()
                        .map_err(|e| format!("--passcode: {value}: {e}"))?;
                }
                "--node-id" => {
                    let value = args.next().ok_or("--node-id needs a number")?;
                    // Accept both plain decimal and 0x-prefixed hex.
                    let (digits, radix) = match value.strip_prefix("0x") {
                        Some(hex) => (hex, 16),
                        None => (value.as_str(), 10),
                    };
                    opts.device_node_id = u64::from_str_radix(digits, radix)
                        .map_err(|e| format!("--node-id: {value}: {e}"))?;
                }
                "--store" | "--store-dir" => {
                    let value = args.next().ok_or("--store needs a path")?;
                    opts.store = PathBuf::from(value);
                }
                other => return Err(format!("unknown argument `{other}`")),
            }
        }

        if !cmd_seen {
            return Err("no command given".into());
        }

        Ok(opts)
    }
}

/// Machine-readable result, in the shape the WebSocket front end expects.
struct Summary {
    controller_fab_idx: u8,
    device_fab_index: NonZeroU8,
    device_node_id: u64,
}

impl Summary {
    fn to_json(&self) -> String {
        format!(
            "{{\"success\":true,\"fabric_id\":{},\"controller_fabric_index\":{},\
             \"device_fabric_index\":{},\"node_id\":\"{}\"}}",
            FABRIC_ID,
            self.controller_fab_idx,
            self.device_fab_index,
            node_hex(self.device_node_id)
        )
    }
}

fn node_hex(node_id: u64) -> String {
    format!("0x{node_id:016x}")
}

fn escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

/// Bind the Matter transport socket and run the commissioning flow on top of it.
///
/// The transport pump (`Matter::run`) must stay alive for the whole flow — it
/// owns the MRP retransmission timers and the session state — hence the
/// `select` between the pump and the flow future.
async fn run(opts: &Opts) -> Result<Summary, Error> {
    if std::fs::create_dir_all(&opts.store).is_err() {
        warn!("cannot create store directory {}", opts.store.display());
    }

    let bind_addr: SocketAddr = "[::]:0".parse().unwrap();
    let socket =
        async_io::Async::<UdpSocket>::bind(bind_addr).map_err(|_| ErrorCode::NoNetworkInterface)?;
    info!(
        "controller bound on {}",
        socket.get_ref().local_addr().unwrap()
    );

    let crypto = default_crypto(rand::rng(), DAC_PRIVKEY);
    let matter = CTRL_MATTER.uninit().init_with(Matter::init(
        &TEST_DEV_DET,
        TEST_DEV_COMM,
        &TEST_DEV_ATT,
        // Local port 0: the kernel picks one, matching the ephemeral socket.
        // A real controller also listens on 5540 so that peers can reach it
        // (M2.3), but commissioning itself is purely client-initiated.
        0,
    ));

    // Persistence: fabrics, ACLs and basic info are re-hydrated from here.
    let store = DirKvBlobStore::new(opts.store.clone());
    let kv = matter.kv(store);
    matter.startup(&kv)?;

    let transport_fut = matter.run(&crypto, &socket, &socket, NoNetwork);
    let flow_fut = commission(matter, &crypto, &opts);

    let mut transport_fut = pin!(transport_fut);
    let mut flow_fut = pin!(flow_fut);

    match select(&mut transport_fut, &mut flow_fut).await {
        Either::First(r) => {
            error!("transport exited prematurely: {r:?}");
            Err(ErrorCode::NoExchange.into())
        }
        Either::Second(result) => result,
    }
}

/// Install a controller fabric and commission the device at `opts.peer`.
///
/// M2.1 always creates a fresh fabric, which is exactly what chip-tool does by
/// default: it keeps `chip-tool` simple and verifiable, at the cost of the
/// device accumulating one fabric per commissioning run. A stable, persisted
/// fabric is M2.5.
async fn commission<C: Crypto>(
    matter: &Matter<'_>,
    crypto: &C,
    opts: &Opts,
) -> Result<Summary, Error> {
    // ---- Controller fabric PKI -------------------------------------------------

    // Offline root of trust. RCAC, then ICAC below it; the RCAC private key is
    // discarded immediately (a real controller would never hold it at all).
    let mut rcac_buf = [0u8; MAX_CERT_TLV_AND_ASN1_LEN];
    let mut rcac_gen = RcacGenerator::new(&mut rcac_buf);
    let (rcac_priv, rcac) = rcac_gen.generate(crypto, FABRIC_ID, VALID_FOREVER)?;

    let mut icac_buf = [0u8; MAX_CERT_TLV_AND_ASN1_LEN];
    let mut icac_gen = IcacGenerator::new(&mut icac_buf);
    let (icac_priv, icac) = icac_gen.generate(crypto, rcac_priv.reference(), rcac, VALID_FOREVER)?;
    drop(rcac_priv);

    // Controller operational keypair and its CSR.
    let controller_secret_key = crypto.generate_secret_key()?;
    let mut controller_csr_buf = [0u8; 256];
    let controller_csr = controller_secret_key.csr(&mut controller_csr_buf)?;
    let mut controller_secret_key_canon = CanonPkcSecretKey::new();
    controller_secret_key.write_canon(&mut controller_secret_key_canon)?;

    // Signs our NOC now and the device NOC during commissioning. The NOC serial
    // number is derived from the NodeID internally.
    let mut noc_buf = [0u8; MAX_CERT_TLV_AND_ASN1_LEN];
    let mut noc_generator = NocGenerator::create(icac_priv.reference(), rcac, icac, &mut noc_buf)?;

    let controller_noc = noc_generator.generate(
        crypto,
        controller_csr,
        CONTROLLER_NODE_ID,
        &[],
        VALID_FOREVER,
    )?;

    // Fabric IPK: 16 random bytes shared by every node on the fabric.
    let mut ipk = CanonAeadKey::new();
    crypto.rand()?.fill_bytes(ipk.access_mut());

    let controller_fab_idx = matter.with_state(|state| {
        state
            .fabrics
            .add(
                crypto,
                controller_secret_key_canon.reference(),
                rcac,
                controller_noc,
                icac,
                Some(ipk.reference()),
                ADMIN_VENDOR_ID,
                CONTROLLER_NODE_ID,
            )
            .map(|fab| fab.fab_idx())
    })?;

    // ---- Phase 1: PASE, ArmFailSafe → AddNOC -----------------------------------

    // Scratch slice used to stage the fabric's RCAC/ICAC bytes across the
    // asynchronous on-wire invokes; one certificate's worth is enough because
    // the two transfers are sequenced.
    let mut commissioner_buf = [0u8; MAX_CERT_TLV_LEN];
    let mut commissioner = Commissioner::new(
        matter,
        crypto,
        controller_fab_idx,
        &mut noc_generator,
        &mut commissioner_buf,
    );

    let commission_opts = CommissionOptions {
        // M2.4: fetch the device's attestation from the DCL and validate the
        // certificate chain. Until then rs-matter has no verification path and
        // refuses to commission with `allow_test_attestation: false`.
        allow_test_attestation: true,
        ..CommissionOptions::default()
    };

    info!("phase 1: PASE + ArmFailSafe + AddNOC against {}", opts.peer);
    let phase1 = {
        let mut fut = pin!(commissioner.commission(
            Address::Udp(opts.peer),
            opts.passcode,
            &commission_opts,
            opts.device_node_id,
            VALID_FOREVER,
        ));
        let mut timeout = pin!(Timer::after(Duration::from_secs(PHASE_TIMEOUT_SECS)));
        match select(&mut fut, &mut timeout).await {
            Either::First(r) => r?,
            Either::Second(_) => {
                error!("commission() timed out after {PHASE_TIMEOUT_SECS}s");
                return Err(ErrorCode::RxTimeout.into());
            }
        }
    };
    info!(
        "phase 1 ok: device fabric slot {}, node {}",
        phase1.fabric_index,
        node_hex(phase1.device_node_id)
    );

    // ---- Phase 2: operational discovery, CASE, CommissioningComplete -----------

    // Phase 2 deliberately ignores the address phase 1 used and re-discovers the
    // device on its operational network. Without a controller-side mDNS resolver
    // (M2.2) we answer the stack's resolve requests from the address given on the
    // command line: enough to finish commissioning over loopback or on a device
    // that kept its address.
    let peer_v6 = match opts.peer {
        SocketAddr::V6(v6) => v6,
        // Matter transports are IPv6; a v4 peer enters the dual-stack socket
        // as a v4-mapped address.
        SocketAddr::V4(v4) => {
            SocketAddrV6::new(v4.ip().to_ipv6_mapped(), v4.port(), 0, 0)
        }
    };

    info!("phase 2: discovery + CASE + CommissioningComplete");
    {
        let resolver = pin!(direct_resolver(matter, opts.device_node_id, peer_v6));
        let case = pin!(commissioner.complete_via_case(&phase1));
        let mut combined = pin!(select(case, resolver));
        let mut timeout = pin!(Timer::after(Duration::from_secs(PHASE_TIMEOUT_SECS)));

        match select(&mut combined, &mut timeout).await {
            Either::First(Either::First(r)) => r?,
            Either::First(Either::Second(_)) => unreachable!("the resolver never returns"),
            Either::Second(_) => {
                error!("complete_via_case() timed out after {PHASE_TIMEOUT_SECS}s");
                return Err(ErrorCode::RxTimeout.into());
            }
        }
    }
    info!("phase 2 ok: CASE established, CommissioningComplete acknowledged");

    Ok(Summary {
        controller_fab_idx: controller_fab_idx.get(),
        device_fab_index: phase1.fabric_index,
        device_node_id: phase1.device_node_id,
    })
}

/// Answer the stack's operational mDNS resolve requests with a fixed address.
///
/// Stand-in for the real resolver (M2.2): same hook, no network traffic. The
/// stack asks for the address of a node ID as soon as `complete_via_case()` runs
/// its CASE attempt.
async fn direct_resolver(matter: &Matter<'_>, node_id: u64, addr: SocketAddrV6) -> ! {
    loop {
        let service = matter.transport().wait_mdns_resolve_request().await;

        let MatterRemoteService::Operational {
            node_id: wanted, ..
        } = &service
        else {
            continue;
        };

        if *wanted != node_id {
            continue;
        }

        let mut name = heapless::String::<128>::new();
        service.instance_name(&mut name);

        matter.transport().try_deposit_mdns_resolve(
            &MdnsRemoteService {
                instance_name: DottedName(name.as_str()),
                port: Some(addr.port()),
                addrs: core::iter::once(IpAddr::V6(*addr.ip())),
                txt: false.then_some(("T", "")).into_iter(),
                scope_id: 0,
            },
            &[],
        );
    }
}
