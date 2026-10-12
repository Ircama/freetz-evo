# matter-bridge tests

## Native Controller Integration

The active daemon is `controller/src/server.rs`, not the historical C++
frontend described below. Run the native end-to-end test with isolated stores:

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

## Historical Frontend Tests

Two protocol tests drive `matter-bridge` exactly like a real client would and can
be run on the development host, without a FRITZ!Box, because the sources build
natively as well.

## Why the host build is a valid test

`src/matter-bridge.cpp` only depends on `libwebsockets` and `jsoncpp`, both of
which are available on a normal Linux distribution, and the wire protocol is
identical for the host and the MIPS build. Testing on the host therefore
validates the same code that runs on the router.

## Preparation

```bash
# jsoncpp for the host, from the sources already downloaded by Freetz
JC=$PWD/source/target-mips_gcc-13.4.0_uClibc-1.0.59-nptl_kernel-4.9/jsoncpp-1.9.8
mkdir -p /tmp/mbhost && cd /tmp/mbhost
g++ -O2 -std=gnu++17 -I"$JC/include" -c "$JC"/src/lib_json/*.cpp
g++ -O2 -std=gnu++17 -I"$JC/include" -o mb-host \
    "$OLDPWD"/make/pkgs/matter-bridge/src/matter-bridge.cpp *.o \
    -lwebsockets -lcap -lpthread

# start it with the seed store shipped in the firmware
./mb-host -p 5599 -n /tmp/mb-state.json \
    -s /path/to/freetz-evo/make/pkgs/matter-bridge/files/root/etc/matter-bridge/nodes.json -v
```

## `conformance-python-matter-server.py`

Validates every message the bridge sends against the **reference implementation**:
it downloads the `python-matter-server` source distribution, imports its protocol
dataclasses (`matter_server.common.models`) and its constants
(`SCHEMA_VERSION`, `MIN_SCHEMA_VERSION`, the error-code enum) and checks that

* the first frame is a flat `ServerInfoMessage` with exactly the reference fields,
  `schema_version == 11` and `min_supported_schema_version == 9`;
* replies parse as `SuccessResultMessage` / `ErrorResultMessage`;
* events parse as `EventMessage` with a known `EventType` and the positional
  `[node_id, "endpoint/cluster/attribute", value]` payload;
* error codes follow the reference enum (`5` NodeNotExists, `8` InvalidArguments,
  `9` InvalidCommand);
* every frame carries exactly one JSON document, even after 20+ exchanges.

```bash
pip download python-matter-server --no-deps --no-binary :all: -d /tmp/pms
tar -C /tmp/pms -xzf /tmp/pms/python_matter_server-*.tar.gz   # adjust PMS in the script
python3 conformance-python-matter-server.py 5599
```

## `domoticz-driver-test.py`

Replays the sequence of the Domoticz Matter driver
(`hardware/Matter.cpp`): connects to `ws://host:port/ws`, requires the top-level
`sdk_version` handshake, sends `start_listening`, `device_command` for the
`OnOff` and `LevelControl` clusters (the exact argument layout used by
`sendOnOff`/`sendLevel`, including `MoveToLevelWithOnOff` with
`level`/`optionsMask`/`optionsOverride`/`transitionTime`) and `write_attribute`,
and verifies the `attribute_updated` events and the `error_code` replies.

## Expected output

Both scripts exit with status 0 and end with `RESULT: ALL ... PASSED`.
