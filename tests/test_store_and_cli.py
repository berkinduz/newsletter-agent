from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sincap import core, delivery
from sincap.store import LocalStore
from test_core import fixtures, ROOT, NOW


class LocalStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.json"
        self.store = LocalStore(self.path)
        self.store.create({"history": core.new_history(), "deliveries": {}})

    def test_reservation_and_result_history_counter_are_atomic(self):
        profile, issue = fixtures()
        rows, _, key = core.select_articles(profile, issue, core.new_history(), NOW, demo=True)
        snapshot = self.store.read()
        data = snapshot["data"]
        state = delivery.new_delivery(key, 1, profile["delivery"]["recipients"], core.digest("fixture-content"))
        data["deliveries"][key] = delivery.reserve(state, "fixture-reservation")
        saved = self.store.cas(snapshot["version"], data)
        self.assertEqual(self.store.read()["data"]["deliveries"][key]["status"], "sending")
        with self.assertRaises(ValueError):
            delivery.reserve(saved["data"]["deliveries"][key], "retry")
        result = delivery.record_result(saved["data"]["deliveries"][key], "fixture-reservation", {
            "self": {"status": "provider_accepted", "provider_message_id": "fixture-provider",
                     "sent_verified": True, "evidence": "Synthetic acceptance and Sent fixture"}})
        result, _ = delivery.advance_once(result, 1)
        data = saved["data"]
        data["deliveries"][key] = result
        data["history"] = core.record_publication(data["history"], key, issue["researched_at"], rows, result)
        final = self.store.cas(saved["version"], data)
        self.assertEqual(final["data"]["history"]["next_issue_number"], 2)
        self.assertEqual(final["data"]["deliveries"][key]["status"], "sent")

    def test_concurrent_writers_cannot_both_commit_same_version(self):
        def attempt(value):
            try:
                return LocalStore(self.path).cas(0, {"value": value})["version"]
            except (FileExistsError, ValueError):
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(attempt, [1, 2]))
        self.assertEqual(results.count(1), 1)
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(self.store.read()["version"], 1)

    def test_existing_state_stale_version_and_leftover_lock_never_reset(self):
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.create({})
        with self.assertRaises(ValueError):
            self.store.cas(99, {})
        lock = self.path.with_name(self.path.name + ".lock")
        lock.touch()
        with self.assertRaises(FileExistsError):
            self.store.cas(0, {})
        self.assertEqual(before, self.path.read_bytes())
        self.assertTrue(lock.exists())


class CliTests(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "sincap", *map(str, args)], cwd=ROOT,
                              text=True, capture_output=True)

    def test_init_nonoverwrite_and_offline_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "local"
            self.assertEqual(self.command("init", "--directory", local).returncode, 0)
            self.assertEqual(json.loads((local / "profile.json").read_text())["language"], "en")
            before = (local / "state.json").read_bytes()
            self.assertNotEqual(self.command("init", "--directory", local).returncode, 0)
            self.assertEqual(before, (local / "state.json").read_bytes())
            out = local / "preview"
            args = ("prepare", "--demo", "--profile", local / "profile.json", "--input", ROOT / "examples/issue.json",
                    "--at", NOW.isoformat(), "--out", out)
            result = self.command(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertFalse(report["sent"])
            self.assertFalse(report["history_changed"])
            self.assertTrue((out / "newsletter.eml").is_file())
            self.assertNotEqual(self.command(*args).returncode, 0)
            self.assertEqual(before, (local / "state.json").read_bytes())

    def test_each_starter_language_produces_a_matching_offline_bundle(self):
        from sincap.onboarding import load_bundle

        for language, greeting, issue_label, topic, source in (
                ("en", "Hello,", "Issue", "Science", "Example Science"),
                ("tr", "Merhaba,", "Sayı", "Bilim", "Örnek Bilim")):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                local = Path(directory) / "local"
                result = self.command("init", "--language", language, "--directory", local, "--profile-id", "reading")
                self.assertEqual(result.returncode, 0, result.stderr)
                profile = json.loads((local / "profile.json").read_text(encoding="utf-8"))
                self.assertEqual(profile["id"], "reading")
                self.assertEqual(profile["language"], language)
                self.assertFalse(profile["delivery"]["enabled"])
                self.assertFalse(profile["schedule"]["enabled"])
                before = (local / "state.json").read_bytes()
                examples = ROOT / "examples" / ("tr" if language == "tr" else "")
                out = local / "preview"
                result = self.command("prepare", "--demo", "--profile", local / "profile.json",
                                      "--input", examples / "issue.json", "--at", NOW.isoformat(), "--out", out)
                self.assertEqual(result.returncode, 0, result.stderr)
                bundle = load_bundle(out)
                self.assertIn(f'<html lang="{language}">', bundle["html"])
                self.assertIn(f"{issue_label} 001", bundle["delivery"]["subject"])
                for value in (greeting, topic, source, profile["signature"][0], profile["labels"]["comment"]):
                    self.assertIn(value, bundle["html"])
                    self.assertIn(value, bundle["plain"])
                if language == "en":
                    for value in ("Merhaba", "Sayı", "Kaynak", "Bilim", "Kültür", "Bir düşünce"):
                        self.assertNotIn(value, bundle["html"] + bundle["plain"] + bundle["delivery"]["subject"])
                self.assertEqual(before, (local / "state.json").read_bytes())
                doctor = self.command("doctor", "--profile", local / "profile.json")
                self.assertEqual(doctor.returncode, 0, doctor.stderr)
                self.assertEqual(json.loads(doctor.stdout)["language"], language)

    def test_mismatched_language_and_unknown_starter_do_not_create_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "local"
            result = self.command("init", "--language", "de", "--directory", local)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(local.exists())
            out = Path(directory) / "preview"
            result = self.command("prepare", "--demo", "--profile", ROOT / "examples/profile.json",
                                  "--input", ROOT / "examples/tr/issue.json", "--at", NOW.isoformat(), "--out", out)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("language", result.stderr)
            self.assertFalse(out.exists())

    def test_doctor_reports_missing_capabilities_and_no_send_interface(self):
        result = self.command("doctor", "--profile", ROOT / "examples/profile.json", "--capabilities", ROOT / "examples/capabilities.json", "--stage", "scheduled")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["remote_probe_performed"])
        self.assertEqual(self.command("send").returncode, 2)
        result = self.command("prepare", "--at", NOW.isoformat(), "--profile", ROOT / "examples/profile.json", "--input", ROOT / "examples/issue.json", "--out", "unused")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Clock override", result.stderr)
