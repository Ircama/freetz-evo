//! Matter DNS-SD (commissionable/operational service) publishing.
//!
//! `builtin` is the rs-matter responder on a dedicated multicast socket and
//! needs no system service; the other backends delegate to a system daemon
//! and are compiled in only with their Cargo feature (see Cargo.toml).

use crate::config::{MatterConfig, MdnsBackend};
use rs_matter::crypto::Crypto;
use rs_matter::error::{Error, ErrorCode};
use rs_matter::transport::network::mdns::builtin::{BuiltinMdns, Host};
use rs_matter::transport::network::mdns::{
    MDNS_IPV4_BROADCAST_ADDR, MDNS_IPV6_BROADCAST_ADDR, MDNS_SOCKET_DEFAULT_BIND_ADDR,
};
use rs_matter::Matter;
use socket2::{Domain, Protocol, Socket, Type};
use std::net::{Ipv4Addr, Ipv6Addr, UdpSocket};

fn mdns_socket(index: u32, ipv4: Option<Ipv4Addr>) -> Result<UdpSocket, Error> {
    let socket = Socket::new(Domain::IPV6, Type::DGRAM, Some(Protocol::UDP))
        .map_err(|_| ErrorCode::StdIoError)?;
    socket.set_reuse_address(true).map_err(|_| ErrorCode::StdIoError)?;
    socket.set_only_v6(false).map_err(|_| ErrorCode::StdIoError)?;
    socket.set_unicast_hops_v6(255).map_err(|_| ErrorCode::StdIoError)?;
    socket.set_multicast_hops_v6(255).map_err(|_| ErrorCode::StdIoError)?;
    socket.set_multicast_if_v6(index).map_err(|_| ErrorCode::StdIoError)?;
    socket.set_ttl_v4(255).map_err(|_| ErrorCode::StdIoError)?;
    socket.set_multicast_ttl_v4(255).map_err(|_| ErrorCode::StdIoError)?;
    if let Some(address) = ipv4 {
        socket.set_multicast_if_v4(&address).map_err(|_| ErrorCode::StdIoError)?;
    }
    Ok(socket.into())
}

/// Interfaces carrying a default route (IPv4 then IPv6), in table order.
fn default_route_interfaces() -> Vec<String> {
    let mut names = Vec::new();
    if let Ok(text) = std::fs::read_to_string("/proc/net/route") {
        for line in text.lines().skip(1) {
            let fields: Vec<_> = line.split_whitespace().collect();
            if fields.len() > 7 && fields[1] == "00000000" && fields[7] == "00000000" && !names.iter().any(|name| name == fields[0]) {
                names.push(fields[0].to_string());
            }
        }
    }
    if let Ok(text) = std::fs::read_to_string("/proc/net/ipv6_route") {
        for line in text.lines() {
            let fields: Vec<_> = line.split_whitespace().collect();
            if fields.len() == 10 && fields[0] == "0".repeat(32) && fields[1] == "00" && fields[9] != "lo" && !names.iter().any(|name| name == fields[9]) {
                names.push(fields[9].to_string());
            }
        }
    }
    names
}

/// Automatic interface preference (lower is better). The Freetz profile keeps
/// the FRITZ!Box LAN bridge first; the standalone build prefers the interface
/// of the default route and avoids container/VPN interfaces.
fn rank(name: &str, default_routes: &[String]) -> usize {
    if crate::profile::FREETZ {
        return if name == "lan" { 0 } else if name.starts_with("br") { 1 } else { 2 };
    }
    if let Some(position) = default_routes.iter().position(|route| route == name) {
        return position;
    }
    const VIRTUAL: [&str; 12] = ["docker", "veth", "virbr", "br-", "tun", "tap", "wg", "zt", "tailscale", "vmnet", "vboxnet", "lxc"];
    default_routes.len() + if VIRTUAL.iter().any(|prefix| name.starts_with(prefix)) { 1 } else { 0 }
}

fn interface(preferred: &str) -> Result<(u32, Option<Ipv4Addr>, Vec<Ipv6Addr>), Error> {
    let routes = default_route_interfaces();
    let text =
        std::fs::read_to_string("/proc/net/if_inet6").map_err(|_| ErrorCode::NoNetworkInterface)?;
    let mut addresses = Vec::new();
    for line in text.lines() {
        let fields: Vec<_> = line.split_whitespace().collect();
        if fields.len() != 6 || fields[0].len() != 32 || !fields[0].is_ascii() {
            continue;
        }
        let index =
            u32::from_str_radix(fields[1], 16).map_err(|_| ErrorCode::NoNetworkInterface)?;
        let mut bytes = [0; 16];
        for (position, byte) in bytes.iter_mut().enumerate() {
            *byte = u8::from_str_radix(&fields[0][position * 2..position * 2 + 2], 16)
                .map_err(|_| ErrorCode::NoNetworkInterface)?;
        }
        addresses.push((
            fields[5].to_string(),
            index,
            Ipv6Addr::from(bytes),
            fields[3] == "20",
        ));
    }
    let selected = addresses
        .iter()
        .filter(|(name, _, _, local)| {
            *local && name != "lo" && (preferred.is_empty() || name == preferred)
        })
        .min_by_key(|(name, _, _, _)| rank(name, &routes))
        .ok_or(ErrorCode::NoNetworkInterface)?;
    let name = &selected.0;
    let mut ipv6: Vec<Ipv6Addr> = Vec::new();
    for (candidate, _, address, _) in &addresses {
        // AVM kernels may list the same address more than once.
        if candidate == name && !address.is_loopback() && !ipv6.contains(address) {
            ipv6.push(*address);
        }
    }
    let mut request = [0u8; 40];
    if name.len() >= 16 {
        return Err(ErrorCode::NoNetworkInterface.into());
    }
    request[..name.len()].copy_from_slice(name.as_bytes());
    let descriptor = unsafe { libc::socket(libc::AF_INET, libc::SOCK_DGRAM, 0) };
    let ipv4 = if descriptor >= 0 {
        let result = unsafe { libc::ioctl(descriptor, libc::SIOCGIFADDR, request.as_mut_ptr()) };
        unsafe { libc::close(descriptor) };
        (result >= 0).then(|| Ipv4Addr::new(request[20], request[21], request[22], request[23]))
    } else {
        None
    };
    Ok((selected.1, ipv4, ipv6))
}

#[cfg(any(feature = "mdns-avahi", feature = "mdns-resolved"))]
async fn bus_name_has_owner(connection: &rs_matter::utils::zbus::Connection, name: &str) -> bool {
    use rs_matter::utils::zbus::{fdo::DBusProxy, names::BusName};
    let Ok(proxy) = DBusProxy::new(connection).await else { return false };
    let Ok(name) = BusName::try_from(name) else { return false };
    proxy.name_has_owner(name).await.unwrap_or(false)
}

/// `auto`: the first compiled system backend whose daemon is reachable and
/// that did not fail before in this process, otherwise builtin.
async fn select_auto(demoted: &[MdnsBackend]) -> MdnsBackend {
    let usable = |backend: MdnsBackend| backend.compiled() && !demoted.contains(&backend);
    #[cfg(any(feature = "mdns-avahi", feature = "mdns-resolved"))]
    if usable(MdnsBackend::Avahi) || usable(MdnsBackend::Resolved) {
        if let Ok(connection) = rs_matter::utils::zbus::Connection::system().await {
            for (backend, owner) in [(MdnsBackend::Avahi, "org.freedesktop.Avahi"), (MdnsBackend::Resolved, "org.freedesktop.resolve1")] {
                if usable(backend) && bus_name_has_owner(&connection, owner).await {
                    return backend;
                }
            }
        }
    }
    [MdnsBackend::Zeroconf, MdnsBackend::Astro]
        .into_iter()
        .find(|backend| usable(*backend))
        .unwrap_or(MdnsBackend::Builtin)
}

/// Publish until an error occurs. In `auto` mode a failing system backend is
/// demoted, so the caller's next retry moves on (ultimately to builtin).
pub async fn run<C: Crypto>(
    matter: &Matter<'_>,
    crypto: &C,
    config: &MatterConfig,
    demoted: &mut Vec<MdnsBackend>,
) -> Result<(), Error> {
    let configured = config.effective_mdns_backend();
    let backend = match configured {
        MdnsBackend::Auto => select_auto(demoted).await,
        backend => backend,
    };
    log::info!("Matter DNS-SD backend: {} (configured: {})", backend.name(), configured.name());
    let result = match backend {
        MdnsBackend::Disabled => core::future::pending().await,
        MdnsBackend::Builtin => run_builtin(matter, crypto, &config.mdns_interface, &config.effective_mdns_hostname()).await,
        #[cfg(feature = "mdns-avahi")]
        MdnsBackend::Avahi => {
            let connection = rs_matter::utils::zbus::Connection::system().await?;
            rs_matter::transport::network::mdns::avahi::AvahiMdns::new(connection).run(matter).await
        }
        #[cfg(feature = "mdns-resolved")]
        MdnsBackend::Resolved => {
            let connection = rs_matter::utils::zbus::Connection::system().await?;
            rs_matter::transport::network::mdns::resolve::ResolveMdns::new(connection).run(matter).await
        }
        #[cfg(feature = "mdns-zeroconf")]
        MdnsBackend::Zeroconf => rs_matter::transport::network::mdns::zeroconf::ZeroconfMdns::new().run(matter).await,
        #[cfg(feature = "mdns-astro")]
        MdnsBackend::Astro => rs_matter::transport::network::mdns::astro::AstroMdns::new().run(matter).await,
        #[allow(unreachable_patterns)]
        _ => Err(ErrorCode::InvalidState.into()),
    };
    if result.is_err() && configured == MdnsBackend::Auto && backend != MdnsBackend::Builtin {
        log::warn!("Matter DNS-SD backend {} failed; auto mode falls back", backend.name());
        demoted.push(backend);
    }
    result
}

async fn run_builtin<C: Crypto>(matter: &Matter<'_>, crypto: &C, preferred: &str, hostname: &str) -> Result<(), Error> {
    let (index, ipv4, ipv6) = interface(preferred)?;
    let socket = Socket::from(mdns_socket(index, ipv4)?);
    socket
        .bind(&MDNS_SOCKET_DEFAULT_BIND_ADDR.into())
        .map_err(|_| ErrorCode::StdIoError)?;
    let socket = async_io::Async::<UdpSocket>::new_nonblocking(socket.into())
        .map_err(|_| ErrorCode::StdIoError)?;
    socket
        .get_ref()
        .join_multicast_v6(&MDNS_IPV6_BROADCAST_ADDR, index)
        .map_err(|_| ErrorCode::StdIoError)?;
    if let Some(address) = ipv4 {
        socket
            .get_ref()
            .join_multicast_v4(&MDNS_IPV4_BROADCAST_ADDR, &address)
            .map_err(|_| ErrorCode::StdIoError)?;
    }
    log::info!("Matter mDNS advertising {hostname}.local on interface {index}, IPv4={ipv4:?}, IPv6={ipv6:?}");
    BuiltinMdns::new()
        .run(
            &socket,
            &socket,
            &Host {
                hostname,
                ip: ipv4.unwrap_or(Ipv4Addr::UNSPECIFIED),
                ipv6: &ipv6,
            },
            ipv4,
            Some(index),
            matter,
            crypto,
        )
        .await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn automatic_interface_rank_follows_the_build_profile() {
        let routes = vec!["eth0".to_string(), "wlan0".to_string()];
        if crate::profile::FREETZ {
            assert!(rank("lan", &routes) < rank("br0", &routes));
            assert!(rank("br0", &routes) < rank("eth0", &routes));
        } else {
            assert!(rank("eth0", &routes) < rank("wlan0", &routes));
            assert!(rank("wlan0", &routes) < rank("enp3s0", &routes));
            assert!(rank("enp3s0", &routes) < rank("docker0", &routes));
            assert!(rank("br0", &routes) < rank("br-1a2b3c", &routes));
        }
    }

    #[test]
    fn auto_without_reachable_system_backend_uses_builtin() {
        let all = MdnsBackend::ALL.to_vec();
        assert_eq!(futures_lite::future::block_on(select_auto(&all)), MdnsBackend::Builtin);
    }

    #[test]
    fn mdns_uses_255_hops_and_explicit_outgoing_interfaces() {
        let index = unsafe { libc::if_nametoindex(c"lo".as_ptr()) };
        assert_ne!(index, 0);
        let socket = Socket::from(mdns_socket(index, Some(Ipv4Addr::LOCALHOST)).unwrap());
        assert_eq!(socket.unicast_hops_v6().unwrap(), 255);
        assert_eq!(socket.multicast_hops_v6().unwrap(), 255);
        assert_eq!(socket.multicast_if_v6().unwrap(), index);
        assert_eq!(socket.ttl_v4().unwrap(), 255);
        assert_eq!(socket.multicast_ttl_v4().unwrap(), 255);
        assert_eq!(socket.multicast_if_v4().unwrap(), Ipv4Addr::LOCALHOST);
    }
}
