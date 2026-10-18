#!/usr/bin/env python3
"""Apply version-checked dependency fixes without floating Cargo lock entries."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tarfile
import tomllib


DATAFUSION_REVISION = "676dd338f8fe8464a861b5c74ec3c4de8325d382"
WASM_REVISION = "9186474d530904e787e8903b61f586c10e97e317"
WASI_HTTP_CHECKSUM = "1d75e17f0c94810a34a51dccee9a5e9733eb423dff5176aaeb9152a7a03b2812"
PROMETHEUS_CHECKSUM = "3ca5326d8d0b950a9acd87e6a3f94745394f62e4dae1b1ee22b2bc0c394af43a"


def apply_patch(directory, patch):
    command = ["patch", "--batch", "--fuzz=0", "-p1", "-i", str(patch)]
    forward = subprocess.run(command + ["--forward", "--dry-run"], cwd=directory, capture_output=True)
    if forward.returncode == 0:
        subprocess.run(command + ["--forward"], cwd=directory, check=True)
        return
    reverse = subprocess.run(command + ["--reverse", "--dry-run"], cwd=directory, capture_output=True)
    if reverse.returncode != 0:
        raise RuntimeError(f"patch does not match the pinned source: {patch.name}")


def apply_registry_overrides(workspace, cargo_home, patches, lock):
    overrides = [
        ("wasmtime-wasi-http", "48.0.1", WASI_HTTP_CHECKSUM,
         "103-wasi-http-atomic64.patch", "104-wasi-http-workspace.patch"),
        ("prometheus", "0.14.0", PROMETHEUS_CHECKSUM,
         "107-prometheus-atomic64.patch", "108-prometheus-workspace.patch"),
    ]
    for name, version, checksum, source_patch, workspace_patch in overrides:
        packages = [package for package in lock["package"] if package["name"] == name]
        if len(packages) != 1 or packages[0]["version"] != version:
            raise RuntimeError(f"unexpected {name} version; review the dependency patch")
        archives = list((cargo_home / "registry/cache").glob(f"*/{name}-{version}.crate"))
        if not archives:
            continue
        if len(archives) != 1 or hashlib.sha256(archives[0].read_bytes()).hexdigest() != checksum:
            raise RuntimeError(f"{name} archive is ambiguous or has an unexpected checksum")
        directory = workspace / ".cargo/freetz-sources" / f"{name}-{version}"
        if not directory.exists():
            directory.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archives[0]) as archive:
                archive.extractall(directory.parent, filter="data")
        apply_patch(directory, patches / source_patch)
        apply_patch(workspace, patches / workspace_patch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cargo-home", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    patches = Path(__file__).resolve().parents[1] / "cargo-patches"
    lock = tomllib.loads((workspace / "Cargo.lock").read_text())
    execution = [package for package in lock["package"] if package["name"] == "datafusion-execution"]
    atomic = [package for package in lock["package"] if package["name"] == "portable-atomic"]
    if len(execution) != 1 or not execution[0].get("source", "").endswith("#" + DATAFUSION_REVISION):
        raise RuntimeError("unexpected DataFusion revision; review the dependency patch before updating")
    if len(atomic) != 1 or atomic[0]["version"] != "1.13.1":
        raise RuntimeError("the pinned portable-atomic dependency is missing or ambiguous")
    procfs = [package for package in lock["package"] if package["name"] == "rustix-linux-procfs"]
    if len(procfs) != 1 or procfs[0]["version"] != "0.1.1":
        raise RuntimeError("unexpected rustix-linux-procfs version; review the dependency patch")
    for directory in (args.cargo_home.resolve() / "registry/src").glob("*/rustix-linux-procfs-0.1.1"):
        apply_patch(directory, patches / "102-rustix-linux-procfs-statfs.patch")
    apply_registry_overrides(workspace, args.cargo_home.resolve(), patches, lock)
    checkouts = args.cargo_home.resolve() / "git/checkouts"
    wasm = [package for package in lock["package"] if package["name"] == "datafusion-udf-wasm-host"]
    if len(wasm) != 1 or not wasm[0].get("source", "").endswith("#" + WASM_REVISION):
        raise RuntimeError("unexpected WASM host revision; review the dependency patch")
    wasm_checkouts = [directory for directory in checkouts.glob("datafusion-udf-wasm-*/*")
                      if directory.name == WASM_REVISION[:7]
                      and (directory / "host/Cargo.toml").is_file()]
    for directory in wasm_checkouts:
        apply_patch(directory, patches / "105-wasm-host-target-support.patch")
    if wasm_checkouts:
        apply_patch(workspace, patches / "106-wasm-host-lock.patch")
    matching = [directory for directory in checkouts.glob("arrow-datafusion-*/*")
                if directory.name == DATAFUSION_REVISION[:7]
                and (directory / "datafusion/execution/Cargo.toml").is_file()]
    if not matching:
        return
    for directory in matching:
        apply_patch(directory, patches / "100-datafusion-execution-atomic64.patch")
    apply_patch(workspace, patches / "101-datafusion-execution-lock.patch")
    updated = tomllib.loads((workspace / "Cargo.lock").read_text())
    current = next(package for package in updated["package"] if package["name"] == "datafusion-execution")
    if "portable-atomic" not in current["dependencies"]:
        raise RuntimeError("DataFusion lock entry was not updated")


if __name__ == "__main__":
    main()