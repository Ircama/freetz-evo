#!/usr/bin/env python3
# Generate the 2021-style (libc 0.2.168..0.2.182) aarch64-uclibc module from the
# NEW-STYLE (>= 0.2.183) module.
# Differences applied:
#   - keep `use crate::prelude::*;` (prelude exists in this range)
#   - define Padding<T> locally (prelude lacks it until >= 0.2.183)
#   - off_t/time_t/... are NOT at crate root (arch module defines them locally)
#     -> crate::X for those becomes bare X
#   - msgqnum_t/msglen_t/Ioctl not at crate root -> define locally
#   - sem_t union -> struct (unions gated on cfg libc_union)

import re

SRC = "make/include/rust/libc-aarch64-uclibc.rs"
DST = "make/include/rust/libc-aarch64-uclibc-2021.rs"

# Types the module defines itself -> reference bare (NOT crate::).
LOCAL = {
    "wchar_t","time_t","clock_t","fsblkcnt_t","fsfilcnt_t","ino_t","nlink_t",
    "off_t","fsword_t","suseconds_t","blksize_t","blkcnt_t","fsblkcnt64_t",
    "fsfilcnt64_t","__u64","__s64","pthread_t","stat64","stat","__sched_param",
    "pthread_attr_t","ipc_perm","shmid_ds","msqid_ds","msghdr","cmsghdr",
    "sysinfo","statfs","statfs64","statvfs64","termios","sigaction","sigset_t",
    "siginfo_t","stack_t","flock","sem_t","NCCS","msgqnum_t","msglen_t",
}

with open(SRC) as f:
    text = f.read()

# sem_t union -> struct
sem_re = re.compile(
    r"s_no_extra_traits!\s*\{\s*pub union sem_t \{\s*__size: \[c_char; 32\],\s*__align: c_longlong,\s*\}\s*\}", re.S)
def sem_struct(m):
    return ("s! {\n    pub struct sem_t {\n        __size: [crate::c_char; 32],\n"
            "        __align: [crate::c_long; 0],\n    }\n}")
text = sem_re.sub(sem_struct, text)

# crate::X -> bare for locally-defined types; keep crate:: for crate-root ones
def crate_repl(m):
    name = m.group(1)
    if name == "Ioctl":
        return "crate::c_ulong"
    if name in LOCAL:
        return name
    return "crate::" + name
text = re.sub(r"crate::([a-zA-Z0-9_]+)", crate_repl, text)

# prepend header (after the prelude use line stays at top)
header = (
    "//! Definitions for uClibc on 64-bit aarch64 systems (2021-style libc,\n"
    "//! 0.2.168..0.2.182: crate::prelude exists, but no Padding<T> and the\n"
    "//! uclibc arch module owns off_t/time_t/... locally).\n"
    "pub type Padding<T> = [T; 0];\n"
    "// msgqnum_t/msglen_t are not at crate root in this libc range.\n"
    "pub type msgqnum_t = crate::c_ulong;\n"
    "pub type msglen_t = crate::c_ulong;\n\n"
)
text = header + text

with open(DST, "w") as f:
    f.write(text)

print("generated", DST)
left = re.findall(r"crate::([a-zA-Z0-9_]+)", text)
# report crate:: refs that are NOT in a known-good crate-root set
known_root = {"c_long","c_ulong","c_int","c_uint","c_short","c_ushort","c_void",
    "c_ulonglong","c_longlong","pid_t","size_t","uid_t","gid_t","mode_t","dev_t",
    "off64_t","ino64_t","blkcnt64_t","key_t","iovec","timespec","socklen_t",
    "sa_family_t","in_port_t","in_addr","in6_addr","sighandler_t","shmatt_t",
    "speed_t","tcflag_t","cc_t","fsid_t","ipc_perm"}
odd = {n for n in left if n not in known_root}
print("crate:: refs non-standard:", odd if odd else "none")
