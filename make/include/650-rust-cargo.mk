### Rust/Cargo macros

# Expand to the rustix crate directory glob in Cargo registry.
# $1: rustix crate version (for example: 1.1.3)
define RUSTIX_REGISTRY_DIR_GLOB__INT
$$HOME/.cargo/registry/src/*/rustix-$(1)
endef

# Apply patch commands identical across rustix layouts.
define RUSTIX_APPLY_COMMON_UCLIBC_PATCHES__INT
	perl -0pi -e 's/c::getpriority\(c::PRIO_USER, uid\.as_raw\(\) as _\)/c::getpriority(c::PRIO_USER as _, uid.as_raw() as _)/g; s/c::getpriority\(c::PRIO_PGRP, Pid::as_raw\(pgid\) as _\)/c::getpriority(c::PRIO_PGRP as _, Pid::as_raw(pgid) as _)/g; s/c::getpriority\(c::PRIO_PROCESS, Pid::as_raw\(pid\) as _\)/c::getpriority(c::PRIO_PROCESS as _, Pid::as_raw(pid) as _)/g; s/c::setpriority\(c::PRIO_USER, uid\.as_raw\(\) as _, priority\)/c::setpriority(c::PRIO_USER as _, uid.as_raw() as _, priority)/g; s/c::PRIO_PGRP,/c::PRIO_PGRP as _,/; s/c::PRIO_PROCESS,/c::PRIO_PROCESS as _,/;' "$$rustix_dir/src/backend/libc/process/syscalls.rs"; \
	perl -0pi -e 's/const CRDLY = c::CRDLY;/const CRDLY = c::CRDLY as c::tcflag_t;/; s/const FFDLY = c::FFDLY;/const FFDLY = c::FFDLY as c::tcflag_t;/; s/const VTDLY = c::VTDLY;/const VTDLY = c::VTDLY as c::tcflag_t;/; s/const CMSPAR = c::CMSPAR;/const CMSPAR = c::CMSPAR as c::tcflag_t;/;' "$$rustix_dir/src/termios/types.rs";
endef

# Apply shared rustix uClibc compatibility fixes for 1.1.x crate layout.
# $1: rustix crate version (for example: 1.1.3)
define RUSTIX_APPLY_UCLIBC_PATCHES_RAW_DEP__INT
for rustix_dir in $(call RUSTIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$rustix_dir" ] || continue; \
	if ! grep -q 'Freetz uClibc fallbacks' "$$rustix_dir/src/backend/libc/c.rs"; then \
		perl -0pi -e 's@\#\[cfg\(all\(linux_raw_dep, feature = "termios"\)\)\]\npub\(crate\) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;@#[cfg(all(linux_raw_dep, feature = "termios"))]\npub(crate) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;\n\n// Freetz uClibc fallbacks for symbols missing from libc on MIPS.\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const STATX__RESERVED: u32 = linux_raw_sys::general::STATX__RESERVED;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_NOEXEC_SEAL: c_uint = linux_raw_sys::general::MFD_NOEXEC_SEAL as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_EXEC: c_uint = linux_raw_sys::general::MFD_EXEC as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_64KB: c_uint = linux_raw_sys::general::MFD_HUGE_64KB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512KB: c_uint = linux_raw_sys::general::MFD_HUGE_512KB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1MB: c_uint = linux_raw_sys::general::MFD_HUGE_1MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2MB: c_uint = linux_raw_sys::general::MFD_HUGE_2MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_8MB: c_uint = linux_raw_sys::general::MFD_HUGE_8MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16MB: c_uint = linux_raw_sys::general::MFD_HUGE_16MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_32MB: c_uint = linux_raw_sys::general::MFD_HUGE_32MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_256MB: c_uint = linux_raw_sys::general::MFD_HUGE_256MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512MB: c_uint = linux_raw_sys::general::MFD_HUGE_512MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1GB: c_uint = linux_raw_sys::general::MFD_HUGE_1GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2GB: c_uint = linux_raw_sys::general::MFD_HUGE_2GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16GB: c_uint = linux_raw_sys::general::MFD_HUGE_16GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) type __fsword_t = linux_raw_sys::general::__fsword_t;\n#[cfg(all(linux_raw_dep, target_env = "uclibc"))]\npub(crate) const EHWPOISON: c_int = linux_raw_sys::general::EHWPOISON as _;\n#[cfg(all(linux_raw_dep, feature = "net", target_env = "uclibc"))]\npub(crate) const AF_XDP: c_int = linux_raw_sys::net::AF_XDP as _;\n#[cfg(all(linux_raw_dep, feature = "net", target_env = "uclibc"))]\npub(crate) const IP_PMTUDISC_INTERFACE: c_int = linux_raw_sys::net::IP_PMTUDISC_INTERFACE as _;\n#[cfg(all(linux_raw_dep, feature = "net", target_env = "uclibc"))]\npub(crate) const IP_PMTUDISC_OMIT: c_int = linux_raw_sys::net::IP_PMTUDISC_OMIT as _;\n#[cfg(all(linux_raw_dep, feature = "termios", target_env = "uclibc"))]\npub(crate) const CMSPAR: tcflag_t = linux_raw_sys::general::CMSPAR as _;@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	fi; \
	perl -0pi -e 's@\#\[cfg\(any\(target_os = "linux", target_os = "hurd", target_os = "emscripten"\)\)\]\npub\(super\) use \{preadv64 as preadv, pwritev64 as pwritev\};@#[cfg(all(target_os = "linux", target_env = "uclibc"))]\npub(super) use {preadv, pwritev};\n#[cfg(any(\n    target_os = "hurd",\n    target_os = "emscripten",\n    all(target_os = "linux", not(target_env = "uclibc"))\n))]\npub(super) use {preadv64 as preadv, pwritev64 as pwritev};@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	perl -0pi -e 's/const NONBLOCK = backend::c::PIDFD_NONBLOCK;/const NONBLOCK = backend::c::PIDFD_NONBLOCK as ffi::c_uint;/' "$$rustix_dir/src/process/pidfd.rs"; \
	$(call RUSTIX_APPLY_COMMON_UCLIBC_PATCHES__INT) \
done;
endef

# Apply shared rustix uClibc compatibility fixes for 0.38.x crate layout.
# $1: rustix crate version (for example: 0.38.37)
define RUSTIX_APPLY_UCLIBC_PATCHES_LINUX_KERNEL__INT
for rustix_dir in $(call RUSTIX_REGISTRY_DIR_GLOB__INT,$(1)); do \
	[ -d "$$rustix_dir" ] || continue; \
	if ! grep -q 'Freetz uClibc fallbacks' "$$rustix_dir/src/backend/libc/c.rs"; then \
		perl -0pi -e 's@\#\[cfg\(all\(linux_kernel, feature = "termios"\)\)\]\npub\(crate\) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;@#[cfg(all(linux_kernel, feature = "termios"))]\npub(crate) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;\n\n// Freetz uClibc fallbacks for symbols missing from libc on MIPS.\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const STATX__RESERVED: u32 = linux_raw_sys::general::STATX__RESERVED;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_NOEXEC_SEAL: c_uint = linux_raw_sys::general::MFD_NOEXEC_SEAL as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_EXEC: c_uint = linux_raw_sys::general::MFD_EXEC as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_64KB: c_uint = linux_raw_sys::general::MFD_HUGE_64KB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512KB: c_uint = linux_raw_sys::general::MFD_HUGE_512KB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1MB: c_uint = linux_raw_sys::general::MFD_HUGE_1MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2MB: c_uint = linux_raw_sys::general::MFD_HUGE_2MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_8MB: c_uint = linux_raw_sys::general::MFD_HUGE_8MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16MB: c_uint = linux_raw_sys::general::MFD_HUGE_16MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_32MB: c_uint = linux_raw_sys::general::MFD_HUGE_32MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_256MB: c_uint = linux_raw_sys::general::MFD_HUGE_256MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512MB: c_uint = linux_raw_sys::general::MFD_HUGE_512MB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1GB: c_uint = linux_raw_sys::general::MFD_HUGE_1GB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2GB: c_uint = linux_raw_sys::general::MFD_HUGE_2GB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16GB: c_uint = linux_raw_sys::general::MFD_HUGE_16GB as _;\n#[cfg(all(linux_kernel, feature = "fs", target_env = "uclibc"))]\npub(crate) type __fsword_t = linux_raw_sys::general::__fsword_t;\n#[cfg(all(linux_kernel, target_env = "uclibc"))]\npub(crate) const EHWPOISON: c_int = linux_raw_sys::general::EHWPOISON as _;\n#[cfg(all(linux_kernel, feature = "net", target_env = "uclibc"))]\npub(crate) const AF_XDP: c_int = linux_raw_sys::net::AF_XDP as _;\n#[cfg(all(linux_kernel, feature = "termios", target_env = "uclibc"))]\npub(crate) const CMSPAR: tcflag_t = linux_raw_sys::general::CMSPAR as _;@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	fi; \
	perl -0pi -e 's@\#\[cfg\(any\(target_os = "linux", target_os = "hurd", target_os = "emscripten"\)\)\]\npub\(super\) use libc::\{preadv64 as preadv, pwritev64 as pwritev\};@#[cfg(all(target_os = "linux", target_env = "uclibc"))]\npub(super) use libc::{preadv, pwritev};\n#[cfg(any(target_os = "hurd", target_os = "emscripten", all(target_os = "linux", not(target_env = "uclibc"))))]\npub(super) use libc::{preadv64 as preadv, pwritev64 as pwritev};@s' "$$rustix_dir/src/backend/libc/c.rs"; \
	perl -0pi -e 's/const NONBLOCK = backend::c::PIDFD_NONBLOCK;/const NONBLOCK = backend::c::PIDFD_NONBLOCK as backend::c::c_uint;/' "$$rustix_dir/src/process/pidfd.rs"; \
	$(call RUSTIX_APPLY_COMMON_UCLIBC_PATCHES__INT) \
done;
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
