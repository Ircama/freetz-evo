//! mDNS / DNS-SD advertisement of the Matter services (rs-matter `builtin`).
//!
//! FRITZ!OS runs AVM's own closed mDNS responder (`libavmdnsdomains.so`,
//! `libavmdnsnotify.so`, used by `ctlmgr`, `multid`, `upnpd`, `nqcs`, `dsld`,
//! `ddnsd`, `dect_manager`, `cloudmsgd`), which holds UDP 5353 for `fritz.box`
//! and for the services of the box. Two responders on the same host are fine as
//! long as both set `SO_REUSEADDR` and each of them answers only for its own
//! records: this module binds `[::]:5353` with `SO_REUSEADDR` and publishes
//! *only* the Matter services (`_matterc._udp`, `_matter._tcp` and their
//! `_services._dns-sd._udp` enumeration entries), never the box name.
//!
//! rs-matter's `builtin` backend is the only one that can run here: the `avahi`
//! and `resolve` backends need a D-Bus daemon (Avahi or systemd-resolved) that a
//! FRITZ!Box does not have, `zeroconf` and `astro-dnssd` target Windows and
//! macOS.
//!
//! Besides advertising, the responder built here is what feeds
//! `Transport::wait_mdns_resolve_request()`, so the controller can answer mDNS
//! resolve queries for the nodes it knows.
//!
//! mDNS is an *addition* to the local chain (Domoticz -> `127.0.0.1:5580` ->
//! `[::1]:5540`), never a requirement: every failure is logged and the daemon
//! keeps running.

use std::net::{Ipv4Addr, Ipv6Addr, UdpSocket};
use std::sync::Arc;
use std::time::{Duration, Instant};

use rs_matter::crypto::Crypto;
use rs_matter::error::{Error, ErrorCode};
use rs_matter::transport::network::mdns::builtin::{BuiltinMdns, Host};
use rs_matter::transport::network::mdns::{
    MDNS_IPV4_BROADCAST_ADDR, MDNS_IPV6_BROADCAST_ADDR, MDNS_SOCKET_DEFAULT_BIND_ADDR,
};
use rs_matter::Matter;
use socket2::{Domain, Protocol, Socket, Type};

/// Host name published as the mDNS SRV target (`<HOSTNAME>.local`).
///
/// Deliberately *not* the FRITZ!Box host name: `fritz.box` and its services
/// belong to the responder of FRITZ!OS, and a second claim on the same name
/// would produce conflicting answers on the LAN.
pub const HOSTNAME: &str = "matter-bridge";

/// Host name of the peer whose announcements are watched (the accessory).
pub const PEER_HOSTNAME: &str = "freetz-matter";

/// Called when the peer re-announces its Matter service on mDNS.
pub type PeerSeen = Arc<dyn Fn() + Send + Sync>;

/// Minimum interval between two announce-triggered callbacks.
const PEER_DEBOUNCE: Duration = Duration::from_secs(15);

/// An IPv6 address of a network interface, as reported by the kernel.
struct IfaceV6 {
    index: u32,
    name: String,
    ip: Ipv6Addr,
    scope: u8,
}

/// One entry per IPv6 address, parsed from `/proc/net/if_inet6`:
/// `addr ifindex prefixlen scope flags devname`, numeric fields in hex.
///
/// The kernel's text interface is used on purpose instead of `getifaddrs()`:
/// the FRITZ!Box runs uClibc, whose `struct ifaddrs` and `sockaddr` layouts do
/// not match the glibc definitions the `libc` crate ships, so crates that walk
/// those structures (like `if-addrs`) read garbage there.
fn proc_if_inet6() -> Vec<IfaceV6> {
    fn hex_word(bytes: &[u8]) -> Option<u16> {
        std::str::from_utf8(bytes)
            .ok()
            .and_then(|s| u16::from_str_radix(s, 16).ok())
    }

    let mut out = Vec::new();
    let Ok(text) = std::fs::read_to_string("/proc/net/if_inet6") else {
        return out;
    };
    for line in text.lines() {
        let f: Vec<&str> = line.split_whitespace().collect();
        if f.len() < 6 {
            continue;
        }
        let (Ok(index), Ok(scope)) = (
            u32::from_str_radix(f[1], 16),
            u8::from_str_radix(f[3], 16),
        ) else {
            continue;
        };
        let mut addr = [0u8; 16];
        for (i, chunk) in f[0].as_bytes().chunks(4).enumerate().take(8) {
            // Every group of four hex digits is one 16-bit word of the address.
            let Some(word) = hex_word(chunk) else { break };
            addr[2 * i] = (word >> 8) as u8;
            addr[2 * i + 1] = (word & 0xff) as u8;
        }
        out.push(IfaceV6 {
            index,
            name: f[5].to_string(),
            ip: Ipv6Addr::from(addr),
            scope,
        });
    }
    out
}

/// IPv4 address of an interface, through the `SIOCGIFADDR` ioctl.
///
/// The request buffer is built by hand (interface name + 24 bytes, the address
/// at offset 20) so that no C structure layout of the `libc` crate is involved.
fn iface_ipv4(name: &str) -> Option<Ipv4Addr> {
    let bytes = name.as_bytes();
    if bytes.is_empty() || bytes.len() >= 16 {
        return None;
    }

    let fd = unsafe { libc::socket(libc::AF_INET, libc::SOCK_DGRAM, 0) };
    if fd < 0 {
        return None;
    }

    let mut req = [0u8; 40];
    req[..bytes.len()].copy_from_slice(bytes);
    let ret = unsafe { libc::ioctl(fd, libc::SIOCGIFADDR, req.as_mut_ptr()) };
    unsafe { libc::close(fd) };

    (ret >= 0).then(|| Ipv4Addr::new(req[20], req[21], req[22], req[23]))
}

/// The LAN interface to advertise on: interface index, IPv4 address (when the
/// kernel reports one) and the IPv6 addresses configured on it.
///
/// Prefers an interface with a link-local IPv6 address (scope `0x20`) and, among
/// those, the one named `lan` (FRITZ!Box) or a bridge. `MATTER_MDNS_INTERFACE`
/// selects the interface by name when set.
fn lan_interface(preferred: Option<&str>) -> Option<(u32, Option<Ipv4Addr>, Vec<Ipv6Addr>)> {
    let addrs = proc_if_inet6();
    let mut candidates: Vec<(String, u32)> = Vec::new();

    for a in addrs.iter().filter(|a| a.scope == 0x20 && a.name != "lo") {
        if preferred.is_some_and(|want| want != a.name) {
            continue;
        }
        if candidates.iter().all(|(name, _)| *name != a.name) {
            candidates.push((a.name.clone(), a.index));
        }
    }

    let (name, index) = candidates
        .iter()
        .find(|(name, _)| name == "lan" || name.starts_with("br"))
        .or_else(|| candidates.first())
        .cloned()?;

    let mut ipv6_addrs: Vec<Ipv6Addr> = Vec::new();
    for a in addrs.iter().filter(|a| a.name == name) {
        if !a.ip.is_loopback() && !a.ip.is_unspecified() && !ipv6_addrs.contains(&a.ip) {
            ipv6_addrs.push(a.ip);
        }
    }

    Some((index, iface_ipv4(&name), ipv6_addrs))
}

/// Watches the mDNS traffic of the LAN in its own thread and calls `on_seen`
/// whenever `peer` announces its `_matter._tcp` service again.
///
/// A Matter node announces its operational service when it starts up, so an
/// announcement that arrives while our subscription to it is silent means that
/// the peer has restarted: the controller uses this to re-subscribe at once
/// instead of waiting for the periodic report to time out.
///
/// A dedicated thread with a blocking socket is used on purpose instead of a
/// task of the async executor: the socket is shared with the responder of
/// FRITZ!OS and a reader that is always ready must not be part of the executor
/// that also runs the Matter transport.
///
/// The socket is a passive listener: it shares UDP 5353 with the responder of
/// this node and with the one of FRITZ!OS (`SO_REUSEADDR`) and never answers.
pub fn spawn_peer_watch(peer: &'static str, on_seen: PeerSeen) {
    let result = std::thread::Builder::new()
        .name("mdns-watch".into())
        .spawn(move || {
            if let Err(error) = watch(peer, on_seen) {
                log::warn!(
                    "mDNS: cannot watch the announcements of {peer} ({error:?}); reconnects stay on the periodic path"
                );
            }
        });

    if result.is_err() {
        log::warn!("mDNS: cannot start the watch thread; reconnects stay on the periodic path");
    }
}

fn watch(peer: &'static str, on_seen: PeerSeen) -> Result<(), Error> {
    let (index, _, _) = lan_interface(std::env::var("MATTER_MDNS_INTERFACE").ok().as_deref())
        .ok_or(ErrorCode::NoNetworkInterface)?;

    let socket = Socket::new(Domain::IPV6, Type::DGRAM, Some(Protocol::UDP))
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .set_reuse_address(true)
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .set_only_v6(false)
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .bind(&MDNS_SOCKET_DEFAULT_BIND_ADDR.into())
        .map_err(|_| ErrorCode::StdIoError)?;

    let socket: UdpSocket = socket.into();
    socket
        .join_multicast_v6(&MDNS_IPV6_BROADCAST_ADDR, index)
        .map_err(|_| ErrorCode::StdIoError)?;

    log::info!("mDNS: watching {peer}._matter._tcp.local announcements on UDP 5353");

    let mut buffer = [0u8; 2048];
    let mut last_seen: Option<Instant> = None;
    loop {
        let len = socket.recv(&mut buffer[..]).map_err(|_| ErrorCode::StdIoError)?;
        let packet = &buffer[..len];
        let announces = packet
            .windows(peer.len())
            .any(|window| window == peer.as_bytes())
            && packet.windows(7).any(|window| window == b"_matter");
        if !announces {
            continue;
        }
        if last_seen.map_or(false, |seen: Instant| seen.elapsed() < PEER_DEBOUNCE) {
            continue;
        }
        last_seen = Some(Instant::now());
        log::info!("mDNS: {peer} announced its Matter service");
        on_seen();
    }
}

/// Advertises the Matter services of this node over mDNS/DNS-SD, sharing UDP
/// 5353 with the mDNS responder of FRITZ!OS.
pub async fn run<C: Crypto>(matter: &Matter<'_>, crypto: &C) -> Result<(), Error> {
    let (index, ipv4, ipv6_addrs) =
        lan_interface(std::env::var("MATTER_MDNS_INTERFACE").ok().as_deref())
            .ok_or(ErrorCode::NoNetworkInterface)?;

    let socket = Socket::new(Domain::IPV6, Type::DGRAM, Some(Protocol::UDP))
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .set_reuse_address(true)
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .set_only_v6(false)
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .bind(&MDNS_SOCKET_DEFAULT_BIND_ADDR.into())
        .map_err(|_| ErrorCode::StdIoError)?;

    let socket = async_io::Async::<UdpSocket>::new_nonblocking(socket.into())
        .map_err(|_| ErrorCode::StdIoError)?;

    socket
        .get_ref()
        .join_multicast_v6(&MDNS_IPV6_BROADCAST_ADDR, index)
        .map_err(|_| ErrorCode::StdIoError)?;
    if let Some(ip) = ipv4 {
        socket
            .get_ref()
            .join_multicast_v4(&MDNS_IPV4_BROADCAST_ADDR, &ip)
            .map_err(|_| ErrorCode::StdIoError)?;
    }

    log::info!(
        "mDNS: advertising on UDP 5353 as {HOSTNAME}.local (ifindex {index}, v4 {}, v6 {ipv6_addrs:?}), together with the responder of FRITZ!OS",
        ipv4.map_or_else(|| "none".to_string(), |ip| ip.to_string())
    );

    BuiltinMdns::new()
        .run(
            &socket,
            &socket,
            &Host {
                hostname: HOSTNAME,
                ip: ipv4.unwrap_or(Ipv4Addr::UNSPECIFIED),
                ipv6: &ipv6_addrs,
            },
            ipv4,
            Some(index),
            matter,
            crypto,
        )
        .await
}

/// [`run`] with the failure mode the daemon needs: mDNS is never required for
/// the local Domoticz <-> bridge <-> accessory chain, so a missing or busy mDNS
/// socket only disables the advertisement.
pub async fn run_or_wait<C: Crypto>(matter: &Matter<'_>, crypto: &C) -> Result<(), Error> {
    match run(matter, crypto).await {
        Ok(()) => Ok(()),
        Err(e) => {
            log::warn!(
                "mDNS advertisement unavailable ({e:?}); the Matter services stay reachable by address"
            );
            core::future::pending::<Result<(), Error>>().await
        }
    }
}
