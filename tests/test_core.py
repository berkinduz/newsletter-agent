from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from sincap import core as c, delivery as d

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2030, 1, 2, 8, 30, tzinfo=timezone.utc)


def fixtures():
    profile = json.loads((ROOT / "examples/profile.json").read_text())
    issue = json.loads((ROOT / "examples/issue.json").read_text())
    return profile, issue


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.profile, self.issue = fixtures()
        self.history = c.new_history()

    def choose(self, **kwargs):
        return c.select_articles(self.profile, self.issue, self.history, NOW, demo=True, **kwargs)

    def test_defaults_are_synthetic_and_disabled(self):
        c.validate_profile(self.profile)
        self.assertFalse(self.profile["delivery"]["enabled"])
        self.assertFalse(self.profile["schedule"]["enabled"])
        self.assertEqual(len(self.choose()[0]), 2)
        with self.assertRaises(ValueError):
            c.select_articles(self.profile, self.issue, self.history, NOW)

    def test_url_normalization_keeps_meaningful_query_parameters(self):
        url = "https://EXAMPLE.invalid/story/?id=9&utm_source=demo#section"
        self.assertEqual(c.canonical_url(url), "https://example.invalid/story?id=9")
        self.assertNotEqual(c.canonical_url(url), c.canonical_url(url.replace("id=9", "id=8")))
        for url in ("http://example.invalid", "https://user:pass@example.invalid", "https://127.0.0.1/", "https://example.invalid/?token=demo"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                c.public_url(url)

    def test_doi_and_event_duplicates_are_removed(self):
        first = self.issue["articles"][0]
        first["doi"] = "10.1234/demo"
        duplicate = deepcopy(first)
        duplicate.update(id="duplicate", url="https://science.example.invalid/different", event_key="other-event", doi="https://doi.org/10.1234/DEMO")
        self.issue["articles"].append(duplicate)
        event = deepcopy(first)
        event.update(id="event-copy", url="https://science.example.invalid/copy", doi=None)
        self.issue["articles"].append(event)
        selected, omitted, _ = self.choose()
        self.assertEqual(len(selected), 2)
        self.assertEqual({x["reason"] for x in omitted}, {"duplicate_in_issue"})

    def test_preferences_and_body_read_are_enforced(self):
        self.profile["excluded_sources"] = ["demo-science"]
        selected, omitted, _ = self.choose()
        self.assertEqual([x["id"] for x in selected], ["demo-essay"])
        self.assertEqual(omitted[0]["reason"], "source_disabled_or_unknown")
        self.issue["articles"][1]["body_read"] = False
        with self.assertRaisesRegex(ValueError, "No readable"):
            self.choose()

    def test_last_cutoff_new_development_and_repeated_daily_issue(self):
        selected, _, key = self.choose()
        delivery = d.new_delivery(key, 1, self.profile["delivery"]["recipients"], c.digest("content"))
        delivery = d.reserve(delivery, "fixture-attempt")
        delivery = d.record_result(delivery, "fixture-attempt", {"self": {"status": "provider_accepted", "sent_verified": True,
                     "provider_message_id": "fixture-only", "evidence": "Synthetic provider and matching Sent"}})
        delivery, _ = d.advance_once(delivery, 1)
        history = c.record_publication(self.history, key, self.issue["researched_at"], selected, delivery)
        self.assertEqual(history["next_issue_number"], 2)
        self.assertEqual(c.record_publication(history, key, self.issue["researched_at"], selected, delivery), history)
        with self.assertRaisesRegex(ValueError, "already published"):
            c.select_articles(self.profile, self.issue, history, NOW, demo=True)
        issue = deepcopy(self.issue)
        issue.update(issue_date="2030-01-03", researched_at="2030-01-03T08:00:00Z")
        tomorrow = NOW + timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "No readable"):
            c.select_articles(self.profile, issue, history, tomorrow, demo=True)
        issue["articles"][0].update(new_development=True, development_note="A distinct new result in this synthetic fixture",
                                    updated_at="2030-01-03T07:00:00Z", revision="follow-up")
        rows, _, _ = c.select_articles(self.profile, issue, history, tomorrow, demo=True)
        self.assertEqual([x["id"] for x in rows], ["demo-study"])
        issue["articles"][0]["revision"] = "initial"
        with self.assertRaisesRegex(ValueError, "No readable"):
            c.select_articles(self.profile, issue, history, tomorrow, demo=True)

    def test_old_research_wrong_language_or_wrong_local_day_stops(self):
        self.history["last_cutoff"] = self.issue["researched_at"]
        with self.assertRaisesRegex(ValueError, "New research"):
            self.choose()
        self.history = c.new_history()
        self.issue["language"] = "en"
        with self.assertRaisesRegex(ValueError, "language"):
            self.choose()
        self.issue["language"] = "tr"
        self.profile["timezone"] = "Pacific/Honolulu"
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.choose()

    def test_source_binding_and_research_timestamps_are_enforced(self):
        self.issue["articles"][0]["url"] = "https://unselected.example.invalid/story"
        with self.assertRaisesRegex(ValueError, "Article host"):
            self.choose()
        self.profile, self.issue = fixtures()
        self.issue["articles"][0]["published_at"] = "2030-01-02T08:15:00Z"
        with self.assertRaisesRegex(ValueError, "recorded research"):
            self.choose()
        self.profile, self.issue = fixtures()
        self.issue["synthetic"] = False
        with self.assertRaisesRegex(ValueError, "Synthetic source"):
            c.select_articles(self.profile, self.issue, self.history, NOW)

    def test_capabilities_need_recent_profile_bound_evidence(self):
        record = json.loads((ROOT / "examples/capabilities.json").read_text())
        self.assertTrue(c.capability_gaps(record, "self-test", NOW, self.profile))
        record["context"] = {"runtime": "fixture-runtime", "repository_revision": "fixture-revision", "profile_sha256": c.digest(self.profile)}
        for check in record["checks"].values():
            check.update(status="verified", checked_at=NOW.isoformat(), evidence="Synthetic evidence; not a real app check")
        self.assertFalse(c.capability_gaps(record, "scheduled", NOW, self.profile))
        self.profile["schedule"]["daily_at"] = "10:00"
        self.assertIn("profile_evidence_mismatch", c.capability_gaps(record, "scheduled", NOW, self.profile))
        self.assertTrue(c.capability_gaps(record, "scheduled", NOW + timedelta(days=2), self.profile))
