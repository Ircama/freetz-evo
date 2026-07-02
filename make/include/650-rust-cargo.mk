### Rust/Cargo macros
#
# All packages using these macros MUST set a private CARGO_HOME (and HOME),
# e.g.: PKG_CARGO_HOME:=$(abspath $(PKG_DIR)/.cargo) + export HOME / CARGO_HOME.
# Otherwise they share ~/.cargo/registry/src/ and overwrite each other's patches.

# Expand to the rustix crate directory glob in Cargo registry.
# $1: rustix crate version (for example: 1.1.3)
define RUSTIX_REGISTRY_DIR_GLOB__INT
$$HOME/.cargo/registry/src/*/rustix-$(1)
endef

# Apply patch commands identical across rustix layouts.
# Note: the HWPOISON substitution is guarded to be idempotent — it only runs
# when the file has NOT already been patched (no linux_raw_sys::general::EHWPOISON
# reference in errno.rs). Without this guard, repeated application (from multiple
# packages sharing the same rustix version) creates duplicate HWPOISON definitions.
define RUSTIX_APPLY_COMMON_UCLIBC_PATCHES__INT
	perl -0pi -e 's/c::getpriority\(c::PRIO_USER, uid\.as_raw\(\) as _\)/c::getpriority(c::PRIO_USER as _, uid.as_raw() as _)/g; s/c::getpriority\(c::PRIO_PGRP, Pid::as_raw\(pgid\) as _\)/c::getpriority(c::PRIO_PGRP as _, Pid::as_raw(pgid) as _)/g; s/c::getpriority\(c::PRIO_PROCESS, Pid::as_raw\(pid\) as _\)/c::getpriority(c::PRIO_PROCESS as _, Pid::as_raw(pid) as _)/g; s/c::setpriority\(c::PRIO_USER, uid\.as_raw\(\) as _, priority\)/c::setpriority(c::PRIO_USER as _, uid.as_raw() as _, priority)/g; s/c::PRIO_PGRP,/c::PRIO_PGRP as _,/; s/c::PRIO_PROCESS,/c::PRIO_PROCESS as _,/;' "$$rustix_dir/src/backend/libc/process/syscalls.rs"; \
	perl -0pi -e 's/const CRDLY = c::CRDLY;/const CRDLY = c::CRDLY as c::tcflag_t;/; s/const FFDLY = c::FFDLY;/const FFDLY = c::FFDLY as c::tcflag_t;/; s/const VTDLY = c::VTDLY;/const VTDLY = c::VTDLY as c::tcflag_t;/; s/const CMSPAR = c::CMSPAR;/const CMSPAR = c::CMSPAR as c::tcflag_t;/;' "$$rustix_dir/src/termios/types.rs"; \
	if ! grep -q 'linux_raw_sys::general::EHWPOISON' "$$rustix_dir/src/backend/libc/io/errno.rs" 2>/dev/null; then \
		perl -0pi -e 's/pub const HWPOISON: Self = Self\(c::EHWPOISON\);/#[cfg(not(target_env = "uclibc"))]\n    pub const HWPOISON: Self = Self(c::EHWPOISON);\n    #[cfg(target_env = "uclibc")]\n    pub const HWPOISON: Self = Self(linux_raw_sys::general::EHWPOISON as _);/' "$$rustix_dir/src/backend/libc/io/errno.rs"; \
	fi
endef

# Apply shared rustix uClibc compatibility fixes for 1.1.x crate layout.
# $1: rustix crate version (for example: 1.1.3)
define RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT
for rustix_dir in $(call RUSTIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$rustix_dir" ] || continue; \
	chmod -R u+w "$$rustix_dir"; \
	if ! grep -q 'Freetz uClibc fallbacks' "$$rustix_dir/src/backend/libc/c.rs"; then \
		perl -0pi -e 's@\#\[cfg\(all\(linux_raw_dep, feature = "termios"\)\)\]\npub\(crate\) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;@#[cfg(all(linux_raw_dep, feature = "termios"))]\npub(crate) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;\n\n// Freetz uClibc fallbacks for symbols missing from libc on MIPS.\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const STATX__RESERVED: u32 = linux_raw_sys::general::STATX__RESERVED;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_NOEXEC_SEAL: c_uint = linux_raw_sys::general::MFD_NOEXEC_SEAL as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_EXEC: c_uint = linux_raw_sys::general::MFD_EXEC as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_64KB: c_uint = linux_raw_sys::general::MFD_HUGE_64KB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512KB: c_uint = linux_raw_sys::general::MFD_HUGE_512KB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1MB: c_uint = linux_raw_sys::general::MFD_HUGE_1MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2MB: c_uint = linux_raw_sys::general::MFD_HUGE_2MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_8MB: c_uint = linux_raw_sys::general::MFD_HUGE_8MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16MB: c_uint = linux_raw_sys::general::MFD_HUGE_16MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_32MB: c_uint = linux_raw_sys::general::MFD_HUGE_32MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_256MB: c_uint = linux_raw_sys::general::MFD_HUGE_256MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512MB: c_uint = linux_raw_sys::general::MFD_HUGE_512MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1GB: c_uint = linux_raw_sys::general::MFD_HUGE_1GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2GB: c_uint = linux_raw_sys::general::MFD_HUGE_2GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16GB: c_uint = linux_raw_sys::general::MFD_HUGE_16GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) type __fsword_t = linux_raw_sys::general::__fsword_t;\n#[cfg(all(linux_raw_dep, target_env = "uclibc"))]\npub(crate) const EHWPOISON: c_int = linux_raw_sys::general::EHWPOISON as _;\n#[cfg(all(linux_raw_dep, feature = "net", target_env = "uclibc"))]\npub(crate) const AF_XDP: c_int = linux_raw_sys::net::AF_XDP as _;\n#[cfg(all(linux_raw_dep, feature = "net", target_env = "uclibc"))]\npub(crate) const IP_PMTUDISC_INTERFACE: c_int = linux_raw_sys::net::IP_PMTUDISC_INTERFACE as _;\n#[cfg(all(linux_raw_dep, feature = "net", target_env = "uclibc"))]\npub(crate) const IP_PMTUDISC_OMIT: c_int = linux_raw_sys::net::IP_PMTUDISC_OMIT as _;\n#[cfg(all(linux_raw_dep, feature = "termios", target_env = "uclibc"))]\npub(crate) const CMSPAR: tcflag_t = linux_raw_sys::general::CMSPAR as _;@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	fi; \
	perl -0pi -e 's@\#\[cfg\(any\(target_os = "linux", target_os = "hurd", target_os = "emscripten"\)\)\]\npub\(super\) use \{preadv64 as preadv, pwritev64 as pwritev\};@#[cfg(all(target_os = "linux", target_env = "uclibc"))]\npub(super) use {preadv, pwritev};\n#[cfg(any(\n    target_os = "hurd",\n    target_os = "emscripten",\n    all(target_os = "linux", not(target_env = "uclibc"))\n))]\npub(super) use {preadv64 as preadv, pwritev64 as pwritev};@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	perl -0pi -e 's/(?:c::AT_MINSIGSTKSZ|linux_raw_sys::general::AT_MINSIGSTKSZ)/51/g' "$$rustix_dir/src/backend/libc/param/auxv.rs"; \
	perl -0pi -e 's/const MOVE = c::SPLICE_F_MOVE;/const MOVE = linux_raw_sys::general::SPLICE_F_MOVE as _;/; s/const NONBLOCK = c::SPLICE_F_NONBLOCK;/const NONBLOCK = linux_raw_sys::general::SPLICE_F_NONBLOCK as _;/; s/const MORE = c::SPLICE_F_MORE;/const MORE = linux_raw_sys::general::SPLICE_F_MORE as _;/; s/const GIFT = c::SPLICE_F_GIFT;/const GIFT = linux_raw_sys::general::SPLICE_F_GIFT as _;/' "$$rustix_dir/src/backend/libc/pipe/types.rs"; \
	perl -0pi -e 's/const NONBLOCK = backend::c::PIDFD_NONBLOCK;/const NONBLOCK = backend::c::PIDFD_NONBLOCK as ffi::c_uint;/' "$$rustix_dir/src/process/pidfd.rs"; \
	$(call RUSTIX_APPLY_COMMON_UCLIBC_PATCHES__INT) \
done;
endef

# Apply shared rustix uClibc compatibility fixes for 0.38.x crate layout.
# $1: rustix crate version (for example: 0.38.37)
define RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT
for rustix_dir in $(call RUSTIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$rustix_dir" ] || continue; \
	chmod -R u+w "$$rustix_dir"; \
	if ! grep -q 'Freetz uClibc fallbacks' "$$rustix_dir/src/backend/libc/c.rs"; then \
		perl -0pi -e 's@\#\[cfg\(all\(linux_kernel, feature = "termios"\)\)\]\npub\(crate\) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;@#[cfg(all(linux_kernel, feature = "termios"))]\npub(crate) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;\n\n// Freetz uClibc fallbacks for symbols missing from libc on MIPS.\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const STATX__RESERVED: u32 = linux_raw_sys::general::STATX__RESERVED;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_NOEXEC_SEAL: c_uint = linux_raw_sys::general::MFD_NOEXEC_SEAL as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_EXEC: c_uint = linux_raw_sys::general::MFD_EXEC as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_64KB: c_uint = linux_raw_sys::general::MFD_HUGE_64KB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512KB: c_uint = linux_raw_sys::general::MFD_HUGE_512KB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1MB: c_uint = linux_raw_sys::general::MFD_HUGE_1MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2MB: c_uint = linux_raw_sys::general::MFD_HUGE_2MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_8MB: c_uint = linux_raw_sys::general::MFD_HUGE_8MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16MB: c_uint = linux_raw_sys::general::MFD_HUGE_16MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_32MB: c_uint = linux_raw_sys::general::MFD_HUGE_32MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_256MB: c_uint = linux_raw_sys::general::MFD_HUGE_256MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512MB: c_uint = linux_raw_sys::general::MFD_HUGE_512MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1GB: c_uint = linux_raw_sys::general::MFD_HUGE_1GB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2GB: c_uint = linux_raw_sys::general::MFD_HUGE_2GB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16GB: c_uint = linux_raw_sys::general::MFD_HUGE_16GB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) type __fsword_t = linux_raw_sys::general::__fsword_t;\n#[cfg(all(linux_kernel, target_env = "uclibc"))]\npub(crate) const EHWPOISON: c_int = linux_raw_sys::general::EHWPOISON as _;\n#[cfg(all(linux_kernel, feature = "net", target_env = "uclibc"))]\npub(crate) const AF_XDP: c_int = linux_raw_sys::net::AF_XDP as _;\n#[cfg(all(linux_kernel, feature = "termios", target_env = "uclibc"))]\npub(crate) const CMSPAR: tcflag_t = linux_raw_sys::general::CMSPAR as _;@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	fi; \
	perl -0pi -e 's@\#\[cfg\(any\(target_os = "linux", target_os = "hurd", target_os = "emscripten"\)\)\]\npub\(super\) use (?:libc::)?\{preadv64 as preadv, pwritev64 as pwritev\};@#[cfg(all(target_os = "linux", target_env = "uclibc"))]\npub(super) use libc::{preadv, pwritev};\n#[cfg(any(target_os = "hurd", target_os = "emscripten", all(target_os = "linux", not(target_env = "uclibc"))))]\npub(super) use libc::{preadv64 as preadv, pwritev64 as pwritev};@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	perl -0pi -e 's/const NONBLOCK = backend::c::PIDFD_NONBLOCK;/const NONBLOCK = backend::c::PIDFD_NONBLOCK as backend::c::c_uint;/' "$$rustix_dir/src/process/pidfd.rs"; \
	$(call RUSTIX_APPLY_COMMON_UCLIBC_PATCHES__INT) \
done;
endef

# Apply rustix uClibc/MIPS compatibility fixes via cargo [patch.crates-io].
# This uses CARGO_HOME to locate the registry source, copies it to a patched
# directory, applies all fixes, and writes a cargo patch snippet so the build
# uses the patched copy instead of the registry original (avoids read-only
# registry file issues).
# $1: rustix crate version (for example: 1.1.2)
# Requires: CARGO_HOME exported to the shell, $$CARGO_HOME/config.toml writable
define RUSTIX_APPLY_UCLIBC_PATCHES_VIA_PATCH__INT
	rustix_src="$$(find "$$CARGO_HOME/registry/src" -type d -name 'rustix-$(1)' 2>/dev/null | head -1)"; \
	if [ -n "$$rustix_src" ]; then \
		if [ ! -d "$$CARGO_HOME/rustix-$(1)-patched" ]; then \
			cp -a "$$rustix_src" "$$CARGO_HOME/rustix-$(1)-patched"; \
			chmod -R u+w "$$CARGO_HOME/rustix-$(1)-patched"; \
			perl -i -pe 's/use \{preadv64 as preadv, pwritev64 as pwritev\}/use {preadv, pwritev}/' "$$CARGO_HOME/rustix-$(1)-patched/src/backend/libc/c.rs"; \
			perl -i -pe 's/pub const HWPOISON: Self = Self\(c::EHWPOISON\);/pub const HWPOISON: Self = Self(linux_raw_sys::general::EHWPOISON as _);/' "$$CARGO_HOME/rustix-$(1)-patched/src/backend/libc/io/errno.rs"; \
			perl -i -pe 's/const CMSPAR = c::CMSPAR;/const CMSPAR = linux_raw_sys::general::CMSPAR as c::tcflag_t;/; s/const CRDLY = c::CRDLY;/const CRDLY = c::CRDLY as c::tcflag_t;/; s/const FFDLY = c::FFDLY;/const FFDLY = c::FFDLY as c::tcflag_t;/; s/const VTDLY = c::VTDLY;/const VTDLY = c::VTDLY as c::tcflag_t;/' "$$CARGO_HOME/rustix-$(1)-patched/src/termios/types.rs"; \
		fi; \
		printf '\n[patch.crates-io]\nrustix = { path = "%s" }\n' \
			"$$CARGO_HOME/rustix-$(1)-patched" >> "$$CARGO_HOME/config.toml"; \
	fi
endef

# Expand to the nix crate directory glob in Cargo registry.
# $1: nix crate version (for example: 0.30.1)
define NIX_REGISTRY_DIR_GLOB__INT
$$HOME/.cargo/registry/src/*/nix-$(1)
endef

# Apply libc_bitflags cast fix in nix macros.rs.
# $1: nix crate version (for example: 0.30.1)
define NIX_APPLY_LIBC_BITFLAGS_CAST_PATCH__INT
for nix_dir in $(call NIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$nix_dir" ] || continue; \
	perl -0pi -e 's%const \$$Flag = libc::\$$Flag \$$\(as \$$cast\)\*;%const \$$Flag = libc::\$$Flag as \$$T \$$\(as \$$cast\)*;%' "$$nix_dir/src/macros.rs"; \
done;
endef

# Apply nix 0.22.x uClibc/MIPS compatibility fixes.
# This disables Linux code paths requiring libc symbols missing on uClibc
# and normalizes signatures for uClibc's libc declarations.
# $1: nix crate version (for example: 0.22.1)
define NIX_APPLY_UCLIBC_MIPS_PATCHES_022__INT
for nix_dir in $(call NIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$nix_dir" ] || continue; \
	perl -0pi -e 's/#\[cfg\(any\(target_os = "dragonfly",\n          target_os = "freebsd",\n          target_os = "ios",\n          target_os = "linux",\n          target_os = "macos",\n          target_os = "netbsd"\)\)\]\npub mod aio;/#[cfg(any(target_os = "dragonfly",\n          target_os = "freebsd",\n          target_os = "ios",\n          target_os = "macos",\n          target_os = "netbsd",\n          all(target_os = "linux", not(target_env = "uclibc"))))]\npub mod aio;/s; s/#\[cfg\(target_os = "linux"\)\]\npub mod personality;/#[cfg(all(target_os = "linux", not(target_env = "uclibc")))]\npub mod personality;/g; s/#\[cfg\(any\(target_os = "android",\n          target_os = "dragonfly",\n          target_os = "freebsd",\n          target_os = "linux",\n          target_os = "macos",\n          target_os = "netbsd",\n          target_os = "openbsd"\)\)\]\npub mod ptrace;/#[cfg(any(target_os = "android",\n          target_os = "dragonfly",\n          target_os = "freebsd",\n          all(target_os = "linux", not(target_env = "uclibc")),\n          target_os = "macos",\n          target_os = "netbsd",\n          target_os = "openbsd"))]\npub mod ptrace;/s; s/#\[cfg\(any\(target_os = "android",\n          target_os = "dragonfly",\n          target_os = "freebsd",\n          target_os = "ios",\n          target_os = "linux",\n          target_os = "macos",\n          target_os = "openbsd"\n\)\)\]\npub mod statfs;/#[cfg(any(target_os = "android",\n          target_os = "dragonfly",\n          target_os = "freebsd",\n          target_os = "ios",\n          all(target_os = "linux", not(target_env = "uclibc")),\n          target_os = "macos",\n          target_os = "openbsd"\n))]\npub mod statfs;/s' "$$nix_dir/src/sys/mod.rs"; \
	perl -0pi -e 's/#\[cfg\(target_os = "linux"\)\]\n    Ib = libc::AF_IB,/#\[cfg(all(target_os = "linux", not(target_env = "uclibc")))]\n    Ib = libc::AF_IB,/g; s/#\[cfg\(target_os = "linux"\)\]\n    Mpls = libc::AF_MPLS,/#\[cfg(all(target_os = "linux", not(target_env = "uclibc")))]\n    Mpls = libc::AF_MPLS,/g' "$$nix_dir/src/sys/socket/addr.rs"; \
	perl -0pi -e 's/libc::pwritev\(fd, iov\.as_ptr\(\) as \*const libc::iovec, iov\.len\(\) as c_int, offset\)/libc::pwritev(fd, iov.as_ptr() as *const libc::iovec, iov.len() as c_int, offset as i64)/g; s/libc::preadv\(fd, iov\.as_ptr\(\) as \*const libc::iovec, iov\.len\(\) as c_int, offset\)/libc::preadv(fd, iov.as_ptr() as *const libc::iovec, iov.len() as c_int, offset as i64)/g; s/#\[cfg\(target_os = "linux"\)\]\npub fn process_vm_writev\(/#[cfg(all(target_os = "linux", not(target_env = "uclibc")))]\npub fn process_vm_writev(/g; s/#\[cfg\(any\(target_os = "linux"\)\)\]\npub fn process_vm_readv\(/#[cfg(all(target_os = "linux", not(target_env = "uclibc")))]\npub fn process_vm_readv(/g' "$$nix_dir/src/sys/uio.rs"; \
	perl -0pi -e 's/#\[cfg\(not\(target_os = "redox"\)\)\]\ntype SaFlags_t = libc::c_int;/#[cfg(all(not(target_os = "redox"), target_env = "uclibc"))]\ntype SaFlags_t = libc::c_uint;\n#[cfg(all(not(target_os = "redox"), not(target_env = "uclibc")))]\ntype SaFlags_t = libc::c_int;/s' "$$nix_dir/src/sys/signal.rs"; \
	perl -0pi -e 's|(                #\[cfg\(any\(all\(target_os = "linux", target_env = "musl"\), target_arch = "mips"\)\)\]\n                SigevNotify::SigevThreadId\{\.\.\} => 4  // No SIGEV_THREAD_ID defined)|                #[cfg(all(target_os = "linux", target_env = "uclibc"))]\n                SigevNotify::SigevThreadId{..} => libc::SIGEV_THREAD_ID,\n$$1|' "$$nix_dir/src/sys/signal.rs"; \
done; \
$(call NIX_APPLY_LIBC_BITFLAGS_CAST_PATCH__INT,$(1))
endef

# Apply nix 0.26.x uClibc/MIPS compatibility fixes with shell-safe regexes.
# This disables Linux code paths requiring libc symbols missing on uClibc
# and normalizes libc_bitflags typing on uClibc.
# $1: nix crate version (for example: 0.26.4)
define NIX_APPLY_UCLIBC_MIPS_PATCHES_026_SAFE__INT
for nix_dir in $(call NIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$nix_dir" ] || continue; \
	perl -0pi -e 's/#\[cfg\(any\(target_os = "android", target_os = "linux"\)\)\]\n#\[cfg\(feature = "zerocopy"\)\]\nlibc_bitflags! \{/#[cfg(any(target_os = "android", all(target_os = "linux", not(target_env = "uclibc"))))]\n#[cfg(feature = "zerocopy")]\nlibc_bitflags! {/g; s/#\[cfg\(any\(target_os = "linux", target_os = "android"\)\)\]\npub fn splice\(/#[cfg(any(target_os = "android", all(target_os = "linux", not(target_env = "uclibc"))))]\npub fn splice(/g; s/#\[cfg\(any\(target_os = "linux", target_os = "android"\)\)\]\npub fn tee\(/#[cfg(any(target_os = "android", all(target_os = "linux", not(target_env = "uclibc"))))]\npub fn tee(/g; s/#\[cfg\(any\(target_os = "linux", target_os = "android"\)\)\]\npub fn vmsplice\(/#[cfg(any(target_os = "android", all(target_os = "linux", not(target_env = "uclibc"))))]\npub fn vmsplice(/g' "$$nix_dir/src/fcntl.rs"; \
	perl -0pi -e 's/#\[cfg\(any\(target_os = "android", target_os = "freebsd", target_os = "linux"\)\)\](?=\n#\[cfg\(feature = "net"\)\]\nsockopt_impl!\(\n    #\[cfg_attr\(docsrs, doc\(cfg\(feature = "net"\)\)\)\]\n    \/\/\/ The `recvmsg\(2\)` call will return the destination IP address for a UDP\n    \/\/\/ datagram\.\n    Ipv6OrigDstAddr,)/#[cfg(any(target_os = "android", target_os = "freebsd", all(target_os = "linux", not(target_env = "uclibc"))))]/s; s/#\[cfg\(any\(\n    target_os = "android",\n    target_os = "ios",\n    target_os = "linux",\n    target_os = "macos",\n\)\)\](\nsockopt_impl!\(\n(?:.|\n)*?\n    Ipv6DontFrag,)/#[cfg(any(\n    target_os = "android",\n    target_os = "ios",\n    all(target_os = "linux", not(target_env = "uclibc")),\n    target_os = "macos",\n))]$$1/s' "$$nix_dir/src/sys/socket/sockopt.rs"; \
	perl -0pi -e 's/#\[cfg\(any\(target_os = "android", target_os = "freebsd", target_os = "linux"\)\)\]\n            #\[cfg\(feature = "net"\)\]\n            \(libc::IPPROTO_IPV6, libc::IPV6_ORIGDSTADDR\) =>/#[cfg(any(target_os = "android", target_os = "freebsd", all(target_os = "linux", not(target_env = "uclibc"))))]\n            #[cfg(feature = "net")]\n            (libc::IPPROTO_IPV6, libc::IPV6_ORIGDSTADDR) =>/g; s/#\[cfg\(any\(target_os = "android", target_os = "freebsd", target_os = "linux"\)\)\]\n            #\[cfg\(feature = "net"\)\]\n            \(libc::IPPROTO_IPV6, libc::IPV6_DONTFRAG\) =>/#[cfg(any(target_os = "android", target_os = "freebsd", all(target_os = "linux", not(target_env = "uclibc"))))]\n            #[cfg(feature = "net")]\n            (libc::IPPROTO_IPV6, libc::IPV6_DONTFRAG) =>/g' "$$nix_dir/src/sys/socket/mod.rs"; \
done; \
$(call NIX_APPLY_LIBC_BITFLAGS_CAST_PATCH__INT,$(1))
endef

# Expand to the getrandom backend implementation path in Cargo registry.
# $1: getrandom crate version (for example: 0.3.4)
define GETRANDOM_BACKEND_PATH_GLOB__INT
$$HOME/.cargo/registry/src/*/getrandom-$(1)/src/backends/getrandom.rs
endef

# Apply uClibc MIPS fallback for getrandom 0.3.x/0.4.x when libc::getrandom is missing.
# Supports both backend syntaxes used by 0.3.x and 0.4.x.
# $1: getrandom crate version (for example: 0.3.4 or 0.4.2)
define GETRANDOM_APPLY_UCLIBC_MIPS_SYSCALL_PATCH__INT
for getrandom_src in $(call GETRANDOM_BACKEND_PATH_GLOB__INT,$(1)); do \
	[ -f "$$getrandom_src" ] || continue; \
	if grep -q 'util_libc::sys_fill_exact(dest, |buf| unsafe {' "$$getrandom_src"; then \
		perl -0pi -e 's@util_libc::sys_fill_exact\(dest, \|buf\| unsafe \{\n(?:.|\n)*?\n    \}\)@util_libc::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n        let ret = libc::syscall(\n            libc::SYS_getrandom,\n            buf.as_mut_ptr() as *mut libc::c_void,\n            buf.len(),\n            0,\n        ) as libc::ssize_t;\n        #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n        let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n        ret\n    })@s' "$$getrandom_src"; \
	elif grep -q 'utils::sys_fill_exact(dest, |buf| unsafe {' "$$getrandom_src"; then \
		perl -0pi -e 's@utils::sys_fill_exact\(dest, \|buf\| unsafe \{\n(?:.|\n)*?\n    \}\)@utils::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        {\n            #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n            let ret = libc::syscall(\n                libc::SYS_getrandom,\n                buf.as_mut_ptr() as *mut libc::c_void,\n                buf.len(),\n                0,\n            ) as libc::ssize_t;\n            #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n            let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n            ret\n        }\n    })@s' "$$getrandom_src"; \
	else \
		perl -0pi -e 's@let ret = libc::getrandom\(buf\.as_mut_ptr\(\)\.cast\(\), buf\.len\(\), 0\);@// Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n        let ret = libc::syscall(\n            libc::SYS_getrandom,\n            buf.as_mut_ptr() as *mut libc::c_void,\n            buf.len(),\n            0,\n        ) as libc::ssize_t;\n        #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n        let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);@s' "$$getrandom_src"; \
	fi; \
done;
endef

# Expand to the tui-textarea crate directory glob in Cargo registry.
# $1: tui-textarea crate version (for example: 0.7.0)
define TUI_TEXTAREA_REGISTRY_DIR_GLOB__INT
$$HOME/.cargo/registry/src/*/tui-textarea-$(1)
endef

# Apply AtomicU64 fallback for tui-textarea on targets without native 64-bit atomics.
# This version avoids adding new dependencies, so --locked builds keep working.
# $1: tui-textarea crate version (for example: 0.7.0)
define TUI_TEXTAREA_APPLY_ATOMICU64_FALLBACK__INT
for textarea_dir in $(call TUI_TEXTAREA_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$textarea_dir" ] || continue; \
	perl -0pi -e 's@\n\[dependencies\.portable-atomic\]\nversion = "1"\n@@g' "$$textarea_dir/Cargo.toml"; \
	perl -0pi -e 's@#\[cfg\(feature = "ratatui"\)\]\nuse ratatui::text::Line;\n(?:.|\n)*?#\[cfg\(feature = "tuirs"\)\]\nuse tui::text::Spans as Line;@#[cfg(feature = "ratatui")]\nuse ratatui::text::Line;\nuse std::cmp;\n// Freetz 32-bit fallback for AtomicU64 without extra dependencies.\n#[cfg(target_has_atomic = "64")]\nuse std::sync::atomic::{AtomicU64, Ordering};\n#[cfg(not(target_has_atomic = "64"))]\nuse std::sync::{atomic::Ordering, Mutex};\n\n#[cfg(not(target_has_atomic = "64"))]\n#[derive(Debug, Default)]\nstruct AtomicU64(Mutex<u64>);\n\n#[cfg(not(target_has_atomic = "64"))]\nimpl AtomicU64 {\n    fn new(value: u64) -> Self { Self(Mutex::new(value)) }\n    fn load(&self, _ordering: Ordering) -> u64 { *self.0.lock().expect("atomic64 emulation lock") }\n    fn store(&self, value: u64, _ordering: Ordering) { *self.0.lock().expect("atomic64 emulation lock") = value; }\n    fn get_mut(&mut self) -> &mut u64 { self.0.get_mut().expect("atomic64 emulation lock") }\n}\n#[cfg(feature = "tuirs")]\nuse tui::text::Spans as Line;@s' "$$textarea_dir/src/widget.rs"; \
	perl -0pi -e 's@(#\[cfg\(feature = "ratatui"\)\]\nuse ratatui::text::Line;\n)(?!use std::cmp;\n)@$$1use std::cmp;\n@s' "$$textarea_dir/src/widget.rs"; \
done;
endef

# Apply AtomicU64 → AtomicUsize fix for the log2src git dependency.
# log2src is pulled via git checkout; glob matches any checkout hash.
# Removes portable-atomic dependency and rewrites progress.rs to use AtomicUsize.
define LOG2SRC_APPLY_ATOMICU64_FALLBACK__INT
for log2src_dir in $$HOME/.cargo/git/checkouts/log2src-*/*; do \
	[ -f "$$log2src_dir/Cargo.toml" ] || continue; \
	perl -0pi -e 's/\nportable-atomic = "1\.13\.1"//g' "$$log2src_dir/Cargo.toml"; \
	perl -0pi -e 's/use portable_atomic::AtomicU64;\nuse std::sync::atomic::Ordering;/use std::sync::atomic::{AtomicUsize, Ordering};/; s/use std::sync::atomic::\{AtomicU64, Ordering\};/use std::sync::atomic::{AtomicUsize, Ordering};/; s/pub completed: AtomicU64,/pub completed: AtomicUsize,/; s/self\.completed\.load\(Ordering::Relaxed\) as u64 < self\.total/(self.completed.load(Ordering::Relaxed) as u64) < self.total/; s/self\.completed\.load\(Ordering::Relaxed\) < self\.total/(self.completed.load(Ordering::Relaxed) as u64) < self.total/; s/fetch_add\(amount, Ordering::Relaxed\)/fetch_add(amount as usize, Ordering::Relaxed)/; s/store\(self\.info\.total, Ordering::Relaxed\)/store(self.info.total as usize, Ordering::Relaxed)/; s/AtomicU64::new\(0\)/AtomicUsize::new(0)/' "$$log2src_dir/src/progress.rs"; \
done;
endef

# Apply 32-bit-friendly generation counter in gitui asyncgit helper crate.
define GITUI_APPLY_ASYNCGIT_GENERATION_ATOMIC_PATCH__INT
if ! grep -q 'Freetz 32-bit atomic fallback for generation counter.' asyncgit/src/status.rs; then \
	perl -0pi -e 's@atomic::\{AtomicU64, AtomicUsize, Ordering\}@atomic::{AtomicUsize, Ordering}@; s@/// Counter that increments after each completed fetch\.\n\tgeneration: Arc<AtomicU64>,@/// Freetz 32-bit atomic fallback for generation counter.\n\tgeneration: Arc<AtomicUsize>,@; s@generation: Arc::new\(AtomicU64::new\(0\)\),@generation: Arc::new(AtomicUsize::new(0)),@' asyncgit/src/status.rs; \
fi;
endef

# --- Rust package boilerplate helpers ---

# Define RUST_TARGET_DIR and RUST_TARGET_ARG for the current package.
# $(PKG) must be set (typically by PKG_INIT_BIN).
# Usage: $(eval $(call RUST_TARGET_VARS))
define RUST_TARGET_VARS
$(PKG)_RUST_TARGET_DIR:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(basename $(notdir $(RUST_TARGET_CUSTOM_NAME))))
$(PKG)_RUST_TARGET_ARG:=$(if $(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_BUILTIN_NAME),$(RUST_TARGET_SPEC_FILE))
endef

# Define CARGO_BUILD_STD_FLAGS and CARGO_BUILD_CMD for the current package.
# $(PKG) must be set.
# Usage: $(eval $(call RUST_CARGO_BUILD_STD_VARS))
define RUST_CARGO_BUILD_STD_VARS
$(PKG)_CARGO_BUILD_STD_FLAGS:=-Z build-std=std\,panic_abort
$(PKG)_CARGO_BUILD_CMD:=$(if $(RUST_TARGET_NEEDS_STD_BUILD),cargo +nightly build --release --locked $$($(PKG)_CARGO_BUILD_STD_FLAGS),cargo build --release --locked)
endef

# Define DEPENDS_ON and REBUILD_SUBOPTS for Rust packages.
# $(PKG) must be set.
# Usage: $(eval $(call RUST_DEPENDS_VARS))
define RUST_DEPENDS_VARS
$(PKG)_DEPENDS_ON += rust-host
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_BUILTIN_TARGET
$(PKG)_REBUILD_SUBOPTS += FREETZ_TARGET_RUST_CUSTOM_TARGET
endef

# Set environment variables for openssl-sys cross-compilation.
# Uses TARGET-PREFIXED UPPERCASE vars (e.g. MIPS_UNKNOWN_LINUX_UCLIBC_OPENSSL_DIR)
# which openssl-sys reads only for the specific cross target, NOT for host builds.
# This avoids contaminating host-side build scripts (like ssh2-config, libssh2-sys)
# with sysroot lib/include paths that the host compiler/linker cannot use.
# PKG_CONFIG vars are intentionally omitted: they leak ARM/MIPS lib paths into
# HOST linker commands, causing "incompatible with elf32-littlearm" link failures.
# $1: rust env target with underscores, lowercase (e.g. mips_unknown_linux_uclibc)
define RUST_OPENSSL_CROSS_ENV__INT
	_RUST_TGT_UPPER=$$(echo "$(1)" | tr '[:lower:]' '[:upper:]'); \
	if [ -f "$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib/libssl.so.3" ]; then \
		echo "System OpenSSL found: setting $${_RUST_TGT_UPPER}_OPENSSL_DIR" >&2; \
		export OPENSSL_NO_VENDOR=1; \
		export $${_RUST_TGT_UPPER}_OPENSSL_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr"; \
		export $${_RUST_TGT_UPPER}_OPENSSL_LIB_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib"; \
		export $${_RUST_TGT_UPPER}_OPENSSL_INCLUDE_DIR="$(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include"; \
	else \
		echo "No system OpenSSL - openssl-sys will use vendored" >&2; \
	fi;
endef

# Patch openssl-src crate to recognise uClibc ARM targets.
# openssl-src's build/main.rs matches target triples to OpenSSL config names.
# armv7-unknown-linux-uclibceabi is not listed; patch it to use linux-armv4
# (same as armv7-unknown-linux-musleabihf). Idempotent: skips if already patched.
define OPENSSL_SRC_APPLY_UCLIBC_ARM_PATCH__INT
for openssl_src_build in $$HOME/.cargo/registry/src/*/openssl-src-*/build/main.rs; do \
	[ -f "$$openssl_src_build" ] || continue; \
	if grep -q "armv7-unknown-linux-uclibceabi" "$$openssl_src_build" 2>/dev/null; then \
		echo "openssl-src already patched for ARM uClibc" >&2; \
	else \
		sed -i 's/"armv7-unknown-linux-musleabihf"/"armv7-unknown-linux-musleabihf"\n            "armv7-unknown-linux-uclibceabi" => "linux-armv4",/' "$$openssl_src_build"; \
		echo "Patched openssl-src: armv7-unknown-linux-uclibceabi -> linux-armv4" >&2; \
	fi; \
done;
endef

# On MIPS FRITZ!Box targets, PIE executables crash with ld-uClibc.so.1 (SIGSEGV).
# Force -no-pie only on MIPS; other architectures support PIE fine.
# Guard against duplicate appends when multiple packages include this file.
ifeq ($(strip $(FREETZ_TARGET_ARCH_MIPS)),y)
ifndef RUSTFLAGS_NO_PIE_GUARD
RUSTFLAGS += -C link-arg=-Wl,-no-pie
export RUSTFLAGS
RUSTFLAGS_NO_PIE_GUARD := 1
endif
endif