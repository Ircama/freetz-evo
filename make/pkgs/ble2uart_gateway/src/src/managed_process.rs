use std::path::PathBuf;
use std::process::Child;
use std::time::{Duration,Instant};

pub struct ManagedProcess {
    child: Child,
    cleanup: Option<PathBuf>,
}

impl ManagedProcess {
    pub fn new(child:Child,cleanup:Option<PathBuf>)->Self {Self {child,cleanup}}
}

impl Drop for ManagedProcess {
    fn drop(&mut self) {
        if self.child.try_wait().ok().flatten().is_none() {
            unsafe {libc::kill(self.child.id() as libc::pid_t,libc::SIGTERM);}
            let deadline=Instant::now()+Duration::from_secs(3);
            loop {
                if self.child.try_wait().ok().flatten().is_some(){break;}
                if Instant::now()>=deadline {let _=self.child.kill();let _=self.child.wait();break;}
                std::thread::sleep(Duration::from_millis(20));
            }
        }
        if let Some(path)=&self.cleanup {let _=std::fs::remove_file(path);}
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn owned_child_and_temporary_config_are_cleaned_on_drop() {
        let path=std::env::temp_dir().join(format!("ble-managed-process-{}",std::process::id()));
        std::fs::write(&path,b"test only").unwrap();
        let child=std::process::Command::new("/bin/cat").stdin(std::process::Stdio::piped()).stdout(std::process::Stdio::null()).spawn().unwrap();
        let identifier=child.id();
        let managed=ManagedProcess::new(child,Some(path.clone()));
        assert_eq!(unsafe{libc::kill(identifier as libc::pid_t,0)},0);
        drop(managed);
        assert!(!path.exists());
        assert_eq!(unsafe{libc::kill(identifier as libc::pid_t,0)},-1);
    }
}