#!/usr/bin/env python3
# Generate the OLD-STYLE (libc <= 0.2.159, edition 2015, no crate::prelude, no
# primitives.rs) aarch64-uclibc module from the NEW-STYLE (>= 0.2.183) module.
# Differences applied:
#   - drop `use crate::prelude::*;`
#   - define c_char/c_long/c_ulong locally (old libc lacks primitives.rs)
#   - define Padding<T> locally (old libc lacks it)
#   - types the module defines itself (off_t, time_t, ...) -> bare reference
#   - crate-root types available in 0.2.159 (pid_t, size_t, ...) -> `::`-path
#   - bare c_int/c_uint/c_short/c_ushort/c_void/size_t/cc_t -> `::`-path
#   - msgqnum_t/msglen_t not at crate root in 0.2.159 -> define locally
#   - crate::Ioctl not available -> ::c_ulong
#   - sem_t union -> struct (0.2.159 unions gated on cfg libc_union)

import re, sys

SRC = "make/include/rust/libc-aarch64-uclibc.rs"
DST = "make/include/rust/libc-aarch64-uclibc-159.rs"

# Types the module defines itself (type aliases, structs, consts used as types).
LOCAL = {
    "wchar_t","time_t","clock_t","fsblkcnt_t","fsfilcnt_t","ino_t","nlink_t",
    "off_t","fsword_t","suseconds_t","blksize_t","blkcnt_t","fsblkcnt64_t",
    "fsfilcnt64_t","__u64","__s64","pthread_t","stat64","stat","__sched_param",
    "pthread_attr_t","ipc_perm","shmid_ds","msqid_ds","msghdr","cmsghdr",
    "sysinfo","statfs","statfs64","statvfs64","termios","sigaction","sigset_t",
    "siginfo_t","stack_t","flock","sem_t","NCCS","msgqnum_t","msglen_t",
}

# crate::X -> ::X (available at crate root in 0.2.159, per libc-x86-uclibc-159.rs)
CRATE_ROOT = {
    "fsid_t","gid_t","uid_t","iovec","key_t","pid_t","shmatt_t","sighandler_t",
    "size_t","socklen_t","speed_t","tcflag_t","cc_t",
}

# bare -> :: (crate-root primitives in 0.2.159)
BARE_TO_ROOT = ["c_int","c_uint","c_short","c_ushort","c_void","size_t",
                "cc_t","c_ulonglong","c_longlong"]

with open(SRC) as f:
    text = f.read()

# 1) drop the prelude use line
text = re.sub(r"^use crate::prelude::\*;\n", "", text, flags=re.M)

# 2) sem_t union -> struct (old libc unions need cfg libc_union)
sem_re = re.compile(
    r"s_no_extra_traits!\s*\{\s*pub union sem_t \{\s*__size: \[c_char; 32\],\s*__align: c_longlong,\s*\}\s*\}", re.S)
def sem_struct(m):
    return ("s! {\n    pub struct sem_t {\n        __size: [::c_char; 32],\n"
            "        __align: [::c_long; 0],\n    }\n}")
text = sem_re.sub(sem_struct, text)

# 3) crate::X rewrites (must be done BEFORE generic :: additions; the
#    msgqnum_t/msglen_t/Ioctl special cases first, then LOCAL vs CRATE_ROOT)
def crate_repl(m):
    name = m.group(1)
    if name == "prelude":
        return ""  # should have been removed by the use-line drop
    if name == "Ioctl":
        return "::c_ulong"
    if name in LOCAL:
        return name
    if name in CRATE_ROOT:
        return "::" + name
    # fallback: assume crate-root (will surface in compile if wrong)
    return "::" + name
text = re.sub(r"crate::([a-zA-Z0-9_]+)", crate_repl, text)

# 4) bare primitives -> :: (not preceded by word char or ':')
for tok in BARE_TO_ROOT:
    text = re.sub(r"(?<![\w:])" + re.escape(tok) + r"\b", "::" + tok, text)

# 5) prepend the old-style header
header = (
    "//! Definitions for uClibc on 64-bit aarch64 systems (old-style libc,\n"
    "//! edition 2015 / <= 0.2.159: no crate::prelude, no primitives.rs).\n"
    "// aarch64 is an ARM target: plain `char` is unsigned, so c_char must be\n"
    "// u8 (matches std::os::raw::c_char and libc's own primitives on aarch64).\n"
    "pub type c_char = u8;\n"
    "pub type c_long = i64;\n"
    "pub type c_ulong = u64;\n"
    "// Padding<T> is provided by crate::prelude only in newer libc; define it\n"
    "// locally so the struct bodies can be shared verbatim across variants.\n"
    "pub type Padding<T> = [T; 0];\n"
    "// msgqnum_t/msglen_t are not at crate root in old libc.\n"
    "pub type msgqnum_t = ::c_ulong;\n"
    "pub type msglen_t = ::c_ulong;\n\n"
)
text = header + text

with open(DST, "w") as f:
    f.write(text)

print("generated", DST)
# sanity: report leftover crate:: or bare c_* that might be wrong
left = re.findall(r"crate::\w+", text)
bare = [t for t in BARE_TO_ROOT if re.search(r"(?<![\w:])" + t + r"\b", text)]
print("leftover crate:: :", set(left) if left else "none")
print("leftover bare c_*:", bare if bare else "none")
