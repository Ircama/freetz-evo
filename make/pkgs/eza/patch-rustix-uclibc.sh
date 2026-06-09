#!/bin/sh
# Patch rustix and getrandom crates in the cargo registry for uClibc/MIPS compatibility.
# Called from eza.mk after cargo fetch, before cargo build.
# Uses $CARGO_HOME to locate registry sources.

set -e
: "${CARGO_HOME:?CARGO_HOME is not set}"

# --- Patch rustix 1.1.2 ---
# Helper: apply all rustix uClibc patches to a single rustix directory
_patch_one_rustix() {
	_rx_dir="$1"
	[ -d "$_rx_dir" ] || return 0
	chmod -R u+w "$_rx_dir" 2>/dev/null || true

	if ! grep -q 'Freetz uClibc fallbacks' "$_rx_dir/src/backend/libc/c.rs" 2>/dev/null; then
		echo "Patching rustix uClibc compat in $_rx_dir ..."

		# Add STATX__RESERVED and MFD_* fallback constants missing from uClibc
		perl -0pi -e 's@\#\[cfg\(all\(linux_raw_dep, feature = "termios"\)\)\]\npub\(crate\) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;@#[cfg(all(linux_raw_dep, feature = "termios"))]\npub(crate) const XCASE: tcflag_t = linux_raw_sys::general::XCASE as _;\n\n// Freetz uClibc fallbacks for symbols missing from libc on MIPS.\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const STATX__RESERVED: u32 = linux_raw_sys::general::STATX__RESERVED;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_NOEXEC_SEAL: c_uint = linux_raw_sys::general::MFD_NOEXEC_SEAL as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_EXEC: c_uint = linux_raw_sys::general::MFD_EXEC as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_64KB: c_uint = linux_raw_sys::general::MFD_HUGE_64KB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512KB: c_uint = linux_raw_sys::general::MFD_HUGE_512KB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1MB: c_uint = linux_raw_sys::general::MFD_HUGE_1MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2MB: c_uint = linux_raw_sys::general::MFD_HUGE_2MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_8MB: c_uint = linux_raw_sys::general::MFD_HUGE_8MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16MB: c_uint = linux_raw_sys::general::MFD_HUGE_16MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_32MB: c_uint = linux_raw_sys::general::MFD_HUGE_32MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_256MB: c_uint = linux_raw_sys::general::MFD_HUGE_256MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_512MB: c_uint = linux_raw_sys::general::MFD_HUGE_512MB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_1GB: c_uint = linux_raw_sys::general::MFD_HUGE_1GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_2GB: c_uint = linux_raw_sys::general::MFD_HUGE_2GB as _;\n#[cfg(all(linux_raw_dep, feature = "fs", target_env = "uclibc"))]\npub(crate) const MFD_HUGE_16GB: c_uint = linux_raw_sys::general::MFD_HUGE_16GB as _;@s' "$_rx_dir/src/backend/libc/c.rs"
	fi

	# Make preadv/pwritev use the non-64-suffix versions on uClibc
	perl -0pi -e 's@\#\[cfg\(any\(target_os = "linux", target_os = "hurd", target_os = "emscripten"\)\)\]\npub\(super\) use \{preadv64 as preadv, pwritev64 as pwritev\};@#[cfg(all(target_os = "linux", target_env = "uclibc"))]\npub(super) use {preadv, pwritev};\n#[cfg(any(\n    target_os = "hurd",\n    target_os = "emscripten",\n    all(target_os = "linux", not(target_env = "uclibc"))\n))]\npub(super) use {preadv64 as preadv, pwritev64 as pwritev};@s' "$_rx_dir/src/backend/libc/c.rs"

	# AT_MINSIGSTKSZ not available on older kernels
	perl -0pi -e 's/(?:c::AT_MINSIGSTKSZ|linux_raw_sys::general::AT_MINSIGSTKSZ)/51/g' "$_rx_dir/src/backend/libc/param/auxv.rs"

	# SPLICE_F_* constants need type cast on uClibc
	perl -0pi -e 's/const MOVE = c::SPLICE_F_MOVE;/const MOVE = linux_raw_sys::general::SPLICE_F_MOVE as _;/; s/const NONBLOCK = c::SPLICE_F_NONBLOCK;/const NONBLOCK = linux_raw_sys::general::SPLICE_F_NONBLOCK as _;/; s/const MORE = c::SPLICE_F_MORE;/const MORE = linux_raw_sys::general::SPLICE_F_MORE as _;/; s/const GIFT = c::SPLICE_F_GIFT;/const GIFT = linux_raw_sys::general::SPLICE_F_GIFT as _;/' "$_rx_dir/src/backend/libc/pipe/types.rs"

	# PIDFD_NONBLOCK type cast
	perl -0pi -e 's/const NONBLOCK = backend::c::PIDFD_NONBLOCK;/const NONBLOCK = backend::c::PIDFD_NONBLOCK as ffi::c_uint;/' "$_rx_dir/src/process/pidfd.rs"

	# getpriority/setpriority PRIO_* const type casts
	perl -0pi -e 's/c::getpriority\(c::PRIO_USER, uid\.as_raw\(\) as _\)/c::getpriority(c::PRIO_USER as _, uid.as_raw() as _)/g; s/c::getpriority\(c::PRIO_PGRP, Pid::as_raw\(pgid\) as _\)/c::getpriority(c::PRIO_PGRP as _, Pid::as_raw(pgid) as _)/g; s/c::getpriority\(c::PRIO_PROCESS, Pid::as_raw\(pid\) as _\)/c::getpriority(c::PRIO_PROCESS as _, Pid::as_raw(pid) as _)/g; s/c::setpriority\(c::PRIO_USER, uid\.as_raw\(\) as _, priority\)/c::setpriority(c::PRIO_USER as _, uid.as_raw() as _, priority)/g; s/c::PRIO_PGRP,/c::PRIO_PGRP as _,/; s/c::PRIO_PROCESS,/c::PRIO_PROCESS as _,/;' "$_rx_dir/src/backend/libc/process/syscalls.rs"

	# termios constant type casts (uClibc uses i32, bitflags expects u32)
	perl -0pi -e 's/const CRDLY = c::CRDLY;/const CRDLY = c::CRDLY as c::tcflag_t;/; s/const FFDLY = c::FFDLY;/const FFDLY = c::FFDLY as c::tcflag_t;/; s/const VTDLY = c::VTDLY;/const VTDLY = c::VTDLY as c::tcflag_t;/; s/const CMSPAR = c::CMSPAR;/const CMSPAR = linux_raw_sys::general::CMSPAR as c::tcflag_t;/; s/const CMSPAR = c::CMSPAR as c::tcflag_t;/const CMSPAR = linux_raw_sys::general::CMSPAR as c::tcflag_t;/;' "$_rx_dir/src/termios/types.rs"

	# HWPOISON constant not available on uClibc
	perl -0pi -e 's/pub const HWPOISON: Self = Self\(c::EHWPOISON\);/#[cfg(not(target_env = "uclibc"))]\n    pub const HWPOISON: Self = Self(c::EHWPOISON);\n    #[cfg(target_env = "uclibc")]\n    #[allow(missing_docs)]\n    pub const HWPOISON: Self = Self(linux_raw_sys::general::EHWPOISON as _);/; s/    #[cfg(target_env = "uclibc")]\n    pub const HWPOISON: Self = Self\(linux_raw_sys::general::EHWPOISON as _\);/    #[cfg(target_env = "uclibc")]\n    #[allow(missing_docs)]\n    pub const HWPOISON: Self = Self(linux_raw_sys::general::EHWPOISON as _);/' "$_rx_dir/src/backend/libc/io/errno.rs"

	echo "  done."
}

# Patch all rustix copies under $CARGO_HOME/registry/src/
for rustix_dir in "$CARGO_HOME/registry/src/"*"/rustix-1.1.2"; do
	[ -d "$rustix_dir" ] || continue
	_patch_one_rustix "$rustix_dir"
done

# Also patch the persistent patched copy if the build recipe created one
for patched_dir in "$CARGO_HOME/rustix-1.1.2-patched"; do
	[ -d "$patched_dir" ] || continue
	# Skip if it's actually inside registry/src (already handled above)
	case "$patched_dir" in
		*/registry/src/*) continue ;;
	esac
	_patch_one_rustix "$patched_dir"
done

# --- Patch getrandom 0.3.3 ---
for getrandom_src in "$CARGO_HOME/registry/src/"*"/getrandom-0.3.3/src/backends/getrandom.rs"; do
	[ -f "$getrandom_src" ] || continue

	if grep -q 'util_libc::sys_fill_exact(dest, |buf| unsafe {' "$getrandom_src"; then
		perl -0pi -e 's@util_libc::sys_fill_exact\(dest, \|buf\| unsafe \{\n(?:.|\n)*?\n    }\)@util_libc::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n        let ret = libc::syscall(\n            libc::SYS_getrandom,\n            buf.as_mut_ptr() as *mut libc::c_void,\n            buf.len(),\n            0,\n        ) as libc::ssize_t;\n        #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n        let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n        ret\n    })@s' "$getrandom_src"
	elif grep -q 'utils::sys_fill_exact(dest, |buf| unsafe {' "$getrandom_src"; then
		perl -0pi -e 's@utils::sys_fill_exact\(dest, \|buf\| unsafe \{\n(?:.|\n)*?\n    }\)@utils::sys_fill_exact(dest, |buf| unsafe {\n        // Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        {\n            #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n            let ret = libc::syscall(\n                libc::SYS_getrandom,\n                buf.as_mut_ptr() as *mut libc::c_void,\n                buf.len(),\n                0,\n            ) as libc::ssize_t;\n            #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n            let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);\n            ret\n        }\n    })@s' "$getrandom_src"
	else
		perl -0pi -e 's@let ret = libc::getrandom\(buf\.as_mut_ptr\(\)\.cast\(\), buf\.len\(\), 0\);@// Freetz uClibc mips syscall fallback for missing libc::getrandom.\n        #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n        let ret = libc::syscall(\n            libc::SYS_getrandom,\n            buf.as_mut_ptr() as *mut libc::c_void,\n            buf.len(),\n            0,\n        ) as libc::ssize_t;\n        #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n        let ret = libc::getrandom(buf.as_mut_ptr().cast(), buf.len(), 0);@s' "$getrandom_src"
	fi
done

# --- Patch getrandom 0.2.16 ---
for getrandom_src in "$CARGO_HOME/registry/src/"*"/getrandom-0.2.16/src/getrandom.rs"; do
	[ -f "$getrandom_src" ] || continue
	grep -q 'Freetz uClibc' "$getrandom_src" && continue

	perl -0pi -e 's@libc::getrandom\(buf_ptr, len, 0\)@// Freetz uClibc mips syscall fallback for missing libc::getrandom\n            #[cfg(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel")))]\n            let ret = libc::syscall(\n                libc::SYS_getrandom,\n                buf_ptr,\n                len,\n                0,\n            ) as libc::ssize_t;\n            #[cfg(not(all(target_os = "linux", target_env = "uclibc", any(target_arch = "mips", target_arch = "mipsel"))))]\n            let ret = libc::getrandom(buf_ptr, len, 0)@s' "$getrandom_src"
done
