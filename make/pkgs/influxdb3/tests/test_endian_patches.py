import hashlib
import importlib.util
from pathlib import Path
import tarfile
import tempfile
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
