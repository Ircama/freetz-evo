#!/usr/bin/env python3
"""Crypto test vectors for the Rust AES-CCM stage (development-time only).

The reference implements four tunnels (AtcMiCodec, MiLikeCodec, BtHomeCodec,
BtHomeV2Codec) with different nonces and AAD. This script *builds* encrypted
frames with the reference encoder and records:
  * `blob`    - the bytes as they appear in the advertisement
  * `payload` - what the tunnel must return after decryption
    * `mac`/`bindkey` - public synthetic test values, never device secrets

A Rust test reproducing `blob -> payload` for every vector proves the crypto
before any hardware is involved.

Usage: python3 tools/gen_crypto_vectors.py [--out src/tests/crypto_vectors.json]
"""

import argparse
import json
import os
import random
import sys

MAC = bytes.fromhex("AABBCCDDEEFF")
BINDKEY = bytes.fromhex("000102030405060708090A0B0C0D0E0F")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--codec", default="/tmp/ble-pkg")
    parser.add_argument("--out", default="src/tests/crypto_vectors.json")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    sys.path.insert(0, args.codec)
    import construct as cs
    from atc_mi_interface.atc_mi_construct_adapters import (
        AtcMiCodec, BtHomeCodec, BtHomeV2Codec, MiLikeCodec)

    rng = random.Random(args.seed)
    vectors = []

    # AtcMiCodec (custom_enc, atc1441_enc): the tunnel payload is the plaintext,
    # the advertisement carries BD + ciphertext + 4 byte MIC.
    for name, size, uuid in (("custom_enc", 6, b"\x1a\x18"), ("atc1441_enc", 3, b"\x1a\x18")):
        for _ in range(8):
            plain = bytes(rng.randrange(256) for _ in range(size))
            structure = cs.Struct(
                "UUID" / cs.Const(uuid, cs.Bytes(2)),
                "x" / AtcMiCodec(cs.Bytes(size), bindkey=BINDKEY, mac_address=MAC),
            )
            blob = structure.build({"x": plain}, mac_address=MAC, bindkey=BINDKEY)
            back = structure.parse(blob, mac_address=MAC, bindkey=BINDKEY)["x"]
            assert back == plain, (name, back.hex(), plain.hex())
            # blob = UUID (2) + 0xBD + ciphertext + MIC, i.e. the whole service data
            assert blob[2] == 0xBD, blob.hex()
            vectors.append({
                "codec": "atc_mi", "format": name, "uuid": uuid.hex().upper(),
                "mac": MAC.hex().upper(), "bindkey": BINDKEY.hex().upper(),
                "blob": blob.hex().upper(), "payload": plain.hex().upper(),
            })

    # MiLikeCodec: nonce = mac[::-1] + device_id(2) + counter(1) + count_id(3),
    # AAD \x11, the tunnel payload is count_id + message.
    for _ in range(8):
        device_id = bytes([0x05, 0x02])
        counter = bytes([rng.randrange(256)])
        message = bytes(rng.randrange(256) for _ in range(rng.randrange(2, 8)))
        payload = bytes(rng.randrange(256) for _ in range(3)) + message
        structure = cs.Struct(
            "device_id" / cs.Const(device_id, cs.Bytes(2)),
            "counter" / cs.Const(counter, cs.Bytes(1)),
            "x" / MiLikeCodec(cs.Bytes(len(payload)), bindkey=BINDKEY, mac_address=MAC),
        )
        blob = structure.build({"x": payload}, mac_address=MAC, bindkey=BINDKEY)
        back = structure.parse(blob, mac_address=MAC, bindkey=BINDKEY)["x"]
        assert back == payload, (back.hex(), payload.hex())
        # dev_id, counter and the 7 trailing bytes are part of the frame.
        assert blob[:3] == device_id + counter, blob.hex()
        vectors.append({
            "codec": "mi_like", "format": "mi_like",
            "device_id": device_id.hex().upper(), "counter": counter.hex().upper(),
            "mac": MAC.hex().upper(), "bindkey": BINDKEY.hex().upper(),
            "blob": blob.hex().upper(), "payload": payload.hex().upper(),
            "header": 3,
        })

    # BtHomeCodec / BtHomeV2Codec: nonce = mac + uuid [+ device_info] + count_id,
    # AAD \x11 for BtHome only, tunnel payload = count_id + message.
    for cls, name, uuid in ((BtHomeCodec, "bt_home", b"\x1e\x18"),
                            (BtHomeV2Codec, "bt_home_v2", b"\xd2\xfc")):
        for _ in range(8):
            message = bytes(rng.randrange(256) for _ in range(rng.randrange(2, 8)))
            payload = bytes(rng.randrange(256) for _ in range(4)) + message
            fields = ["UUID" / cs.Const(uuid, cs.Bytes(2))]
            if cls is BtHomeV2Codec:
                # The v2 nonce includes the one byte DevInfo prefix (0x41).
                fields.append("DevInfo" / cs.Const(b"\x41", cs.Bytes(1)))
            fields.append("x" / cls(cs.Bytes(len(payload)), bindkey=BINDKEY,
                                    mac_address=MAC))
            structure = cs.Struct(*fields)
            blob = structure.build({"x": payload}, mac_address=MAC, bindkey=BINDKEY)
            back = structure.parse(blob, mac_address=MAC, bindkey=BINDKEY)["x"]
            assert back == payload, (name, back.hex(), payload.hex())
            vectors.append({
                "codec": name, "format": name, "uuid": uuid.hex().upper(),
                "mac": MAC.hex().upper(), "bindkey": BINDKEY.hex().upper(),
                "blob": blob.hex().upper(), "payload": payload.hex().upper(),
            })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as handle:
        json.dump({"generated_by": "tools/gen_crypto_vectors.py", "vectors": vectors},
                  handle, indent=1, sort_keys=True)
        handle.write("\n")
    counts = {}
    for vector in vectors:
        counts[vector["codec"]] = counts.get(vector["codec"], 0) + 1
    print("crypto vectors: %d %s -> %s" % (len(vectors), counts, args.out))


if __name__ == "__main__":
    main()
