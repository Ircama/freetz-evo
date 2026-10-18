fn main() {
    let directory = rustix_linux_procfs::proc_self_fd().expect("validated procfs directory");
    let filesystem = rustix::fs::fstatfs(directory).expect("procfs statfs");
    assert_eq!(filesystem.f_type as u64, 0x9fa0);
    let _fdinfo = rustix_linux_procfs::proc_self_fdinfo_fd(directory).expect("validated fdinfo");
    let _maps = rustix_linux_procfs::proc_self_maps().expect("validated maps");
    let _status = rustix_linux_procfs::proc_self_status().expect("validated status");
    println!("procfs_identity_and_validated_files_ok");
}
