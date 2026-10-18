use portable_atomic::AtomicU64;
use std::sync::{atomic::Ordering, Arc};

fn main() {
    let initial = u64::from(u32::MAX) + 8192;
    let counter = Arc::new(AtomicU64::new(initial));
    assert_eq!(counter.load(Ordering::Relaxed), initial);
    assert_eq!(counter.fetch_add(4096, Ordering::Relaxed), initial);
    assert_eq!(counter.fetch_sub(4096, Ordering::Relaxed), initial + 4096);
    let workers: Vec<_> = (0..4)
        .map(|_| {
            let counter = Arc::clone(&counter);
            std::thread::spawn(move || {
                for _ in 0..10000 {
                    counter.fetch_add(1, Ordering::Relaxed);
                }
            })
        })
        .collect();
    for worker in workers {
        worker.join().unwrap();
    }
    assert_eq!(counter.load(Ordering::Relaxed), initial + 40000);
    println!("atomic64_width_and_concurrency_ok value={} lock_free={}", counter.load(Ordering::Relaxed), AtomicU64::is_lock_free());
}