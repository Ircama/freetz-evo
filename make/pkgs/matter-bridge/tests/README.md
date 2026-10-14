# matter-bridge tests

## Native Controller Integration

The daemon is `controller/src/server.rs`, built on rs-matter. Run the native
end-to-end test with isolated stores:

```sh
python3 make/pkgs/matter-bridge/tests/native-controller-test.py \
  --server /path/to/host/matter-bridge --device /path/to/host/light_tests
python3 make/pkgs/matter-bridge/tests/native-controller-test.py \
  --server /path/to/host/matter-bridge --device /path/to/host/freetz-matter --freetz
```

The test checks automatic local PASE/CASE, interview, OnOff/level, delayed
subscription reports, read/write and restart with unchanged fabric. The
freetz variant checks the temperature and speaker endpoints too; physical
sensor/ALSA behavior needs router testing. The Python `websockets` dependency
is test-only and is not installed or required on the router.

Both sides of the test are host builds of the same sources that are
cross-compiled for MIPS (`controller/` for the bridge), so the protocol and the
controller logic under test are the ones that run on the box: the wire protocol
is identical for the host and the MIPS build.

