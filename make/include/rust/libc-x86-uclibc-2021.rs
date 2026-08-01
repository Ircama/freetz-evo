//! Definitions for uClibc on 32-bit x86 systems

use crate::prelude::*;

pub type blkcnt_t = crate::c_long;
pub type blksize_t = crate::c_long;
pub type clock_t = crate::c_long;
pub type fsblkcnt_t = crate::c_ulong;
pub type fsfilcnt_t = crate::c_ulong;
pub type fsword_t = crate::c_long;
pub type ino_t = crate::c_ulong;
pub type nlink_t = crate::c_uint;
pub type off_t = crate::c_long;
pub type stat64 = stat;
pub type suseconds_t = crate::c_long;
pub type time_t = crate::c_int;
pub type wchar_t = crate::c_int;
pub type pthread_t = crate::c_ulong;
pub type greg_t = crate::c_int;

pub type fsblkcnt64_t = u64;
pub type fsfilcnt64_t = u64;
pub type __u64 = crate::c_ulonglong;
pub type __s64 = crate::c_longlong;

s! {
    pub struct flock {
        pub l_type: crate::c_short,
        pub l_whence: crate::c_short,
        pub l_start: off_t,
        pub l_len: off_t,
        pub l_pid: crate::pid_t,
    }

    pub struct flock64 {
        pub l_type: crate::c_short,
        pub l_whence: crate::c_short,
        pub l_start: crate::off64_t,
        pub l_len: crate::off64_t,
        pub l_pid: crate::pid_t,
    }

    pub struct ipc_perm {
        pub __key: crate::key_t,
        pub uid: crate::uid_t,
        pub gid: crate::gid_t,
        pub cuid: crate::uid_t,
        pub cgid: crate::gid_t,
        pub mode: crate::c_ushort, // read / write
        __pad1: crate::c_ushort,
        pub __seq: crate::c_ushort,
        __pad2: crate::c_ushort,
        __unused1: crate::c_ulong,
        __unused2: crate::c_ulong,
    }

    pub struct pthread_attr_t {
        __detachstate: crate::c_int,
        __schedpolicy: crate::c_int,
        __schedparam: __sched_param,
        __inheritsched: crate::c_int,
        __scope: crate::c_int,
        __guardsize: crate::size_t,
        __stackaddr_set: crate::c_int,
        __stackaddr: *mut crate::c_void, // better don't use it
        __stacksize: crate::size_t,
    }

    pub struct __sched_param {
        __sched_priority: crate::c_int,
    }

    pub struct siginfo_t {
        pub si_signo: crate::c_int,       // signal number
        pub si_errno: crate::c_int,       // if not zero: error value of signal, see errno.
        pub si_code: crate::c_int,        // signal code
        _pad: [crate::c_int; 29],     // padding to 128 bytes
    }

    pub struct shmid_ds {
        pub shm_perm: crate::ipc_perm,
        __shm_pad1: crate::c_ulong,
        pub shm_segsz: crate::size_t,
        __shm_pad2: crate::c_ulong,
        pub shm_atime: time_t,
        __shm_pad3: crate::c_ulong,
        pub shm_dtime: time_t,
        __shm_pad4: crate::c_ulong,
        pub shm_ctime: time_t,
        __shm_pad5: crate::c_ulong,
        pub shm_cpid: crate::pid_t,
        pub shm_lpid: crate::pid_t,
        pub shm_nattch: crate::shmatt_t,
        __shm_pad6: crate::c_ulong,
        __unused1: crate::c_ulong,
        __unused2: crate::c_ulong,
    }

    pub struct msqid_ds {
        pub msg_perm: crate::ipc_perm,
        __msg_pad1: crate::c_ulong,
        pub msg_stime: time_t,
        __msg_pad2: crate::c_ulong,
        pub msg_rtime: time_t,
        __msg_pad3: crate::c_ulong,
        pub msg_ctime: time_t,
        __msg_pad4: crate::c_ulong,
        __msg_cb: crate::c_ulong,
        __msg_qnum: crate::c_ulong,
        __msg_qbytes: crate::c_ulong,
        __msg_lspid: crate::c_ulong,
        __msg_lrpid: crate::c_ulong,
    }

    pub struct sockaddr {
        pub sa_family: crate::sa_family_t,
        pub sa_data: [crate::c_char; 14],
    }

    pub struct sockaddr_in {
        pub sin_family: crate::sa_family_t,
        pub sin_port: crate::in_port_t,
        pub sin_addr: crate::in_addr,
        pub sin_zero: [u8; 8],
    }

    pub struct sockaddr_in6 {
        pub sin6_family: crate::sa_family_t,
        pub sin6_port: crate::in_port_t,
        pub sin6_flowinfo: u32,
        pub sin6_addr: crate::in6_addr,
        pub sin6_scope_id: u32,
    }

    pub struct stat {
        pub st_dev: crate::dev_t,
        __pad1: crate::c_ushort,
        pub st_ino: crate::ino_t,
        pub st_mode: crate::mode_t,
        pub st_nlink: crate::nlink_t,
        pub st_uid: crate::uid_t,
        pub st_gid: crate::gid_t,
        pub st_rdev: crate::dev_t,
        __pad2: crate::c_ushort,
        pub st_size: crate::off64_t,
        pub st_blksize: crate::blksize_t,
        pub st_blocks: crate::blkcnt64_t,
        pub st_atime: time_t,
        pub st_atime_nsec: crate::c_long,
        pub st_mtime: time_t,
        pub st_mtime_nsec: crate::c_long,
        pub st_ctime: time_t,
        pub st_ctime_nsec: crate::c_long,
        __unused4: crate::c_long,
        __unused5: crate::c_long,
    }

    pub struct sigaction {
        pub sa_sigaction: crate::sighandler_t,
        pub sa_mask: crate::sigset_t,
        pub sa_flags: crate::c_ulong,
        pub sa_restorer: Option<extern "C" fn()>,
    }

    pub struct stack_t {
        pub ss_sp: *mut crate::c_void,
        pub ss_flags: crate::c_int,
        pub ss_size: crate::size_t,
    }

    pub struct _libc_fpreg {
        pub significand: [u16; 4],
        pub exponent: u16,
    }

    pub struct _libc_fpstate {
        pub cw: crate::c_ulong,
        pub sw: crate::c_ulong,
        pub tag: crate::c_ulong,
        pub ipoff: crate::c_ulong,
        pub cssel: crate::c_ulong,
        pub dataoff: crate::c_ulong,
        pub datasel: crate::c_ulong,
        pub _st: [_libc_fpreg; 8],
        pub status: crate::c_ulong,
    }

    pub struct mcontext_t {
        pub gregs: [greg_t; 19],
        pub fpregs: *mut _libc_fpstate,
        pub oldmask: crate::c_ulong,
        pub cr2: crate::c_ulong,
    }

    pub struct statfs {
        pub f_type: crate::c_long,
        pub f_bsize: crate::c_long,
        pub f_blocks: crate::fsblkcnt_t,
        pub f_bfree: crate::fsblkcnt_t,
        pub f_bavail: crate::fsblkcnt_t,
        pub f_files: crate::fsfilcnt_t,
        pub f_ffree: crate::fsfilcnt_t,
        pub f_fsid: crate::fsid_t,
        pub f_namelen: crate::c_long,
        pub f_frsize: crate::c_long,
        pub f_flags: crate::c_long,
        pub f_spare: [crate::c_long; 4],
    }

    pub struct statfs64 {
        pub f_type: crate::c_long,
        pub f_bsize: crate::c_long,
        pub f_blocks: u64,
        pub f_bfree: u64,
        pub f_bavail: u64,
        pub f_files: u64,
        pub f_ffree: u64,
        pub f_fsid: crate::fsid_t,
        pub f_namelen: crate::c_long,
        pub f_frsize: crate::c_long,
        pub f_flags: crate::c_long,
        pub f_spare: [crate::c_long; 4],
    }

    pub struct statvfs64 {
        pub f_type: crate::c_ulong,
        pub f_bsize: crate::c_ulong,
        pub f_blocks: u64,
        pub f_bfree: u64,
        pub f_bavail: u64,
        pub f_files: u64,
        pub f_ffree: u64,
        pub f_fsid: crate::c_ulong,
        pub f_namelen: crate::c_ulong,
        pub f_frsize: crate::c_ulong,
        pub f_flags: crate::c_ulong,
        pub f_spare: [crate::c_ulong; 4],
    }

    pub struct msghdr {
        pub msg_name: *mut crate::c_void,
        pub msg_namelen: crate::socklen_t,
        pub msg_iov: *mut crate::iovec,
        pub msg_iovlen: crate::c_int,
        pub msg_control: *mut crate::c_void,
        pub msg_controllen: crate::socklen_t,
        pub msg_flags: crate::c_int,
    }

    pub struct termios {
        pub c_iflag: crate::tcflag_t,
        pub c_oflag: crate::tcflag_t,
        pub c_cflag: crate::tcflag_t,
        pub c_lflag: crate::tcflag_t,
        pub c_line: crate::cc_t,
        pub c_cc: [crate::cc_t; NCCS],
    }

    pub struct sigset_t {
        __val: [crate::c_ulong; 32],
    }

    pub struct sysinfo {
        pub uptime: crate::c_long,
        pub loads: [crate::c_ulong; 3],
        pub totalram: crate::c_ulong,
        pub freeram: crate::c_ulong,
        pub sharedram: crate::c_ulong,
        pub bufferram: crate::c_ulong,
        pub totalswap: crate::c_ulong,
        pub freeswap: crate::c_ulong,
        pub procs: crate::c_ushort,
        pub pad: crate::c_ushort,
        pub totalhigh: crate::c_ulong,
        pub freehigh: crate::c_ulong,
        pub mem_unit: crate::c_uint,
        pub _f: [crate::c_char; 0],
    }

    pub struct sem_t {
        __size: [crate::c_char; 16],
        __align: [crate::c_long; 0],
    }

    pub struct cmsghdr {
        pub cmsg_len: crate::size_t,
        pub cmsg_level: crate::c_int,
        pub cmsg_type: crate::c_int,
    }
}

s_no_extra_traits! {
    pub struct ucontext_t {
        pub uc_flags: crate::c_ulong,
        pub uc_link: *mut ucontext_t,
        pub uc_stack: crate::stack_t,
        pub uc_mcontext: mcontext_t,
        pub uc_sigmask: crate::sigset_t,
        __private: [u8; 112],
        __ssp: [crate::c_ulong; 4],
    }
}

cfg_if! {
    if #[cfg(feature = "extra_traits")] {
        impl PartialEq for ucontext_t {
            fn eq(&self, other: &ucontext_t) -> bool {
                self.uc_flags == other.uc_flags
                    && self.uc_link == other.uc_link
                    && self.uc_stack == other.uc_stack
                    && self.uc_mcontext == other.uc_mcontext
                    && self.uc_sigmask == other.uc_sigmask
                // Ignore __private field
            }
        }

        impl Eq for ucontext_t {}

        impl hash::Hash for ucontext_t {
            fn hash<H: hash::Hasher>(&self, state: &mut H) {
                self.uc_flags.hash(state);
                self.uc_link.hash(state);
                self.uc_stack.hash(state);
                self.uc_mcontext.hash(state);
                self.uc_sigmask.hash(state);
                // Ignore __private field
            }
        }
    }
}

// Constants from gnu/b32/x86/mod.rs
pub const VEOF: usize = 4;
pub const RTLD_DEEPBIND: crate::c_int = 0x8;
pub const RTLD_GLOBAL: crate::c_int = 0x100;
pub const O_DIRECT: crate::c_int = 0x4000;
pub const O_DIRECTORY: crate::c_int = 0x10000;
pub const O_NOFOLLOW: crate::c_int = 0x20000;
pub const O_LARGEFILE: crate::c_int = 0o0100000;
pub const O_APPEND: crate::c_int = 1024;
pub const O_CREAT: crate::c_int = 64;
pub const O_EXCL: crate::c_int = 128;
pub const O_NOCTTY: crate::c_int = 256;
pub const O_NONBLOCK: crate::c_int = 2048;
pub const O_SYNC: crate::c_int = 1052672;
pub const O_RSYNC: crate::c_int = 1052672;
pub const O_DSYNC: crate::c_int = 4096;
pub const O_FSYNC: crate::c_int = 0x101000;
pub const O_ASYNC: crate::c_int = 0x2000;
pub const O_NDELAY: crate::c_int = 0x800;
pub const MADV_SOFT_OFFLINE: crate::c_int = 101;
pub const MAP_LOCKED: crate::c_int = 0x02000;
pub const MAP_NORESERVE: crate::c_int = 0x04000;
pub const MAP_32BIT: crate::c_int = 0x0040;
pub const MAP_ANON: crate::c_int = 0x0020;
pub const MAP_ANONYMOUS: crate::c_int = 0x0020;
pub const MAP_DENYWRITE: crate::c_int = 0x0800;
pub const MAP_EXECUTABLE: crate::c_int = 0x01000;
pub const MAP_POPULATE: crate::c_int = 0x08000;
pub const MAP_NONBLOCK: crate::c_int = 0x010000;
pub const MAP_STACK: crate::c_int = 0x020000;
pub const MAP_HUGETLB: crate::c_int = 0x040000;
pub const MAP_GROWSDOWN: crate::c_int = 0x0100;
pub const MAP_SYNC: crate::c_int = 0x080000;
pub const EUCLEAN: crate::c_int = 117;
pub const ENOTNAM: crate::c_int = 118;
pub const ENAVAIL: crate::c_int = 119;
pub const EISNAM: crate::c_int = 120;
pub const EREMOTEIO: crate::c_int = 121;
pub const EDEADLK: crate::c_int = 35;
pub const ENAMETOOLONG: crate::c_int = 36;
pub const ENOLCK: crate::c_int = 37;
pub const ENOSYS: crate::c_int = 38;
pub const ENOTEMPTY: crate::c_int = 39;
pub const ELOOP: crate::c_int = 40;
pub const ENOMSG: crate::c_int = 42;
pub const EIDRM: crate::c_int = 43;
pub const ECHRNG: crate::c_int = 44;
pub const EL2NSYNC: crate::c_int = 45;
pub const EL3HLT: crate::c_int = 46;
pub const EL3RST: crate::c_int = 47;
pub const ELNRNG: crate::c_int = 48;
pub const EUNATCH: crate::c_int = 49;
pub const ENOCSI: crate::c_int = 50;
pub const EL2HLT: crate::c_int = 51;
pub const EBADE: crate::c_int = 52;
pub const EBADR: crate::c_int = 53;
pub const EXFULL: crate::c_int = 54;
pub const ENOANO: crate::c_int = 55;
pub const EBADRQC: crate::c_int = 56;
pub const EBADSLT: crate::c_int = 57;
pub const EMULTIHOP: crate::c_int = 72;
pub const EOVERFLOW: crate::c_int = 75;
pub const ENOTUNIQ: crate::c_int = 76;
pub const EBADFD: crate::c_int = 77;
pub const EBADMSG: crate::c_int = 74;
pub const EREMCHG: crate::c_int = 78;
pub const ELIBACC: crate::c_int = 79;
pub const ELIBBAD: crate::c_int = 80;
pub const ELIBSCN: crate::c_int = 81;
pub const ELIBMAX: crate::c_int = 82;
pub const ELIBEXEC: crate::c_int = 83;
pub const EILSEQ: crate::c_int = 84;
pub const ERESTART: crate::c_int = 85;
pub const ESTRPIPE: crate::c_int = 86;
pub const EUSERS: crate::c_int = 87;
pub const ENOTSOCK: crate::c_int = 88;
pub const EDESTADDRREQ: crate::c_int = 89;
pub const EMSGSIZE: crate::c_int = 90;
pub const EPROTOTYPE: crate::c_int = 91;
pub const ENOPROTOOPT: crate::c_int = 92;
pub const EPROTONOSUPPORT: crate::c_int = 93;
pub const ESOCKTNOSUPPORT: crate::c_int = 94;
pub const EOPNOTSUPP: crate::c_int = 95;
pub const EPFNOSUPPORT: crate::c_int = 96;
pub const EAFNOSUPPORT: crate::c_int = 97;
pub const EADDRINUSE: crate::c_int = 98;
pub const EADDRNOTAVAIL: crate::c_int = 99;
pub const ENETDOWN: crate::c_int = 100;
pub const ENETUNREACH: crate::c_int = 101;
pub const ENETRESET: crate::c_int = 102;
pub const ECONNABORTED: crate::c_int = 103;
pub const ECONNRESET: crate::c_int = 104;
pub const ENOBUFS: crate::c_int = 105;
pub const EISCONN: crate::c_int = 106;
pub const ENOTCONN: crate::c_int = 107;
pub const ESHUTDOWN: crate::c_int = 108;
pub const ETOOMANYREFS: crate::c_int = 109;
pub const ETIMEDOUT: crate::c_int = 110;
pub const ECONNREFUSED: crate::c_int = 111;
pub const EHOSTDOWN: crate::c_int = 112;
pub const EHOSTUNREACH: crate::c_int = 113;
pub const EALREADY: crate::c_int = 114;
pub const EINPROGRESS: crate::c_int = 115;
pub const ESTALE: crate::c_int = 116;
pub const EDQUOT: crate::c_int = 122;
pub const ENOMEDIUM: crate::c_int = 123;
pub const EMEDIUMTYPE: crate::c_int = 124;
pub const ECANCELED: crate::c_int = 125;
pub const ENOKEY: crate::c_int = 126;
pub const EKEYEXPIRED: crate::c_int = 127;
pub const EKEYREVOKED: crate::c_int = 128;
pub const EKEYREJECTED: crate::c_int = 129;
pub const EOWNERDEAD: crate::c_int = 130;
pub const ENOTRECOVERABLE: crate::c_int = 131;
pub const EHWPOISON: crate::c_int = 133;
pub const ERFKILL: crate::c_int = 132;
pub const SA_NOCLDSTOP: crate::c_ulong = 0x1;
pub const SA_NOCLDWAIT: crate::c_ulong = 0x2;
pub const SA_SIGINFO: crate::c_ulong = 0x4;
pub const SA_NODEFER: crate::c_ulong = 0x40000000;
pub const SOCK_STREAM: crate::c_int = 1;
pub const SOCK_DGRAM: crate::c_int = 2;
pub const PTRACE_SYSEMU: crate::c_uint = 31;
pub const PTRACE_SYSEMU_SINGLESTEP: crate::c_uint = 32;
pub const POLLWRNORM: crate::c_short = 0x100;
pub const POLLWRBAND: crate::c_short = 0x200;
pub const EFD_NONBLOCK: crate::c_int = 0x800;
pub const SFD_NONBLOCK: crate::c_int = 0x0800;
pub const SIGCHLD: crate::c_int = 17;
pub const SIGBUS: crate::c_int = 7;
pub const SIGUSR1: crate::c_int = 10;
pub const SIGUSR2: crate::c_int = 12;
pub const SIGCONT: crate::c_int = 18;
pub const SIGSTOP: crate::c_int = 19;
pub const SIGTSTP: crate::c_int = 20;
pub const SIGURG: crate::c_int = 23;
pub const SIGSYS: crate::c_int = 31;
pub const SIGSTKFLT: crate::c_int = 16;
pub const SIGUNUSED: crate::c_int = 31;
pub const SIGPWR: crate::c_int = 30;
pub const SIG_SETMASK: crate::c_int = 2;
pub const SIG_BLOCK: crate::c_int = 0x000000;
pub const SIG_UNBLOCK: crate::c_int = 0x01;
pub const SIGTTIN: crate::c_int = 21;
pub const SIGTTOU: crate::c_int = 22;
pub const SIGXCPU: crate::c_int = 24;
pub const SIGXFSZ: crate::c_int = 25;
pub const SIGVTALRM: crate::c_int = 26;
pub const SIGPROF: crate::c_int = 27;
pub const SIGWINCH: crate::c_int = 28;
pub const SIGSTKSZ: crate::size_t = 8192;
pub const CBAUD: crate::tcflag_t = 0o0010017;
pub const TAB1: crate::tcflag_t = 0x00000800;
pub const TAB2: crate::tcflag_t = 0x00001000;
pub const TAB3: crate::tcflag_t = 0x00001800;
pub const CR1: crate::tcflag_t = 0x00000200;
pub const CR2: crate::tcflag_t = 0x00000400;
pub const CR3: crate::tcflag_t = 0x00000600;
pub const FF1: crate::tcflag_t = 0x00008000;
pub const BS1: crate::tcflag_t = 0x00002000;
pub const VT1: crate::tcflag_t = 0x00004000;
pub const VWERASE: usize = 14;
pub const VREPRINT: usize = 12;
pub const VSUSP: usize = 10;
pub const VSTART: usize = 8;
pub const VSTOP: usize = 9;
pub const VDISCARD: usize = 13;
pub const VTIME: usize = 5;
pub const IXON: crate::tcflag_t = 0x00000400;
pub const IXOFF: crate::tcflag_t = 0x00001000;
pub const ONLCR: crate::tcflag_t = 0x4;
pub const CSIZE: crate::tcflag_t = 0x00000030;
pub const CS6: crate::tcflag_t = 0x00000010;
pub const CS7: crate::tcflag_t = 0x00000020;
pub const CS8: crate::tcflag_t = 0x00000030;
pub const CSTOPB: crate::tcflag_t = 0x00000040;
pub const CREAD: crate::tcflag_t = 0x00000080;
pub const PARENB: crate::tcflag_t = 0x00000100;
pub const PARODD: crate::tcflag_t = 0x00000200;
pub const HUPCL: crate::tcflag_t = 0x00000400;
pub const CLOCAL: crate::tcflag_t = 0x00000800;
pub const ECHOKE: crate::tcflag_t = 0x00000800;
pub const ECHOE: crate::tcflag_t = 0x00000010;
pub const ECHOK: crate::tcflag_t = 0x00000020;
pub const ECHONL: crate::tcflag_t = 0x00000040;
pub const ECHOPRT: crate::tcflag_t = 0x00000400;
pub const ECHOCTL: crate::tcflag_t = 0x00000200;
pub const ISIG: crate::tcflag_t = 0x00000001;
pub const ICANON: crate::tcflag_t = 0x00000002;
pub const PENDIN: crate::tcflag_t = 0x00004000;
pub const NOFLSH: crate::tcflag_t = 0x00000080;
pub const CIBAUD: crate::tcflag_t = 0o02003600000;
pub const CBAUDEX: crate::tcflag_t = 0o010000;
pub const VSWTC: usize = 7;
pub const OLCUC: crate::tcflag_t = 0o000002;
pub const NLDLY: crate::tcflag_t = 0o000400;
pub const CRDLY: crate::tcflag_t = 0o003000;
pub const TABDLY: crate::tcflag_t = 0o014000;
pub const BSDLY: crate::tcflag_t = 0o020000;
pub const FFDLY: crate::tcflag_t = 0o100000;
pub const VTDLY: crate::tcflag_t = 0o040000;
pub const XTABS: crate::tcflag_t = 0o014000;
pub const B0: crate::speed_t = 0o000000;
pub const B50: crate::speed_t = 0o000001;
pub const B75: crate::speed_t = 0o000002;
pub const B110: crate::speed_t = 0o000003;
pub const B134: crate::speed_t = 0o000004;
pub const B150: crate::speed_t = 0o000005;
pub const B200: crate::speed_t = 0o000006;
pub const B300: crate::speed_t = 0o000007;
pub const B600: crate::speed_t = 0o000010;
pub const B1200: crate::speed_t = 0o000011;
pub const B1800: crate::speed_t = 0o000012;
pub const B2400: crate::speed_t = 0o000013;
pub const B4800: crate::speed_t = 0o000014;
pub const B9600: crate::speed_t = 0o000015;
pub const EXTA: crate::speed_t = 0o000016;
pub const B57600: crate::speed_t = 0o010001;
pub const B115200: crate::speed_t = 0o010002;
pub const B230400: crate::speed_t = 0o010003;
pub const B460800: crate::speed_t = 0o010004;
pub const B500000: crate::speed_t = 0o010005;
pub const B576000: crate::speed_t = 0o010006;
pub const B921600: crate::speed_t = 0o010007;
pub const B1000000: crate::speed_t = 0o010010;
pub const B1152000: crate::speed_t = 0o010011;
pub const B1500000: crate::speed_t = 0o010012;
pub const B2000000: crate::speed_t = 0o010013;
pub const B2500000: crate::speed_t = 0o010014;
pub const B3000000: crate::speed_t = 0o010015;
pub const B3500000: crate::speed_t = 0o010016;
pub const B4000000: crate::speed_t = 0o010017;
pub const VEOL: usize = 11;
pub const VEOL2: usize = 16;
pub const VMIN: usize = 6;
pub const IEXTEN: crate::tcflag_t = 0x00008000;
pub const TOSTOP: crate::tcflag_t = 0x00000100;
pub const FLUSHO: crate::tcflag_t = 0x00001000;
pub const TCSANOW: crate::c_int = 0;
pub const TCSADRAIN: crate::c_int = 1;
pub const TCSAFLUSH: crate::c_int = 2;
pub const SYS_restart_syscall: crate::c_long = 0;
pub const SYS_exit: crate::c_long = 1;
pub const SYS_fork: crate::c_long = 2;
pub const SYS_read: crate::c_long = 3;
pub const SYS_write: crate::c_long = 4;
pub const SYS_open: crate::c_long = 5;
pub const SYS_close: crate::c_long = 6;
pub const SYS_waitpid: crate::c_long = 7;
pub const SYS_creat: crate::c_long = 8;
pub const SYS_link: crate::c_long = 9;
pub const SYS_unlink: crate::c_long = 10;
pub const SYS_execve: crate::c_long = 11;
pub const SYS_chdir: crate::c_long = 12;
pub const SYS_time: crate::c_long = 13;
pub const SYS_mknod: crate::c_long = 14;
pub const SYS_chmod: crate::c_long = 15;
pub const SYS_lchown: crate::c_long = 16;
pub const SYS_break: crate::c_long = 17;
pub const SYS_oldstat: crate::c_long = 18;
pub const SYS_lseek: crate::c_long = 19;
pub const SYS_getpid: crate::c_long = 20;
pub const SYS_mount: crate::c_long = 21;
pub const SYS_umount: crate::c_long = 22;
pub const SYS_setuid: crate::c_long = 23;
pub const SYS_getuid: crate::c_long = 24;
pub const SYS_stime: crate::c_long = 25;
pub const SYS_ptrace: crate::c_long = 26;
pub const SYS_alarm: crate::c_long = 27;
pub const SYS_oldfstat: crate::c_long = 28;
pub const SYS_pause: crate::c_long = 29;
pub const SYS_utime: crate::c_long = 30;
pub const SYS_stty: crate::c_long = 31;
pub const SYS_gtty: crate::c_long = 32;
pub const SYS_access: crate::c_long = 33;
pub const SYS_nice: crate::c_long = 34;
pub const SYS_ftime: crate::c_long = 35;
pub const SYS_sync: crate::c_long = 36;
pub const SYS_kill: crate::c_long = 37;
pub const SYS_rename: crate::c_long = 38;
pub const SYS_mkdir: crate::c_long = 39;
pub const SYS_rmdir: crate::c_long = 40;
pub const SYS_dup: crate::c_long = 41;
pub const SYS_pipe: crate::c_long = 42;
pub const SYS_times: crate::c_long = 43;
pub const SYS_prof: crate::c_long = 44;
pub const SYS_brk: crate::c_long = 45;
pub const SYS_setgid: crate::c_long = 46;
pub const SYS_getgid: crate::c_long = 47;
pub const SYS_signal: crate::c_long = 48;
pub const SYS_geteuid: crate::c_long = 49;
pub const SYS_getegid: crate::c_long = 50;
pub const SYS_acct: crate::c_long = 51;
pub const SYS_umount2: crate::c_long = 52;
pub const SYS_lock: crate::c_long = 53;
pub const SYS_ioctl: crate::c_long = 54;
pub const SYS_fcntl: crate::c_long = 55;
pub const SYS_mpx: crate::c_long = 56;
pub const SYS_setpgid: crate::c_long = 57;
pub const SYS_ulimit: crate::c_long = 58;
pub const SYS_oldolduname: crate::c_long = 59;
pub const SYS_umask: crate::c_long = 60;
pub const SYS_chroot: crate::c_long = 61;
pub const SYS_ustat: crate::c_long = 62;
pub const SYS_dup2: crate::c_long = 63;
pub const SYS_getppid: crate::c_long = 64;
pub const SYS_getpgrp: crate::c_long = 65;
pub const SYS_setsid: crate::c_long = 66;
pub const SYS_sigaction: crate::c_long = 67;
pub const SYS_sgetmask: crate::c_long = 68;
pub const SYS_ssetmask: crate::c_long = 69;
pub const SYS_setreuid: crate::c_long = 70;
pub const SYS_setregid: crate::c_long = 71;
pub const SYS_sigsuspend: crate::c_long = 72;
pub const SYS_sigpending: crate::c_long = 73;
pub const SYS_sethostname: crate::c_long = 74;
pub const SYS_setrlimit: crate::c_long = 75;
pub const SYS_getrlimit: crate::c_long = 76;
pub const SYS_getrusage: crate::c_long = 77;
pub const SYS_gettimeofday: crate::c_long = 78;
pub const SYS_settimeofday: crate::c_long = 79;
pub const SYS_getgroups: crate::c_long = 80;
pub const SYS_setgroups: crate::c_long = 81;
pub const SYS_select: crate::c_long = 82;
pub const SYS_symlink: crate::c_long = 83;
pub const SYS_oldlstat: crate::c_long = 84;
pub const SYS_readlink: crate::c_long = 85;
pub const SYS_uselib: crate::c_long = 86;
pub const SYS_swapon: crate::c_long = 87;
pub const SYS_reboot: crate::c_long = 88;
pub const SYS_readdir: crate::c_long = 89;
pub const SYS_mmap: crate::c_long = 90;
pub const SYS_munmap: crate::c_long = 91;
pub const SYS_truncate: crate::c_long = 92;
pub const SYS_ftruncate: crate::c_long = 93;
pub const SYS_fchmod: crate::c_long = 94;
pub const SYS_fchown: crate::c_long = 95;
pub const SYS_getpriority: crate::c_long = 96;
pub const SYS_setpriority: crate::c_long = 97;
pub const SYS_profil: crate::c_long = 98;
pub const SYS_statfs: crate::c_long = 99;
pub const SYS_fstatfs: crate::c_long = 100;
pub const SYS_ioperm: crate::c_long = 101;
pub const SYS_socketcall: crate::c_long = 102;
pub const SYS_syslog: crate::c_long = 103;
pub const SYS_setitimer: crate::c_long = 104;
pub const SYS_getitimer: crate::c_long = 105;
pub const SYS_stat: crate::c_long = 106;
pub const SYS_lstat: crate::c_long = 107;
pub const SYS_fstat: crate::c_long = 108;
pub const SYS_olduname: crate::c_long = 109;
pub const SYS_iopl: crate::c_long = 110;
pub const SYS_vhangup: crate::c_long = 111;
pub const SYS_idle: crate::c_long = 112;
pub const SYS_vm86old: crate::c_long = 113;
pub const SYS_wait4: crate::c_long = 114;
pub const SYS_swapoff: crate::c_long = 115;
pub const SYS_sysinfo: crate::c_long = 116;
pub const SYS_ipc: crate::c_long = 117;
pub const SYS_fsync: crate::c_long = 118;
pub const SYS_sigreturn: crate::c_long = 119;
pub const SYS_clone: crate::c_long = 120;
pub const SYS_setdomainname: crate::c_long = 121;
pub const SYS_uname: crate::c_long = 122;
pub const SYS_modify_ldt: crate::c_long = 123;
pub const SYS_adjtimex: crate::c_long = 124;
pub const SYS_mprotect: crate::c_long = 125;
pub const SYS_sigprocmask: crate::c_long = 126;
pub const SYS_create_module: crate::c_long = 127;
pub const SYS_init_module: crate::c_long = 128;
pub const SYS_delete_module: crate::c_long = 129;
pub const SYS_get_kernel_syms: crate::c_long = 130;
pub const SYS_quotactl: crate::c_long = 131;
pub const SYS_getpgid: crate::c_long = 132;
pub const SYS_fchdir: crate::c_long = 133;
pub const SYS_bdflush: crate::c_long = 134;
pub const SYS_sysfs: crate::c_long = 135;
pub const SYS_personality: crate::c_long = 136;
pub const SYS_afs_syscall: crate::c_long = 137;
pub const SYS_setfsuid: crate::c_long = 138;
pub const SYS_setfsgid: crate::c_long = 139;
pub const SYS__llseek: crate::c_long = 140;
pub const SYS_getdents: crate::c_long = 141;
pub const SYS__newselect: crate::c_long = 142;
pub const SYS_flock: crate::c_long = 143;
pub const SYS_msync: crate::c_long = 144;
pub const SYS_readv: crate::c_long = 145;
pub const SYS_writev: crate::c_long = 146;
pub const SYS_getsid: crate::c_long = 147;
pub const SYS_fdatasync: crate::c_long = 148;
pub const SYS__sysctl: crate::c_long = 149;
pub const SYS_mlock: crate::c_long = 150;
pub const SYS_munlock: crate::c_long = 151;
pub const SYS_mlockall: crate::c_long = 152;
pub const SYS_munlockall: crate::c_long = 153;
pub const SYS_sched_setparam: crate::c_long = 154;
pub const SYS_sched_getparam: crate::c_long = 155;
pub const SYS_sched_setscheduler: crate::c_long = 156;
pub const SYS_sched_getscheduler: crate::c_long = 157;
pub const SYS_sched_yield: crate::c_long = 158;
pub const SYS_sched_get_priority_max: crate::c_long = 159;
pub const SYS_sched_get_priority_min: crate::c_long = 160;
pub const SYS_sched_rr_get_interval: crate::c_long = 161;
pub const SYS_nanosleep: crate::c_long = 162;
pub const SYS_mremap: crate::c_long = 163;
pub const SYS_setresuid: crate::c_long = 164;
pub const SYS_getresuid: crate::c_long = 165;
pub const SYS_vm86: crate::c_long = 166;
pub const SYS_query_module: crate::c_long = 167;
pub const SYS_poll: crate::c_long = 168;
pub const SYS_nfsservctl: crate::c_long = 169;
pub const SYS_setresgid: crate::c_long = 170;
pub const SYS_getresgid: crate::c_long = 171;
pub const SYS_prctl: crate::c_long = 172;
pub const SYS_rt_sigreturn: crate::c_long = 173;
pub const SYS_rt_sigaction: crate::c_long = 174;
pub const SYS_rt_sigprocmask: crate::c_long = 175;
pub const SYS_rt_sigpending: crate::c_long = 176;
pub const SYS_rt_sigtimedwait: crate::c_long = 177;
pub const SYS_rt_sigqueueinfo: crate::c_long = 178;
pub const SYS_rt_sigsuspend: crate::c_long = 179;
pub const SYS_pread64: crate::c_long = 180;
pub const SYS_pwrite64: crate::c_long = 181;
pub const SYS_chown: crate::c_long = 182;
pub const SYS_getcwd: crate::c_long = 183;
pub const SYS_capget: crate::c_long = 184;
pub const SYS_capset: crate::c_long = 185;
pub const SYS_sigaltstack: crate::c_long = 186;
pub const SYS_sendfile: crate::c_long = 187;
pub const SYS_getpmsg: crate::c_long = 188;
pub const SYS_putpmsg: crate::c_long = 189;
pub const SYS_vfork: crate::c_long = 190;
pub const SYS_ugetrlimit: crate::c_long = 191;
pub const SYS_mmap2: crate::c_long = 192;
pub const SYS_truncate64: crate::c_long = 193;
pub const SYS_ftruncate64: crate::c_long = 194;
pub const SYS_stat64: crate::c_long = 195;
pub const SYS_lstat64: crate::c_long = 196;
pub const SYS_fstat64: crate::c_long = 197;
pub const SYS_lchown32: crate::c_long = 198;
pub const SYS_getuid32: crate::c_long = 199;
pub const SYS_getgid32: crate::c_long = 200;
pub const SYS_geteuid32: crate::c_long = 201;
pub const SYS_getegid32: crate::c_long = 202;
pub const SYS_setreuid32: crate::c_long = 203;
pub const SYS_setregid32: crate::c_long = 204;
pub const SYS_getgroups32: crate::c_long = 205;
pub const SYS_setgroups32: crate::c_long = 206;
pub const SYS_fchown32: crate::c_long = 207;
pub const SYS_setresuid32: crate::c_long = 208;
pub const SYS_getresuid32: crate::c_long = 209;
pub const SYS_setresgid32: crate::c_long = 210;
pub const SYS_getresgid32: crate::c_long = 211;
pub const SYS_chown32: crate::c_long = 212;
pub const SYS_setuid32: crate::c_long = 213;
pub const SYS_setgid32: crate::c_long = 214;
pub const SYS_setfsuid32: crate::c_long = 215;
pub const SYS_setfsgid32: crate::c_long = 216;
pub const SYS_pivot_root: crate::c_long = 217;
pub const SYS_mincore: crate::c_long = 218;
pub const SYS_madvise: crate::c_long = 219;
pub const SYS_getdents64: crate::c_long = 220;
pub const SYS_fcntl64: crate::c_long = 221;
pub const SYS_gettid: crate::c_long = 224;
pub const SYS_readahead: crate::c_long = 225;
pub const SYS_setxattr: crate::c_long = 226;
pub const SYS_lsetxattr: crate::c_long = 227;
pub const SYS_fsetxattr: crate::c_long = 228;
pub const SYS_getxattr: crate::c_long = 229;
pub const SYS_lgetxattr: crate::c_long = 230;
pub const SYS_fgetxattr: crate::c_long = 231;
pub const SYS_listxattr: crate::c_long = 232;
pub const SYS_llistxattr: crate::c_long = 233;
pub const SYS_flistxattr: crate::c_long = 234;
pub const SYS_removexattr: crate::c_long = 235;
pub const SYS_lremovexattr: crate::c_long = 236;
pub const SYS_fremovexattr: crate::c_long = 237;
pub const SYS_tkill: crate::c_long = 238;
pub const SYS_sendfile64: crate::c_long = 239;
pub const SYS_futex: crate::c_long = 240;
pub const SYS_sched_setaffinity: crate::c_long = 241;
pub const SYS_sched_getaffinity: crate::c_long = 242;
pub const SYS_set_thread_area: crate::c_long = 243;
pub const SYS_get_thread_area: crate::c_long = 244;
pub const SYS_io_setup: crate::c_long = 245;
pub const SYS_io_destroy: crate::c_long = 246;
pub const SYS_io_getevents: crate::c_long = 247;
pub const SYS_io_submit: crate::c_long = 248;
pub const SYS_io_cancel: crate::c_long = 249;
pub const SYS_fadvise64: crate::c_long = 250;
pub const SYS_exit_group: crate::c_long = 252;
pub const SYS_lookup_dcookie: crate::c_long = 253;
pub const SYS_epoll_create: crate::c_long = 254;
pub const SYS_epoll_ctl: crate::c_long = 255;
pub const SYS_epoll_wait: crate::c_long = 256;
pub const SYS_remap_file_pages: crate::c_long = 257;
pub const SYS_set_tid_address: crate::c_long = 258;
pub const SYS_timer_create: crate::c_long = 259;
pub const SYS_timer_settime: crate::c_long = 260;
pub const SYS_timer_gettime: crate::c_long = 261;
pub const SYS_timer_getoverrun: crate::c_long = 262;
pub const SYS_timer_delete: crate::c_long = 263;
pub const SYS_clock_settime: crate::c_long = 264;
pub const SYS_clock_gettime: crate::c_long = 265;
pub const SYS_clock_getres: crate::c_long = 266;
pub const SYS_clock_nanosleep: crate::c_long = 267;
pub const SYS_statfs64: crate::c_long = 268;
pub const SYS_fstatfs64: crate::c_long = 269;
pub const SYS_tgkill: crate::c_long = 270;
pub const SYS_utimes: crate::c_long = 271;
pub const SYS_fadvise64_64: crate::c_long = 272;
pub const SYS_vserver: crate::c_long = 273;
pub const SYS_mbind: crate::c_long = 274;
pub const SYS_get_mempolicy: crate::c_long = 275;
pub const SYS_set_mempolicy: crate::c_long = 276;
pub const SYS_mq_open: crate::c_long = 277;
pub const SYS_mq_unlink: crate::c_long = 278;
pub const SYS_mq_timedsend: crate::c_long = 279;
pub const SYS_mq_timedreceive: crate::c_long = 280;
pub const SYS_mq_notify: crate::c_long = 281;
pub const SYS_mq_getsetattr: crate::c_long = 282;
pub const SYS_kexec_load: crate::c_long = 283;
pub const SYS_waitid: crate::c_long = 284;
pub const SYS_add_key: crate::c_long = 286;
pub const SYS_request_key: crate::c_long = 287;
pub const SYS_keyctl: crate::c_long = 288;
pub const SYS_ioprio_set: crate::c_long = 289;
pub const SYS_ioprio_get: crate::c_long = 290;
pub const SYS_inotify_init: crate::c_long = 291;
pub const SYS_inotify_add_watch: crate::c_long = 292;
pub const SYS_inotify_rm_watch: crate::c_long = 293;
pub const SYS_migrate_pages: crate::c_long = 294;
pub const SYS_openat: crate::c_long = 295;
pub const SYS_mkdirat: crate::c_long = 296;
pub const SYS_mknodat: crate::c_long = 297;
pub const SYS_fchownat: crate::c_long = 298;
pub const SYS_futimesat: crate::c_long = 299;
pub const SYS_fstatat64: crate::c_long = 300;
pub const SYS_unlinkat: crate::c_long = 301;
pub const SYS_renameat: crate::c_long = 302;
pub const SYS_linkat: crate::c_long = 303;
pub const SYS_symlinkat: crate::c_long = 304;
pub const SYS_readlinkat: crate::c_long = 305;
pub const SYS_fchmodat: crate::c_long = 306;
pub const SYS_faccessat: crate::c_long = 307;
pub const SYS_pselect6: crate::c_long = 308;
pub const SYS_ppoll: crate::c_long = 309;
pub const SYS_unshare: crate::c_long = 310;
pub const SYS_set_robust_list: crate::c_long = 311;
pub const SYS_get_robust_list: crate::c_long = 312;
pub const SYS_splice: crate::c_long = 313;
pub const SYS_sync_file_range: crate::c_long = 314;
pub const SYS_tee: crate::c_long = 315;
pub const SYS_vmsplice: crate::c_long = 316;
pub const SYS_move_pages: crate::c_long = 317;
pub const SYS_getcpu: crate::c_long = 318;
pub const SYS_epoll_pwait: crate::c_long = 319;
pub const SYS_utimensat: crate::c_long = 320;
pub const SYS_signalfd: crate::c_long = 321;
pub const SYS_timerfd_create: crate::c_long = 322;
pub const SYS_eventfd: crate::c_long = 323;
pub const SYS_fallocate: crate::c_long = 324;
pub const SYS_timerfd_settime: crate::c_long = 325;
pub const SYS_timerfd_gettime: crate::c_long = 326;
pub const SYS_signalfd4: crate::c_long = 327;
pub const SYS_eventfd2: crate::c_long = 328;
pub const SYS_epoll_create1: crate::c_long = 329;
pub const SYS_dup3: crate::c_long = 330;
pub const SYS_pipe2: crate::c_long = 331;
pub const SYS_inotify_init1: crate::c_long = 332;
pub const SYS_preadv: crate::c_long = 333;
pub const SYS_pwritev: crate::c_long = 334;
pub const SYS_rt_tgsigqueueinfo: crate::c_long = 335;
pub const SYS_perf_event_open: crate::c_long = 336;
pub const SYS_recvmmsg: crate::c_long = 337;
pub const SYS_fanotify_init: crate::c_long = 338;
pub const SYS_fanotify_mark: crate::c_long = 339;
pub const SYS_prlimit64: crate::c_long = 340;
pub const SYS_name_to_handle_at: crate::c_long = 341;
pub const SYS_open_by_handle_at: crate::c_long = 342;
pub const SYS_clock_adjtime: crate::c_long = 343;
pub const SYS_syncfs: crate::c_long = 344;
pub const SYS_sendmmsg: crate::c_long = 345;
pub const SYS_setns: crate::c_long = 346;
pub const SYS_process_vm_readv: crate::c_long = 347;
pub const SYS_process_vm_writev: crate::c_long = 348;
pub const SYS_kcmp: crate::c_long = 349;
pub const SYS_finit_module: crate::c_long = 350;
pub const SYS_sched_setattr: crate::c_long = 351;
pub const SYS_sched_getattr: crate::c_long = 352;
pub const SYS_renameat2: crate::c_long = 353;
pub const SYS_seccomp: crate::c_long = 354;
pub const SYS_getrandom: crate::c_long = 355;
pub const SYS_memfd_create: crate::c_long = 356;
pub const SYS_bpf: crate::c_long = 357;
pub const SYS_execveat: crate::c_long = 358;
pub const SYS_socket: crate::c_long = 359;
pub const SYS_socketpair: crate::c_long = 360;
pub const SYS_bind: crate::c_long = 361;
pub const SYS_connect: crate::c_long = 362;
pub const SYS_listen: crate::c_long = 363;
pub const SYS_accept4: crate::c_long = 364;
pub const SYS_getsockopt: crate::c_long = 365;
pub const SYS_setsockopt: crate::c_long = 366;
pub const SYS_getsockname: crate::c_long = 367;
pub const SYS_getpeername: crate::c_long = 368;
pub const SYS_sendto: crate::c_long = 369;
pub const SYS_sendmsg: crate::c_long = 370;
pub const SYS_recvfrom: crate::c_long = 371;
pub const SYS_recvmsg: crate::c_long = 372;
pub const SYS_shutdown: crate::c_long = 373;
pub const SYS_userfaultfd: crate::c_long = 374;
pub const SYS_membarrier: crate::c_long = 375;
pub const SYS_mlock2: crate::c_long = 376;
pub const SYS_copy_file_range: crate::c_long = 377;
pub const SYS_preadv2: crate::c_long = 378;
pub const SYS_pwritev2: crate::c_long = 379;
pub const SYS_pkey_mprotect: crate::c_long = 380;
pub const SYS_pkey_alloc: crate::c_long = 381;
pub const SYS_pkey_free: crate::c_long = 382;
pub const SYS_statx: crate::c_long = 383;
pub const SYS_rseq: crate::c_long = 386;
pub const SYS_pidfd_send_signal: crate::c_long = 424;
pub const SYS_io_uring_setup: crate::c_long = 425;
pub const SYS_io_uring_enter: crate::c_long = 426;
pub const SYS_io_uring_register: crate::c_long = 427;
pub const SYS_open_tree: crate::c_long = 428;
pub const SYS_move_mount: crate::c_long = 429;
pub const SYS_fsopen: crate::c_long = 430;
pub const SYS_fsconfig: crate::c_long = 431;
pub const SYS_fsmount: crate::c_long = 432;
pub const SYS_fspick: crate::c_long = 433;
pub const SYS_pidfd_open: crate::c_long = 434;
pub const SYS_clone3: crate::c_long = 435;
pub const SYS_close_range: crate::c_long = 436;
pub const SYS_openat2: crate::c_long = 437;
pub const SYS_pidfd_getfd: crate::c_long = 438;
pub const SYS_faccessat2: crate::c_long = 439;
pub const SYS_process_madvise: crate::c_long = 440;
pub const SYS_epoll_pwait2: crate::c_long = 441;
pub const SYS_mount_setattr: crate::c_long = 442;
pub const SYS_quotactl_fd: crate::c_long = 443;
pub const SYS_landlock_create_ruleset: crate::c_long = 444;
pub const SYS_landlock_add_rule: crate::c_long = 445;
pub const SYS_landlock_restrict_self: crate::c_long = 446;
pub const SYS_memfd_secret: crate::c_long = 447;
pub const SYS_process_mrelease: crate::c_long = 448;
pub const SYS_futex_waitv: crate::c_long = 449;
pub const SYS_set_mempolicy_home_node: crate::c_long = 450;
pub const SYS_fchmodat2: crate::c_long = 452;
pub const SYS_mseal: crate::c_long = 462;
pub const EBX: crate::c_int = 0;
pub const ECX: crate::c_int = 1;
pub const EDX: crate::c_int = 2;
pub const ESI: crate::c_int = 3;
pub const EDI: crate::c_int = 4;
pub const EBP: crate::c_int = 5;
pub const EAX: crate::c_int = 6;
pub const DS: crate::c_int = 7;
pub const ES: crate::c_int = 8;
pub const FS: crate::c_int = 9;
pub const GS: crate::c_int = 10;
pub const ORIG_EAX: crate::c_int = 11;
pub const EIP: crate::c_int = 12;
pub const CS: crate::c_int = 13;
pub const EFL: crate::c_int = 14;
pub const UESP: crate::c_int = 15;
pub const SS: crate::c_int = 16;
pub const REG_GS: crate::c_int = 0;
pub const REG_FS: crate::c_int = 1;
pub const REG_ES: crate::c_int = 2;
pub const REG_DS: crate::c_int = 3;
pub const REG_EDI: crate::c_int = 4;
pub const REG_ESI: crate::c_int = 5;
pub const REG_EBP: crate::c_int = 6;
pub const REG_ESP: crate::c_int = 7;
pub const REG_EBX: crate::c_int = 8;
pub const REG_EDX: crate::c_int = 9;
pub const REG_ECX: crate::c_int = 10;
pub const REG_EAX: crate::c_int = 11;
pub const REG_TRAPNO: crate::c_int = 12;
pub const REG_ERR: crate::c_int = 13;
pub const REG_EIP: crate::c_int = 14;
pub const REG_CS: crate::c_int = 15;
pub const REG_EFL: crate::c_int = 16;
pub const REG_UESP: crate::c_int = 17;
pub const REG_SS: crate::c_int = 18;

pub const ENODATA: crate::c_int = 0x3d;
pub const O_CLOEXEC: crate::c_int = 0x80000;
pub const __SIZEOF_PTHREAD_BARRIERATTR_T: usize = 4;
pub const __SIZEOF_PTHREAD_BARRIER_T: usize = 32;
pub const __SIZEOF_PTHREAD_CONDATTR_T: usize = 4;
pub const __SIZEOF_PTHREAD_MUTEXATTR_T: usize = 4;
pub const __SIZEOF_PTHREAD_MUTEX_T: usize = 40;
pub const __SIZEOF_PTHREAD_RWLOCKATTR_T: usize = 8;
pub const __SIZEOF_PTHREAD_RWLOCK_T: usize = 56;
pub const PTHREAD_STACK_MIN: usize = 16384;
pub const NCCS: usize = 32;

pub const O_ACCMODE: crate::c_int = 0o003;
pub const O_TRUNC: crate::c_int = 0o1000;
pub const SA_ONSTACK: crate::c_ulong = 0x08000000;
pub const SA_RESETHAND: crate::c_ulong = 0x80000000;
pub const SA_RESTART: crate::c_ulong = 0x10000000;
pub const SOCK_SEQPACKET: crate::c_int = 5;
pub const SOCK_NONBLOCK: crate::c_int = 0o4000;
pub const SOCK_CLOEXEC: crate::c_int = 0x80000;
pub const EPOLL_CLOEXEC: crate::c_int = 0x80000;
pub const EFD_CLOEXEC: crate::c_int = 0x80000;
pub const SFD_CLOEXEC: crate::c_int = 0x80000;
pub const EADV: crate::c_int = 68;
pub const EBFONT: crate::c_int = 59;
pub const ECOMM: crate::c_int = 70;
pub const EDOTDOT: crate::c_int = 73;
pub const ENOLINK: crate::c_int = 67;
pub const ENONET: crate::c_int = 64;
pub const ENOPKG: crate::c_int = 65;
pub const ENOSR: crate::c_int = 63;
pub const ENOSTR: crate::c_int = 60;
pub const EPROTO: crate::c_int = 71;
pub const EREMOTE: crate::c_int = 66;
pub const ESRMNT: crate::c_int = 69;
pub const ETIME: crate::c_int = 62;
pub const F_GETLK: crate::c_int = 5;
pub const F_SETLK: crate::c_int = 6;
pub const F_SETLKW: crate::c_int = 7;
pub const O_NOATIME: crate::c_int = 0o1000000;
pub const O_PATH: crate::c_int = 0o10000000;

// cpu_set_t, CPU_ISSET and sched_getaffinity come from linux_l4re_shared;
// only the per-arch CPU_SETSIZE is missing on uClibc x86.
pub const CPU_SETSIZE: crate::c_int = 0x400;

extern "C" {
    pub fn getcontext(ucp: *mut ucontext_t) -> crate::c_int;
    pub fn setcontext(ucp: *const ucontext_t) -> crate::c_int;
    pub fn makecontext(ucp: *mut ucontext_t, func: extern "C" fn(), argc: crate::c_int, ...);
    pub fn swapcontext(uocp: *mut ucontext_t, ucp: *const ucontext_t) -> crate::c_int;
}
