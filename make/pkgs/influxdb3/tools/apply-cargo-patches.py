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
ENDIAN_OVERRIDES = {
    "arrow-buffer": ("57.3.1", "0d18b89b4c4f4811d0858175e79541fe98e33e18db3b011708bc287b1240593f"),
    "parquet": ("57.3.1", "2e832c6aa20310fc6de7ea5a3f4e20d34fd83e3b43229d32b81ffe5c14d74692"),
}


def replace_checked(path, old, new, count=1):
    source = path.read_text()
    if old in new and source.count(new) == count:
        return
    if source.count(old) == count:
        path.write_text(source.replace(old, new))
    elif source.count(new) != count:
        raise RuntimeError(f"endian fix does not match the pinned source: {path}")


def apply_endian_fixes(name, directory):
    if name == "arrow-buffer":
        path = directory / "src/util/bit_chunk_iterator.rs"
        replace_checked(path, "let prefix = chunks[0] & prefix_mask;",
                        "let prefix = u64::from_le(chunks[0]) & prefix_mask;")
        replace_checked(path, "let suffix = chunks[chunks.len() - 1] & suffix_mask;",
                        "let suffix = u64::from_le(chunks[chunks.len() - 1]) & suffix_mask;")
        replace_checked(path, ".chain(self.chunks.iter().cloned())",
                        ".chain(self.chunks.iter().cloned().map(u64::from_le as fn(u64) -> u64))")
        replace_checked(
            path,
            "std::iter::Cloned<std::slice::Iter<'a, u64>>",
            "std::iter::Map<std::iter::Cloned<std::slice::Iter<'a, u64>>, fn(u64) -> u64>",
        )
        return

    path = directory / "src/data_type.rs"
    replace_checked(
        path,
        "    fn as_bytes(&self) -> &[u8];\n}",
        """    fn as_bytes(&self) -> &[u8];

    fn as_le_bytes(&self) -> std::borrow::Cow<'_, [u8]> {
        std::borrow::Cow::Borrowed(self.as_bytes())
    }
}""",
    )
    replace_checked(
        path,
        "        impl AsBytes for $source_ty {\n",
        """        impl AsBytes for $source_ty {
            fn as_le_bytes(&self) -> std::borrow::Cow<'_, [u8]> {
                #[cfg(target_endian = "little")]
                { std::borrow::Cow::Borrowed(self.as_bytes()) }
                #[cfg(target_endian = "big")]
                { std::borrow::Cow::Owned(self.to_le_bytes().to_vec()) }
            }
""",
    )
    replace_checked(path, "writer.write_all(&len.to_ne_bytes())?;",
                    "writer.write_all(&len.to_le_bytes())?;")
    replace_checked(
        path,
        "                    writer.write_all(raw)?;\n",
        """                    #[cfg(target_endian = "little")]
                    writer.write_all(raw)?;
                    #[cfg(target_endian = "big")]
                    {
                        let _ = raw;
                        for value in values {
                            writer.write_all(&value.to_le_bytes())?;
                        }
                    }
""",
    )
    replace_checked(
        path,
        "                    decoder.start += bytes_to_decode;\n",
        """                    #[cfg(target_endian = "big")]
                    for value in &mut buffer[..num_values] {
                        *value = Self::from_le_bytes(value.to_ne_bytes());
                    }
                    decoder.start += bytes_to_decode;
""",
    )
    path = directory / "src/encodings/rle.rs"
    replace_checked(path, ".to_ne_bytes()", ".to_le_bytes()", count=2)
    path = directory / "src/util/bit_util.rs"
    replace_checked(path, "let slice = val.as_bytes();", "let slice = val.as_le_bytes();", count=2)
    replace_checked(path, "T::try_from_le_slice(v.as_bytes()).ok()",
                    "T::try_from_le_slice(&v.to_le_bytes()).ok()")
    path = directory / "src/file/statistics.rs"
    replace_checked(
        path,
        "    // Get min/max if set.\n",
        """    let encoded_statistic = |bytes: &[u8]| {
        #[allow(unused_mut)]
        let mut bytes = bytes.to_vec();
        #[cfg(target_endian = "big")]
        match stats.physical_type() {
            Type::INT32 | Type::INT64 | Type::FLOAT | Type::DOUBLE => bytes.reverse(),
            Type::INT96 => {
                for word in bytes.chunks_exact_mut(4) {
                    word.reverse();
                }
            }
            _ => {}
        }
        bytes
    };
    // Get min/max if set.
""",
    )
    replace_checked(path, "stats.min_bytes_opt().map(|x| x.to_vec())",
                    "stats.min_bytes_opt().map(encoded_statistic)")
    replace_checked(path, "stats.max_bytes_opt().map(|x| x.to_vec())",
                    "stats.max_bytes_opt().map(encoded_statistic)")
    path = directory / "src/file/page_index/column_index.rs"
    for bound in ("min", "max"):
        replace_checked(
            path,
            f"let {bound} = self.{bound}_value(i).map(|m| m.as_bytes()).unwrap_or(&[]);\n"
            f"            {bound}.write_thrift(writer)?;",
            f"let {bound} = self.{bound}_value(i).map(|m| m.as_le_bytes()).unwrap_or_default();\n"
            f"            {bound}.as_ref().write_thrift(writer)?;",
        )
    path = directory / "src/column/writer/encoder.rs"
    for number in ("f32", "f64"):
        replace_checked(
            path,
            f"{number}::from_le_bytes(val.as_bytes().try_into().unwrap())",
            f"{number}::from_le_bytes(val.as_le_bytes().as_ref().try_into().unwrap())",
        )


def apply_endian_overrides(workspace, cargo_home, lock):
    for name, (version, checksum) in ENDIAN_OVERRIDES.items():
        packages = [package for package in lock["package"] if package["name"] == name]
        if len(packages) != 1 or packages[0]["version"] != version:
            raise RuntimeError(f"unexpected {name} version; review endian fixes")
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
        apply_endian_fixes(name, directory)
        manifest = workspace / "Cargo.toml"
        override = f'[patch.crates-io.{name}]\npath = ".cargo/freetz-sources/{name}-{version}"\n'
        source = manifest.read_text()
        if override not in source:
            if f"[patch.crates-io.{name}]" in source:
                raise RuntimeError(f"conflicting {name} override")
            if source.count("[workspace]\n") != 1:
                raise RuntimeError("missing or ambiguous workspace header")
            manifest.write_text(source.replace("[workspace]\n", override + "\n[workspace]\n", 1))
        lock_path = workspace / "Cargo.lock"
        old = (f'name = "{name}"\nversion = "{version}"\n'
               f'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
               f'checksum = "{checksum}"\n')
        replace_checked(lock_path, old, f'name = "{name}"\nversion = "{version}"\n')


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
    apply_endian_overrides(workspace, args.cargo_home.resolve(), lock)
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