#!/usr/bin/env python3
"""Patch yazi workspace source to replace AtomicU64 with AtomicU32/Mutex for MIPS uClibc."""

import sys, os

yazi_dir = sys.argv[1] if len(sys.argv) > 1 else '.'

def patch_file(path, replacements):
    with open(path) as f:
        c = f.read()
    for old, new in replacements:
        c = c.replace(old, new)
    with open(path, 'w') as f:
        f.write(c)
    print(f'  Patched {os.path.relpath(path, yazi_dir)}')

print(f'Patching yazi workspace under {yazi_dir}...')

# 1. yazi-shared/src/id.rs: AtomicU64 -> AtomicU32 (counter fits 32-bit)
patch_file(f'{yazi_dir}/yazi-shared/src/id.rs', [
    ('AtomicU64', 'AtomicU32'),
    ('Id(self.next.load(Ordering::Relaxed))', 'Id(self.next.load(Ordering::Relaxed) as u64)'),
    ('return Id(old);', 'return Id(old as u64);'),
])

# 2. yazi-shared/src/throttle.rs: AtomicU64 -> std::sync::Mutex<u64> (timestamp can exceed u32)
patch_file(f'{yazi_dir}/yazi-shared/src/throttle.rs', [
    (
        'use std::{fmt::Debug, mem, sync::atomic::{AtomicU64, AtomicUsize, Ordering}, time::Duration}',
        'use std::{fmt::Debug, mem, sync::atomic::{AtomicUsize, Ordering}, time::Duration}; use parking_lot::Mutex',
    ),
    ('last:     AtomicU64,', 'last:     std::sync::Mutex<u64>,'),
    ('last: AtomicU64::new(timestamp_us() - interval.as_micros() as u64),', 'last: std::sync::Mutex::new(timestamp_us() - interval.as_micros() as u64),'),
    ('let last = self.last.load(Ordering::Relaxed);', 'let last = *self.last.lock().unwrap();'),
    ('self.last.store(now, Ordering::Relaxed);', '*self.last.lock().unwrap() = now;'),
    ('use parking_lot::Mutex}', 'use parking_lot::Mutex;'),
    ('\n\nuse parking_lot::Mutex;\n\nuse crate::timestamp_us;', '\n\nuse crate::timestamp_us;'),
    ('\n\nuse parking_lot::Mutex;\nuse crate::timestamp_us;', '\n\nuse crate::timestamp_us;'),
])

# 3. yazi-vfs/src/provider/copier.rs: AtomicU64 -> AtomicU32 (byte counter fits 32-bit)
#     n must stay u64 for progress reporting via prog_tx.channel, only cast to u32 for fetch_add
patch_file(f'{yazi_dir}/yazi-vfs/src/provider/copier.rs', [
    ('AtomicU64', 'AtomicU32'),
    ('self.acc.fetch_add(n as u64, Ordering::SeqCst);', 'self.acc.fetch_add(n as u32, Ordering::SeqCst);'),
])

# 4. yazi-dds/src/state.rs: AtomicU64 timestamp -> std::sync::Mutex<u64>
patch_file(f'{yazi_dir}/yazi-dds/src/state.rs', [
    ('use std::{mem, ops::Deref, sync::atomic::{AtomicU64, Ordering}}', 'use std::{mem, ops::Deref, sync::atomic::Ordering, sync::Mutex}'),
    ('last:  AtomicU64,', 'last:  Mutex<u64>,'),
    ('self.last.store(timestamp_us(), Ordering::Relaxed)', '*self.last.lock().unwrap() = timestamp_us()'),
    ('self.last.load(Ordering::Relaxed)', '*self.last.lock().unwrap()'),
])

# 5. yazi-scheduler/src/behavior.rs: AtomicU64 -> AtomicU32 (ID counter fits 32-bit)
patch_file(f'{yazi_dir}/yazi-scheduler/src/behavior.rs', [
    ('use std::sync::atomic::{AtomicU64, Ordering}', 'use std::sync::atomic::{AtomicU32, Ordering}'),
    ('AtomicU64', 'AtomicU32'),
    ('self.first_id.load(Ordering::Relaxed).into()', '(self.first_id.load(Ordering::Relaxed) as u64).into()'),
    ('id.get()),', 'id.get() as u32),'),
])

print('Done patching yazi workspace AtomicU64 -> AtomicU32/Mutex.')
