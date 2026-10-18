//! ble2uart-gateway: gateway between an ESP32 running pvvx ADV_BLE2UART
//! (ble50_scan, USB CDC-ACM) and home automation front-ends.
//!
//! The daemon is also its own configuration tool: the web interface (a shell
//! CGI) never parses YAML, it asks for values with `--get` / `--set` and lets
//! `--check-config` validate the file with the real schema.
//!
//! ```text
//! ble2uart-gateway --config <file>                     run the daemon
//! ble2uart-gateway --write-default-config <file>       create a configuration
//! ble2uart-gateway --check-config <file>               validate, print nothing on success
//! ble2uart-gateway --config <file> --get <key>         print one value (dotted path)
//! ble2uart-gateway --config <file> --set <key>=<value> change one value (atomic write)
//! ble2uart-gateway --config <file> --dump              print the whole configuration
//! ble2uart-gateway --serial <dev> --info               talk to the module: INFO
//! ble2uart-gateway --serial <dev> --scan [seconds]     print the advertisement stream
//! ```

mod codec;
mod config;
mod crypto;
mod link;
mod logger;
mod pipeline;
mod web;
mod mqtt;
mod influx;
mod managed_process;
mod matter;
mod profile;
#[cfg(feature = "matter")]
mod matter_server;
#[cfg(feature = "matter")]
mod matter_mdns;

// Next increments (see docs/make/ble2uart_gateway.md, roadmap):
//   mod codec;     spec driven advertisement/configuration codec (decode + encode)
//   mod model;     canonical attributes with units
//   mod registry;  devices, decode pipeline, derived rules, stable ids
//   mod expose;
//   mod rules;
//   mod frontend;  mysensors.rs / mqtt.rs / matter.rs

use config::Config;
use link::{Cmd, Event, Link, ScanFlags};
use std::io::Read;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

const DEFAULT_CONFIG: &str = "/etc/ble2uart-gateway/config.yaml";
static STOP_REQUESTED: AtomicBool = AtomicBool::new(false);
static RELOAD_LOGGING: AtomicBool = AtomicBool::new(false);

struct Args {
    config: PathBuf,
    serial: Option<String>,
    baudrate: Option<u32>,
    device: Option<String>,
    log_level: Option<String>,
    log_stdout: bool,
    log_color: Option<String>,
    trace_tx: Option<bool>,
    trace_rx: Option<bool>,
    trace_decode: Option<bool>,
    trace_phy: Option<bool>,
    comando: Comando,
}

enum Comando {
    Daemon,
    WriteDefault,
    CheckConfig,
    Get(String),
    Set(String, String),
    Dump,
    WebConfig(String),
    DecodeCaptures,
    Control(String, u64),
    Encode(String),
    Decode(String),
    Benchmark(String),
    Info,
    Scan(u64),
    Version,
}

fn usage() -> ! {
    eprintln!(
        "usage: ble2uart-gateway [--config <file>] [--serial <dev>] [--baudrate <n>] <action>\n\
         actions:\n\
         \x20 (none)                        run the daemon\n\
         \x20 --write-default-config        create a valid configuration file\n\
         \x20 --check-config                validate the configuration file\n\
         \x20 --get <key>                   print one value (dotted path)\n\
         \x20 --set <key>=<value>           change one value and write the file\n\
         \x20 --dump                        print the configuration\n\
         \x20 --decode-captures             decode private JSONL stdin offline, without serial\n\
         \x20 --encode <structure>          JSON stdin to wire hex\n\
         \x20 --decode <structure>          wire hex stdin to JSON\n\
         \x20 --benchmark-codec <structure> decode stdin 10000 times, report timings\n\
         \x20 --device <MAC>                use configured device key for codec\n\
         \x20 --foreground                  run normally, send logs to stdout\n\
         \x20 --log-level <level>           off/error/warn/info/debug/trace\n\
         \x20 --log-stdout                  send logs to stdout instead of stderr\n\
         \x20 --log-color <mode>            auto/always/never (default: auto)\n\
         \x20 --trace-tx / --no-trace-tx     enable/disable full serial TX hex\n\
         \x20 --trace-rx / --no-trace-rx     enable/disable full serial RX hex\n\
         \x20 --trace-decode / --no-trace-decode  enable/disable codec steps\n\
         \x20 --trace-phy / --no-trace-phy   trace received PHYs and decode outcomes\n\
         \x20 --info                        talk to the module: INFO and VERSION\n\
         \x20 --scan [seconds]              print the advertisement stream (60 s)\n\
         \x20 --version                     print the version"
    );
    std::process::exit(2);
}

fn parse_args() -> Args {
    parse_args_from(std::env::args().skip(1))
}

fn parse_args_from(mut iterator: impl Iterator<Item = String>) -> Args {
    let mut args = Args {
        config: DEFAULT_CONFIG.into(),
        serial: None,
        baudrate: None,
        device: None,
        log_level: None,
        log_stdout: false,
        log_color: None,
        trace_tx: None,
        trace_rx: None,
        trace_decode: None,
        trace_phy: None,
        comando: Comando::Daemon,
    };
    while let Some(arg) = iterator.next() {
        match arg.as_str() {
            "--config" | "--store" => {
                let value = iterator.next().unwrap_or_else(|| usage());
                args.config = PathBuf::from(value);
            }
            "--serial" => args.serial = iterator.next(),
            "--foreground" | "--log-stdout" => args.log_stdout = true,
            "--log-level" => args.log_level = Some(iterator.next().unwrap_or_else(|| usage())),
            "--log-color" => args.log_color = Some(iterator.next().unwrap_or_else(|| usage())),
            "--verbose" | "-v" => args.log_level = Some("debug".into()),
            "--trace-tx" => args.trace_tx = Some(true),
            "--no-trace-tx" => args.trace_tx = Some(false),
            "--trace-rx" => args.trace_rx = Some(true),
            "--no-trace-rx" => args.trace_rx = Some(false),
            "--trace-decode" => args.trace_decode = Some(true),
            "--no-trace-decode" => args.trace_decode = Some(false),
            "--trace-phy" => args.trace_phy = Some(true),
            "--no-trace-phy" => args.trace_phy = Some(false),
            "--device" => args.device = Some(iterator.next().unwrap_or_else(|| usage())),
            "--encode" => args.comando = Comando::Encode(iterator.next().unwrap_or_else(|| usage())),
            "--decode" => args.comando = Comando::Decode(iterator.next().unwrap_or_else(|| usage())),
            "--benchmark-codec" => args.comando = Comando::Benchmark(iterator.next().unwrap_or_else(|| usage())),
            "--baudrate" | "--baud" => {
                args.baudrate = iterator.next().and_then(|v| v.parse().ok())
            }
            "--write-default-config" => {
                if let Some(path) = iterator.next() {
                    args.config = PathBuf::from(path);
                }
                args.comando = Comando::WriteDefault;
            }
            "--check-config" => {
                if let Some(path) = iterator.next() {
                    args.config = PathBuf::from(path);
                }
                args.comando = Comando::CheckConfig;
            }
            "--get" => args.comando = Comando::Get(iterator.next().unwrap_or_else(|| usage())),
            "--set" => {
                let pair = iterator.next().unwrap_or_else(|| usage());
                match pair.split_once('=') {
                    Some((key, value)) => {
                        args.comando = Comando::Set(key.to_string(), value.to_string())
                    }
                    None => {
                        eprintln!("--set needs KEY=VALUE");
                        usage();
                    }
                }
            }
            "--dump" => args.comando = Comando::Dump,
            "--web-config" => args.comando = Comando::WebConfig(iterator.next().unwrap_or_else(|| usage())),
            "--decode-captures" => args.comando = Comando::DecodeCaptures,
            "--control" => {
                let action = iterator.next().unwrap_or_else(|| usage());
                let seconds = if action == "discover-start" { iterator.next().and_then(|value| value.parse().ok()).unwrap_or(30) } else { 0 };
                args.comando = Comando::Control(action, seconds);
            },
            "--info" => args.comando = Comando::Info,
            "--scan" => {
                let seconds = match iterator.next() {
                    Some(value) => value.parse().unwrap_or(60),
                    None => 60,
                };
                args.comando = Comando::Scan(seconds);
            }
            "--version" | "-V" => args.comando = Comando::Version,
            "-h" | "--help" => usage(),
            other => {
                eprintln!("unknown option {other}");
                usage();
            }
        }
    }
    args
}

fn main() -> std::process::ExitCode {
    let args = parse_args();
    let verbosity = match &args.comando {
        Comando::Version => 1,
        _ => logger::level_from_env(),
    };
    logger::init(verbosity);
    if let Err(message) = configure_logging(&args, None) {
        eprintln!("ble2uart-gateway: {message}");
        return std::process::ExitCode::FAILURE;
    }

    let outcome = match &args.comando {
        Comando::Version => {
            println!("{} {}", env!("CARGO_PKG_NAME"), env!("CARGO_PKG_VERSION"));
            Ok(())
        }
        Comando::WriteDefault => {
            let config = Config::default();
            config.save(&args.config).map(|_| {
                println!("{} written", args.config.display());
            })
        }
        Comando::CheckConfig => Config::load(&args.config, None, None).and_then(|_| load_spec(&args).map(|_| ())),
        Comando::Get(key) => Config::load(&args.config, None, None).and_then(|config| {
            config.get(key).map(|value| println!("{value}"))
        }),
        Comando::Set(key, value) => Config::load(&args.config, None, None).and_then(|mut config| {
            config.set(key, value)?;
            config.save(&args.config)
        }),
        Comando::Dump => Config::load(&args.config, None, None).map(|config| {
            print!("{}", serde_yaml::to_string(&config).unwrap_or_default());
        }),
        Comando::DecodeCaptures => decode_captures(&args),
        Comando::WebConfig(action) => {
            let mut input = String::new();
            if action != "read" {
                let _ = std::io::stdin().take(262145).read_to_string(&mut input);
            }
            let response = if input.len() > 262144 {
                Err("configuration exceeds 256 KiB".into())
            } else if action == "inspect" {
                load_spec(&args).and_then(|spec| web::inspect(&args.config, &spec, &input))
            } else {
                web::config_action(&args.config, action, &input)
            };
            println!("{}", response.unwrap_or_else(|error| serde_json::json!({"success":false, "error":error})));
            Ok(())
        },
        Comando::Info => module_info(&args),
        Comando::Control(action, seconds) => {
            println!("{}", web::control_client(action, *seconds).unwrap_or_else(|error| serde_json::json!({"success":false, "error":error})));
            Ok(())
        },
        Comando::Encode(format) => codec_command(&args, format, true, 1),
        Comando::Decode(format) => codec_command(&args, format, false, 1),
        Comando::Benchmark(format) => codec_command(&args, format, false, 10000),
        Comando::Scan(seconds) => scan(&args, *seconds),
        Comando::Daemon => run_daemon(&args),
    };

    match outcome {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(message) => {
            log::error!("{message}");
            eprintln!("ble2uart-gateway: {message}");
            std::process::ExitCode::FAILURE
        }
    }
}

fn decode_captures(args: &Args) -> Result<(), String> {
    use std::io::{BufRead, Write};
    let spec = load_spec(args)?;
    let input = std::io::stdin();
    let mut reader = input.lock();
    let output = std::io::stdout();
    let mut writer = std::io::BufWriter::new(output.lock());
    loop {
        let mut line = String::new();
        let count = std::io::Read::take(&mut reader, 16385).read_line(&mut line).map_err(|error| error.to_string())?;
        if count == 0 { break; }
        if count > 16384 { return Err("capture request exceeds 16 KiB".into()); }
        let request: Result<serde_json::Value, _> = serde_json::from_str(&line);
        let (identifier, result) = match request {
            Ok(request) => (request["case"].as_str().unwrap_or("").to_string(), web::inspect_capture(&args.config, &spec, &line)),
            Err(_) => (String::new(), Err("invalid capture JSON".into())),
        };
        let result = result.unwrap_or_else(|error| serde_json::json!({"success":false,"error":error}));
        writeln!(writer, "{}", serde_json::json!({"case":identifier,"result":result})).map_err(|error| error.to_string())?;
    }
    writer.flush().map_err(|error| error.to_string())
}

fn logging_settings(args: &Args, config: Option<&Config>, environment: Option<&str>) -> Result<(log::LevelFilter, bool, bool, bool, bool), String> {
    let level = args.log_level.as_deref().or(environment)
        .or_else(|| config.map(|config| config.log_level.as_str())).unwrap_or("info");
    Ok((logger::parse_level(level)?,
        args.trace_tx.unwrap_or(config.is_some_and(|config| config.diagnostics.tx_hex)),
        args.trace_rx.unwrap_or(config.is_some_and(|config| config.diagnostics.rx_hex)),
        args.trace_decode.unwrap_or(config.is_some_and(|config| config.diagnostics.decode)),
        args.trace_phy.unwrap_or(config.is_some_and(|config| config.diagnostics.phy))))
}

fn logging_color(args: &Args, environment: Option<&str>) -> Result<logger::ColorMode, String> {
    logger::parse_color_mode(args.log_color.as_deref().or(environment).unwrap_or("auto"))
}

fn configure_logging(args: &Args, config: Option<&Config>) -> Result<(), String> {
    let environment = std::env::var("RUST_LOG").ok();
    let (level, tx, rx, decode, phy) = logging_settings(args, config, environment.as_deref())?;
    let environment_color = std::env::var("BLE2UART_LOG_COLOR").ok();
    let color = logging_color(args, environment_color.as_deref())?;
    logger::configure(level, args.log_stdout, tx, rx, decode, phy);
    logger::configure_color(color);
    Ok(())
}

extern "C" fn signal_requested(signal: libc::c_int) {
    if signal == libc::SIGHUP {
        RELOAD_LOGGING.store(true, Ordering::Relaxed);
    } else {
        STOP_REQUESTED.store(true, Ordering::Relaxed);
    }
}

fn install_signals() -> Result<(), String> {
    for signal in [libc::SIGINT, libc::SIGTERM, libc::SIGHUP] {
        let mut action: libc::sigaction = unsafe { std::mem::zeroed() };
        action.sa_sigaction = signal_requested as *const () as libc::sighandler_t;
        unsafe { libc::sigemptyset(&mut action.sa_mask); }
        if unsafe { libc::sigaction(signal, &action, std::ptr::null_mut()) } != 0 {
            return Err(format!("sigaction: {}", std::io::Error::last_os_error()));
        }
    }
    Ok(())
}

fn reload_logging(args: &Args) {
    if RELOAD_LOGGING.swap(false, Ordering::Relaxed) {
        match Config::load(&args.config, args.serial.as_deref(), args.baudrate)
            .and_then(|config| configure_logging(args, Some(&config))) {
            Ok(()) => log::info!("logging configuration reloaded; scanner and device settings unchanged"),
            Err(error) => log::warn!("logging reload rejected, previous settings retained: {error}"),
        }
    }
}

fn load_spec(args: &Args) -> Result<codec::spec::Spec, String> {
    let mut spec = codec::spec::Spec::embedded()?;
    let override_path = args.config.with_file_name("codec.yaml");
    match std::fs::read_to_string(&override_path) {
        Ok(text) => {
            spec.merge(codec::spec::Spec::parse(&text)?);
            log::info!("loaded codec overrides: {}", override_path.display());
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {},
        Err(error) => return Err(format!("{}: {error}", override_path.display())),
    }
    spec.validate()?;
    Ok(spec)
}

fn codec_command(args: &Args, format: &str, encode: bool, iterations: usize) -> Result<(), String> {
    let startup = std::time::Instant::now();
    let spec = load_spec(args)?;
    let schema_us = startup.elapsed().as_micros();
    let params = if let Some(mac) = &args.device {
        let registry = pipeline::Registry::new(&Config::load(&args.config, None, None)?);
        let device = registry.devices.iter().find(|device| device.mac == pipeline::normalize_mac(mac))
            .ok_or("device not configured or disabled")?;
        Some(device.params.clone().ok_or("device has no valid 16-byte key")?)
    } else { None };
    let mut text = String::new();
    std::io::stdin().take(1024 * 1024 + 1).read_to_string(&mut text).map_err(|error| error.to_string())?;
    if text.len() > 1024 * 1024 { return Err("codec input exceeds 1 MiB".into()); }
    if encode {
        let json = serde_json::from_str(&text).map_err(|error| format!("invalid JSON: {error}"))?;
        let encoder = match &params {
            Some(params) => codec::encode::Encoder::with_key(&spec, params),
            None => codec::encode::Encoder::new(&spec),
        };
        let bytes = encoder.encode(format, &codec::value::Value::from_json(&json))?;
        println!("{}", codec::value::hex(&bytes));
    } else {
        let digits: String = text.chars().filter(|character| !character.is_ascii_whitespace()).collect();
        if !digits.is_ascii() || digits.len() % 2 != 0 { return Err("expected pairs of hexadecimal digits".into()); }
        let bytes: Vec<u8> = (0..digits.len()).step_by(2).map(|index| u8::from_str_radix(&digits[index..index + 2], 16))
            .collect::<Result<_, _>>().map_err(|_| "invalid hexadecimal input")?;
        let started = std::time::Instant::now();
        let mut decoded = codec::value::Value::List(Vec::new());
        for _ in 0..iterations {
            let decoder = match &params {
                Some(params) => codec::decode::Decoder::with_key(&spec, &bytes, params,
                    [*bytes.first().unwrap_or(&0), *bytes.get(1).unwrap_or(&0)]),
                None => codec::decode::Decoder::new(&spec, &bytes),
            };
            decoded = std::hint::black_box(decoder.decode(format).map_err(|error| error.0)?);
        }
        if iterations > 1 {
            let elapsed = started.elapsed().as_micros();
            eprintln!("schema_us={schema_us} samples={iterations} decode_us={elapsed} mean_us={:.2}", elapsed as f64 / iterations as f64);
        }
        println!("{}", serde_json::to_string(&decoded.to_json()).map_err(|error| error.to_string())?);
    }
    Ok(())
}

fn open_link(args: &Args, port_override: Option<&str>) -> Result<Link, String> {
    let (path, baudrate, reset) = match Config::load(&args.config, port_override, args.baudrate) {
        Ok(config) => (
            {
                configure_logging(args, Some(&config))?;
                config.serial.port.clone()
            }, config.serial.baudrate, config.serial.reset_on_open,
        ),
        Err(error) => {
            // The command line tools must also work with a broken or missing
            // configuration file: fall back to the defaults.
            log::debug!("configuration not used: {error}");
            (
                port_override.unwrap_or("/dev/ttyACM0").to_string(),
                args.baudrate.unwrap_or(115200),
                false,
            )
        }
    };
    if path.is_empty() {
        return Err("no serial port configured (serial.port or --serial)".into());
    }
    Link::open(&path, baudrate, reset)
}

fn module_info(args: &Args) -> Result<(), String> {
    let mut link = open_link(args, args.serial.as_deref())?;
    let timeout = Duration::from_secs(3);
    let (status, payload) = link.request(&link::build_command(Cmd::Info, [0; 6], &[]), Cmd::Info, timeout)?;
    if !status.is_ok() {
        return Err(format!("INFO: {}", status.as_str()));
    }
    let sw_version = match status { link::Status::Metadata(version) => version, _ => 0 };
    let bd_addr = payload.get(..6).unwrap_or(&[]);
    println!(
        "INFO   status=OK sw_version=0x{sw_version:02X} bd_addr={}",
        bd_addr.iter().map(|b| format!("{b:02X}")).collect::<Vec<_>>().join(":")
    );

    if let Ok((status, payload)) =
        link.request(&link::build_command(Cmd::Version, [0; 6], &[]), Cmd::Version, timeout)
    {
        if status.is_ok() {
            println!(
                "VERSION status=OK hw=0x{:02X} idf={}.{}.{}",
                payload.first().copied().unwrap_or(0),
                payload.get(3).copied().unwrap_or(0),
                payload.get(4).copied().unwrap_or(0),
                payload.get(5).copied().unwrap_or(0)
            );
        } else {
            println!("VERSION status={}", status.as_str());
        }
    }

    if let Ok((status, payload)) =
        link.request(&link::build_command(Cmd::Uart, [0; 6], &[0]), Cmd::Uart, timeout)
    {
        if status.is_ok() {
            println!(
                "UART   status=OK baud_index={} table_size={} rate={}",
                payload.get(1).copied().unwrap_or(0),
                payload.get(2).copied().unwrap_or(0),
                payload.get(3..6).map(|bytes| u32::from_le_bytes([bytes[0], bytes[1], bytes[2], 0])).unwrap_or(0)
            );
        } else {
            println!("UART   status={}", status.as_str());
        }
    }

    if let Ok((status, payload)) =
        link.request(&link::build_command(Cmd::Rfsdk, [0; 6], &[0]), Cmd::Rfsdk, timeout)
    {
        if status.is_ok() {
            println!(
                "RFSDK  status=OK power_index={} xtal_cap={} coded_min_units={}",
                payload.first().copied().unwrap_or(0),
                payload.get(1).copied().unwrap_or(0),
                payload.get(5).copied().unwrap_or(0)
            );
        } else {
            println!("RFSDK  status={}", status.as_str());
        }
    }

    if let Ok((status, payload)) =
        link.request(&link::gpio_evt_command(link::GpioEvtOp::Query, 0), Cmd::GpioEvt, timeout)
    {
        if status.is_ok() && payload.len() >= 4 {
            let mask = u32::from_le_bytes([payload[0], payload[1], payload[2], payload[3]]);
            println!("GPIOEVT status=OK armed_bitmap=0x{mask:08X}");
        } else {
            println!("GPIOEVT status={}", status.as_str());
        }
    }

    Ok(())
}

fn configure_scanner(link: &mut Link, config: &Config) -> Result<bool, String> {
    let (whitelist, addresses) = config.mac_filters()?;
    let timeout = Duration::from_millis(config.serial.command_timeout_ms);
    let (status, _) = link.request(&link::stop_scan_command(), Cmd::Scan, timeout)?;
    if !status.is_ok() {
        return Err(format!("cannot stop scanner before MAC filtering: {}", status.as_str()));
    }
    let (status, _) = link.request(&link::clear_mac_list_command(), Cmd::Clrm, timeout)?;
    match status {
        link::Status::Metadata(capacity) if usize::from(capacity) >= addresses.len() => {}
        _ => return Err("firmware did not confirm sufficient MAC filter capacity".into()),
    }
    let command = if whitelist { Cmd::Wmac } else { Cmd::Bmac };
    for (index, address) in addresses.iter().enumerate() {
        log::debug!("firmware MAC filter {} entry {}: {}", if whitelist { "whitelist" } else { "blacklist" }, index + 1, address.iter().map(|byte| format!("{byte:02X}")).collect::<Vec<_>>().join(":"));
        let wire: Vec<u8> = address.iter().rev().copied().collect();
        let (status, _) = link.request(&link::mac_list_command(whitelist, &wire), command, timeout)?;
        match status {
            link::Status::Metadata(count) if usize::from(count) == index + 1 => {}
            _ => return Err(format!("{} did not confirm MAC filter entry {}", command.name(), index + 1)),
        }
    }
    log::info!("firmware MAC filter applied: registered_only={} list={} entries={}", config.scanner.filter_known_devices, if whitelist { "whitelist" } else { "blacklist" }, addresses.len());
    link.pending.retain(|event| !matches!(event, Event::Adv(_)));
    if config.scanner.filter_known_devices && addresses.is_empty() {
        log::info!("scanner stopped: no enabled registered devices match the MAC filter");
        return Ok(false);
    }
    let flags = ScanFlags {
        own_addr_type: 0,
        discard_random: config.scanner.discard_random,
        discard_rpa: config.scanner.discard_rpa,
        dup_filter: config.scanner.dup_filter,
        active: config.scanner.active_scan,
        phy_coded: config.scanner.phy_coded,
        phy_1m: config.scanner.phy_1m,
    };
    let (status, _) = link.request(&link::scan_command(&flags, config.scanner.window_1m, config.scanner.window_coded), Cmd::Scan, timeout)?;
    if !status.is_ok() {
        return Err(format!("SCAN: {}", status.as_str()));
    }
    log::info!("scanner started: requested_1m={} requested_coded={}", flags.phy_1m, flags.phy_coded);
    Ok(true)
}

fn scan(args: &Args, seconds: u64) -> Result<(), String> {
    let config = Config::load(&args.config, args.serial.as_deref(), args.baudrate)?;
    configure_logging(args, Some(&config))?;
    let mut link = Link::open(&config.serial.port, config.serial.baudrate, config.serial.reset_on_open)?;
    if !configure_scanner(&mut link, &config)? {
        println!("SCAN   stopped: no enabled registered devices match the MAC filter");
        return Ok(());
    }
    println!(
        "SCAN   status=OK (1M window {} units, coded window {} units)",
        config.scanner.window_1m,
        config.scanner.window_coded
    );

    let deadline = std::time::Instant::now() + Duration::from_secs(seconds);
    let mut count = 0u64;
    while std::time::Instant::now() < deadline {
        match link.next(Duration::from_millis(500))? {
            Some(Event::Adv(report)) => {
                count += 1;
                println!(
                    "{:>6}  mac={} rssi={:>4} type={} {} len={:>3}  {}",
                    count,
                    report.mac_colon(),
                    report.rssi,
                    report.event_type,
                    report.phy_summary(),
                    report.data.len(),
                    report
                        .data
                        .iter()
                        .map(|b| format!("{b:02X}"))
                        .collect::<Vec<_>>()
                        .join("")
                );
            }
            Some(Event::Spontaneous { cmd, sub, payload, .. }) => {
                println!(
                    "GPIOEVT/event cmd=0x{cmd:02X} sub={sub} {}", 
                    payload.iter().map(|b| format!("{b:02X}")).collect::<Vec<_>>().join("")
                );
            }
            Some(Event::Debug(text)) => println!("firmware: {text}"),
            Some(other) => log::debug!("event: {other:?}"),
            None => {}
        }
    }
    let (status, _) = link.request(&link::stop_scan_command(), Cmd::Scan, Duration::from_secs(3))?;
    println!("STOP   status={}", status.as_str());
    Ok(())
}

/// The daemon.
///
/// Step 1 (this build): keep the scanner configured, watch the advertisement
/// stream and log the events, including the spontaneous GPIO edges. The codec,
/// the registry with the derived rules and the three front-ends plug into this
/// loop (see the roadmap in docs/make/ble2uart_gateway.md).
fn run_daemon(args: &Args) -> Result<(), String> {
    let config = Config::load(&args.config, args.serial.as_deref(), args.baudrate)?;
    configure_logging(args, Some(&config))?;
    install_signals()?;
    log::info!(
        "ble2uart-gateway {} starting: serial={} baudrate={} config={} devices={} frontends=mysensors:{} mqtt:{} matter:{} influx:{}",
        env!("CARGO_PKG_VERSION"),
        config.serial.port,
        config.serial.baudrate,
        args.config.display(),
        config.devices.len(),
        if config.frontends.mysensors.enabled { "on" } else { "off" },
        if config.frontends.mqtt.enabled { "on" } else { "off" },
        if config.frontends.matter.enabled { "on" } else { "off" },
        if config.frontends.influx.enabled { "on" } else { "off" },
    );

    // The specification is parsed once: it is the schema of every supported
    // format, and a failure here is fatal because a running daemon that cannot
    // decode anything looks exactly like an empty radio band.
    let spec = load_spec(args)?;
    let mut gateway = pipeline::Gateway::new(&config, spec)?;
    let control = web::ControlServer::bind()?;
    let mut discovery = web::Discovery::default();

    while !STOP_REQUESTED.load(Ordering::Relaxed) {
        reload_logging(args);
        serve_control(&control, &mut discovery, None, &config)?;
        match Link::open(
            &config.serial.port,
            config.serial.baudrate,
            config.serial.reset_on_open,
        ) {
            Ok(mut link) => {
                log::info!("serial link up: {}", config.serial.port);
                match link.request(
                    &link::build_command(Cmd::Info, [0; 6], &[]),
                    Cmd::Info,
                    Duration::from_secs(3),
                ) {
                    Ok((status, payload)) if status.is_ok() => log::info!(
                        "module: sw_version=0x{:02X} bd_addr={}",
                        match status { link::Status::Metadata(version) => version, _ => 0 },
                        payload
                            .get(..6)
                            .unwrap_or(&[])
                            .iter()
                            .map(|b| format!("{b:02X}"))
                            .collect::<Vec<_>>()
                            .join(":")
                    ),
                    Ok((status, _)) => log::warn!("INFO: {}", status.as_str()),
                    Err(error) => log::warn!("{error}"),
                }

                if let Err(error) = configure_scanner(&mut link, &config) {
                    log::warn!("scanner configuration failed; scanning will not start: {error}");
                    let _ = link.request(&link::stop_scan_command(), Cmd::Scan, Duration::from_secs(1));
                    std::thread::sleep(Duration::from_millis(config.serial.reconnect_delay_ms));
                    continue;
                }

                while !STOP_REQUESTED.load(Ordering::Relaxed) {
                    reload_logging(args);
                    if discovery.expired() {
                        discovery.until = None;
                        if let Err(error) = configure_scanner(&mut link, &config) {
                            discovery.error = error;
                            break;
                        }
                        log::info!("discovery finished; configured firmware MAC filters restored");
                    }
                    if let Err(error) = serve_control(&control, &mut discovery, Some(&mut link), &config) {
                        discovery.error = error;
                        break;
                    }
                    let event = match link.next(Duration::from_millis(100)) {
                        Ok(Some(event)) => event,
                        Ok(None) => continue,
                        Err(error) => {
                            log::warn!("{error}");
                            break;
                        }
                    };
                    match event {
                        Event::Adv(report) => {
                            discovery.observe(&report, &gateway.spec, &config);
                            gateway.on_advertisement(&report);
                        },
                        Event::Spontaneous { cmd, sub, payload, .. } => log::info!(
                            "spontaneous event cmd=0x{cmd:02X} sub={sub} data={}",
                            payload
                                .iter()
                                .map(|b| format!("{b:02X}"))
                                .collect::<Vec<_>>()
                                .join("")
                        ),
                        Event::Debug(text) => log::debug!("firmware: {text}"),
                        Event::Response { cmd, status, .. } => {
                            log::debug!("response 0x{cmd:02X}: {}", status.as_str())
                        }
                    }
                }
                if STOP_REQUESTED.load(Ordering::Relaxed) {
                    let _ = link.request(&link::stop_scan_command(), Cmd::Scan, Duration::from_secs(1));
                    log::info!("gateway stopped");
                    return Ok(());
                }
                log::warn!("serial link lost, reconnecting");
                discovery.until = None;
                discovery.error = "serial link lost; discovery cancelled".into();
            }
            Err(error) => {
                log::warn!(
                    "serial link unavailable ({error}); retrying in {} ms",
                    config.serial.reconnect_delay_ms
                );
                std::thread::sleep(Duration::from_millis(config.serial.reconnect_delay_ms));
            }
        }
    }
    Ok(())
}

fn serve_control(server: &web::ControlServer, discovery: &mut web::Discovery, mut link: Option<&mut Link>, config: &Config) -> Result<(), String> {
    let Some((stream, request)) = server.next() else { return Ok(()); };
    let action = request["action"].as_str().unwrap_or("");
    let mut restore_failed = None;
    let result: Result<serde_json::Value, String> = (|| {
        match action {
            "status" => {},
            "discover-start" => {
                let seconds = request["seconds"].as_u64().unwrap_or(0);
                if !(1..=300).contains(&seconds) { return Err("discovery duration must be between 1 and 300 seconds".into()); }
                if discovery.until.is_some() { return Err("discovery is already running".into()); }
                let serial = link.as_deref_mut().ok_or("serial link is unavailable")?;
                let mut unfiltered = config.clone();
                unfiltered.scanner.filter_known_devices = false;
                unfiltered.scanner.whitelist.clear();
                unfiltered.scanner.blacklist.clear();
                unfiltered.scanner.discard_random = false;
                unfiltered.scanner.discard_rpa = false;
                unfiltered.scanner.dup_filter = false;
                unfiltered.scanner.phy_1m = true;
                unfiltered.scanner.phy_coded = true;
                if let Err(error) = configure_scanner(serial, &unfiltered) {
                    if let Err(restore) = configure_scanner(serial, config) { restore_failed = Some(restore); }
                    return Err(error);
                }
                discovery.start(seconds)?;
                log::info!("unfiltered discovery started for {seconds} seconds");
            },
            "discover-stop" => {
                if discovery.until.take().is_some() {
                    let serial = link.as_deref_mut().ok_or("serial link is unavailable")?;
                    if let Err(error) = configure_scanner(serial, config) {
                        restore_failed = Some(error.clone());
                        return Err(error);
                    }
                }
            },
            _ => return Err("unknown control action".into()),
        }
        Ok(discovery.snapshot(link.is_some()))
    })();
    web::reply(stream, result.unwrap_or_else(|error| serde_json::json!({"success":false,"error":error})));
    if let Some(error) = restore_failed { return Err(error); }
    Ok(())
}

#[cfg(test)]
mod cli_tests {
    use super::*;

    #[test]
    fn log_color_option_overrides_environment_and_validates_modes() {
        let args = arguments(&["--log-color", "always"]);
        assert_eq!(logging_color(&args, Some("never")).unwrap(), logger::ColorMode::Always);
        let args = arguments(&[]);
        assert_eq!(logging_color(&args, Some("never")).unwrap(), logger::ColorMode::Never);
        assert_eq!(logging_color(&args, None).unwrap(), logger::ColorMode::Auto);
        assert!(logging_color(&args, Some("typo")).is_err());
    }

    #[test]
    fn default_config_path_can_be_overridden() {
        assert_eq!(arguments(&[]).config, PathBuf::from(DEFAULT_CONFIG));
        assert_eq!(arguments(&["--config", "/tmp/private.yaml"]).config, PathBuf::from("/tmp/private.yaml"));
    }

    fn arguments(values: &[&str]) -> Args {
        parse_args_from(values.iter().map(|value| value.to_string()))
    }

    #[test]
    fn foreground_and_cli_diagnostics_override_yaml_and_environment() {
        let args = arguments(&["--foreground", "--log-level", "trace", "--trace-tx", "--trace-rx", "--no-trace-decode", "--trace-phy"]);
        assert!(args.log_stdout);
        let mut config = Config::default();
        config.log_level = "error".into();
        config.diagnostics.decode = true;
        config.diagnostics.phy = true;
        assert_eq!(logging_settings(&args, Some(&config), Some("warn")).unwrap(), (log::LevelFilter::Trace, true, true, false, true));
        let args = arguments(&[]);
        assert_eq!(logging_settings(&args, Some(&config), None).unwrap(), (log::LevelFilter::Error, false, false, true, true));
        assert!(!logging_settings(&arguments(&["--no-trace-phy"]), Some(&config), None).unwrap().4);
        assert_eq!(logging_settings(&args, Some(&config), Some("debug")).unwrap().0, log::LevelFilter::Debug);
        assert!(logging_settings(&arguments(&["--log-level", "wrong"]), None, None).is_err());
    }

    fn firmware_filter_session(config: &Config, steps: Vec<(Vec<u8>, u8)>) -> Result<bool, String> {
        use std::io::{Read, Write};
        use std::os::fd::FromRawFd;
        let mut master_fd = -1;
        let mut slave_fd = -1;
        assert_eq!(unsafe { libc::openpty(&mut master_fd, &mut slave_fd, std::ptr::null_mut(), std::ptr::null(), std::ptr::null()) }, 0);
        let mut master = unsafe { std::fs::File::from_raw_fd(master_fd) };
        let _slave = unsafe { std::fs::File::from_raw_fd(slave_fd) };
        let mut link = Link::open(&format!("/proc/self/fd/{slave_fd}"), 115200, false).unwrap();
        let firmware = std::thread::spawn(move || {
            for (mut expected, metadata) in steps {
                let command = expected[0];
                expected.extend_from_slice(&link::crc16_arc(&expected).to_le_bytes());
                let mut received = vec![0; expected.len()];
                let mut offset = 0;
                while offset < received.len() {
                    let mut poll = libc::pollfd { fd: master_fd, events: libc::POLLIN, revents: 0 };
                    assert_eq!(unsafe { libc::poll(&mut poll, 1, 3000) }, 1, "missing firmware command");
                    let count = master.read(&mut received[offset..]).unwrap();
                    assert_ne!(count, 0);
                    offset += count;
                }
                assert_eq!(received, expected);
                let mut response = vec![0, command, metadata, 0, 0xFF, 0, 0, 0, 0, 0, 0];
                response.extend_from_slice(&link::crc16_arc(&response).to_le_bytes());
                master.write_all(&response).unwrap();
            }
            let mut poll = libc::pollfd { fd: master_fd, events: libc::POLLIN, revents: 0 };
            assert_eq!(unsafe { libc::poll(&mut poll, 1, 150) }, 0, "unexpected firmware command after setup");
            master
        });
        let result = configure_scanner(&mut link, config);
        let _master = firmware.join().unwrap();
        result
    }

    #[test]
    fn firmware_filter_setup_is_ordered_and_fail_closed() {
        let mut config: Config = serde_yaml::from_str("devices:\n- {mac: AABBCCDDEEFF}\n- {mac: '112233445566', enabled: false}\n- {mac: AABBCC112233}\n").unwrap();
        let stop = vec![1, 0, 0, 0];
        let clear = vec![4];
        let first = vec![2, 0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA];
        let second = vec![2, 0x33, 0x22, 0x11, 0xCC, 0xBB, 0xAA];
        let scan = vec![1, 0x0B, 0x40, 0x01, 0x40, 0x00];
        let configured = vec![(stop.clone(), 0), (clear.clone(), 64), (first.clone(), 1), (second, 2), (scan.clone(), 0)];
        assert!(firmware_filter_session(&config, configured.clone()).unwrap());
        assert!(firmware_filter_session(&config, configured).unwrap());
        assert!(firmware_filter_session(&config, vec![(stop.clone(), 0), (clear.clone(), 64), (first, 0)]).is_err());
        assert!(firmware_filter_session(&config, vec![(stop.clone(), 0), (clear.clone(), 0)]).is_err());
        config.devices.iter_mut().for_each(|device| device.enabled = false);
        assert!(!firmware_filter_session(&config, vec![(stop.clone(), 0), (clear.clone(), 64)]).unwrap());
        config.scanner.filter_known_devices = false;
        assert!(firmware_filter_session(&config, vec![(stop.clone(), 0), (clear.clone(), 64), (scan.clone(), 0)]).unwrap());
        config.scanner.whitelist = vec!["AABBCC".into()];
        assert!(firmware_filter_session(&config, vec![(stop.clone(), 0), (clear.clone(), 64), (vec![2, 0xCC, 0xBB, 0xAA], 1), (scan.clone(), 0)]).unwrap());
        config.scanner.whitelist.clear();
        config.scanner.blacklist = vec!["AABBCC".into()];
        assert!(firmware_filter_session(&config, vec![(stop, 0), (clear, 64), (vec![3, 0xCC, 0xBB, 0xAA], 1), (scan, 0)]).unwrap());
    }
}
