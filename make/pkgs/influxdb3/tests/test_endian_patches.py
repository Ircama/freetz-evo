import hashlib
import importlib.util
from pathlib import Path
import tarfile
import tempfile
import tomllib
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cargo_patches", PACKAGE / "tools/apply-cargo-patches.py")
PATCHES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHES)
CACHE = PACKAGE.parents[2] / "build/cargo-influxdb3-cache/3.12.1-mips-unknown-linux-uclibc/cargo"


class EndianPatchesTest(unittest.TestCase):
    def test_replacements_are_idempotent_even_when_new_contains_old(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source"
            path.write_text("old")
            PATCHES.replace_checked(path, "old", "new(old)")
            PATCHES.replace_checked(path, "old", "new(old)")
            self.assertEqual(path.read_text(), "new(old)")

    def test_source_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source"
            path.write_text("unexpected")
            with self.assertRaises(RuntimeError):
                PATCHES.replace_checked(path, "old", "new")

    def test_replacements_remove_metadata_when_new_is_a_prefix_of_old(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Cargo.lock"
            header = 'name = "arrow-buffer"\nversion = "57.3.1"\n'
            original = header + 'source = "registry"\nchecksum = "pinned"\n'
            path.write_text(original)
            PATCHES.replace_checked(path, original, header)
            self.assertEqual(path.read_text(), header)
            PATCHES.replace_checked(path, original, header)
            self.assertEqual(path.read_text(), header)

    def test_endian_overrides_update_manifest_and_lock_together(self):
        for name, (version, _) in PATCHES.ENDIAN_OVERRIDES.items():
            if not list((CACHE / "registry/cache").glob(f"*/{name}-{version}.crate")):
                self.skipTest("the pinned InfluxDB Cargo archives are not available")
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            manifest = workspace / "Cargo.toml"
            manifest.write_text("[workspace]\nmembers = []\n")
            lockfile = workspace / "Cargo.lock"
            lockfile.write_text("\n".join(
                f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
                f'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
                f'checksum = "{checksum}"\n'
                for name, (version, checksum) in PATCHES.ENDIAN_OVERRIDES.items()
            ))
            PATCHES.apply_endian_overrides(workspace, CACHE, tomllib.loads(lockfile.read_text()))
            updated_lock = tomllib.loads(lockfile.read_text())
            updated_manifest = tomllib.loads(manifest.read_text())
            for package in updated_lock["package"]:
                self.assertNotIn("source", package)
                self.assertNotIn("checksum", package)
                name = package["name"]
                self.assertEqual(
                    updated_manifest["patch"]["crates-io"][name]["path"],
                    f'.cargo/freetz-sources/{name}-{package["version"]}',
                )
            first = (manifest.read_text(), lockfile.read_text())
            PATCHES.apply_endian_overrides(workspace, CACHE, updated_lock)
            self.assertEqual(first, (manifest.read_text(), lockfile.read_text()))

    def test_pinned_archive_fixes_are_idempotent(self):
        for name, (version, checksum) in PATCHES.ENDIAN_OVERRIDES.items():
            with self.subTest(package=name):
                archives = list((CACHE / "registry/cache").glob(f"*/{name}-{version}.crate"))
                if not archives:
                    self.skipTest("the pinned InfluxDB Cargo archives are not available")
                self.assertEqual(len(archives), 1)
                self.assertEqual(hashlib.sha256(archives[0].read_bytes()).hexdigest(), checksum)
                with tempfile.TemporaryDirectory() as temporary:
                    with tarfile.open(archives[0]) as archive:
                        archive.extractall(temporary, filter="data")
                    directory = Path(temporary) / f"{name}-{version}"
                    PATCHES.apply_endian_fixes(name, directory)
                    first = {p: p.read_bytes() for p in directory.rglob("*.rs")}
                    PATCHES.apply_endian_fixes(name, directory)
                    self.assertEqual(first, {p: p.read_bytes() for p in directory.rglob("*.rs")})


if __name__ == "__main__":
    unittest.main()
