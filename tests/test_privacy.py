import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).resolve().parents[1] / "scripts/preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PrivacyTests(unittest.TestCase):
    def test_synthetic_address_allowed_real_addresses_and_ids_detected(self):
        self.assertFalse(preflight.scan_text("fixture", b"owner@example.invalid"))
        bad = ["owner" + "@" + "mail.invalid", "libfile_" + "a" * 32, "ghp_" + "x" * 36,
               "A" * 600,
               "/" + "Users" + "/" + "fixture" + "/"]
        for value in bad:
            with self.subTest(kind=value[:6]):
                self.assertTrue(preflight.scan_text("fixture", value.encode()))

    def test_unknown_file_and_symlink_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "MANIFEST.txt").write_text("MANIFEST.txt\n.gitignore\nREADME.md\n")
            (root / ".gitignore").write_text("*\n!/MANIFEST.txt\n!/.gitignore\n!/README.md\n")
            (root / "README.md").write_text("Synthetic fixture")
            (root / "private.env").write_text("not a real credential")
            errors, _ = preflight.inspect(root)
            self.assertTrue(any("private.env" in x for x in errors))
            (root / "README.md").unlink()
            (root / "README.md").symlink_to(root / "private.env")
            errors, _ = preflight.inspect(root)
            self.assertTrue(any("symlink" in x for x in errors))
