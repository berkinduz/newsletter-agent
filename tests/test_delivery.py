#!/usr/bin/env python3
"""Offline two-recipient shared-issue tests. No draft, connector or mail call."""
import hashlib
from datetime import datetime, timezone
import unittest
from sincap import delivery as d


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.readers = [{"id": "first", "email": "first" + "@" + "example.invalid"},
                        {"id": "second", "email": "second" + "@" + "example.invalid"}]
        self.state = d.new_delivery("test/delivery", 2, self.readers,
                                    hashlib.sha256(b"same editorial content").hexdigest())
        self.accepted = {"status": "provider_accepted", "provider_message_id": "fixture-provider-id",
                         "sent_verified": True, "evidence": "Fixture: provider plus matching Sent"}
        self.rejected = {"status": "definitively_rejected", "definitive_rejection": True,
                         "evidence": "Fixture: explicit non-acceptance"}
        self.uncertain = {"status": "uncertain", "evidence": "Fixture: timeout, provider unknown"}

    def test_same_issue_one_envelope_one_counter_advance(self):
        self.assertEqual(d.to_header(self.state), ", ".join(x["email"] for x in self.readers))
        d.validate_envelope(self.state, d.to_header(self.state))
        state = d.reserve(self.state, "attempt")
        state = d.record_result(state, "attempt", {"first": self.accepted, "second": self.accepted})
        state, number = d.advance_once(state, 2)
        self.assertEqual(number, 3)
        self.assertEqual(d.advance_once(state, 3)[1], 3)
        self.assertEqual(d.eligible_recipient_ids(state), [])

    def test_accepted_recipient_excluded_from_partial_repair(self):
        state = d.reserve(self.state, "attempt")
        state = d.record_result(state, "attempt", {"first": self.accepted, "second": self.rejected})
        state, number = d.advance_once(state, 2)
        self.assertEqual(d.eligible_recipient_ids(state), ["second"])
        with self.assertRaises(d.DeliveryError):
            d.reserve(state, "bad-repair", ["first", "second"])
        repaired = d.reserve(state, "repair", ["second"])
        d.validate_envelope(repaired, self.readers[1]["email"], recipient_ids=["second"])
        repaired = d.record_result(repaired, "repair", {"second": self.accepted})
        self.assertEqual(d.advance_once(repaired, number)[1], 3)

    def test_uncertainty_blocks_repeat_for_every_recipient(self):
        state = d.reserve(self.state, "attempt")
        state = d.record_result(state, "attempt", {"first": self.accepted, "second": self.uncertain})
        state, number = d.advance_once(state, 2)
        self.assertEqual(number, 3)
        self.assertEqual(state["status"], "partial_uncertain")
        self.assertEqual(d.eligible_recipient_ids(state), [])
        with self.assertRaises(d.DeliveryError):
            d.reserve(state, "retry")

    def test_unknown_all_does_not_consume_issue(self):
        state = d.reserve(self.state, "attempt")
        state = d.record_result(state, "attempt", {"first": self.uncertain, "second": self.uncertain})
        self.assertEqual(d.advance_once(state, 2)[1], 2)

    def test_reconcile_unknown_once_without_changing_confirmed_recipient(self):
        state = d.reserve(self.state, "attempt")
        old = {"first": self.accepted, "second": self.uncertain}
        state = d.record_result(state, "attempt", old)
        result = {"first": self.accepted, "second": self.accepted}
        with self.assertRaises(d.DeliveryError):
            d.record_result(state, "attempt", result)
        state = d.record_result(state, "attempt", result, reconcile=True)
        self.assertEqual(d.record_result(state, "attempt", result), state)
        state, number = d.advance_once(state, 2)
        self.assertEqual(d.advance_once(state, number)[1], 3)

    def test_existing_reservation_never_authorizes_second_call(self):
        state = d.reserve(self.state, "attempt")
        with self.assertRaises(d.DeliveryError):
            d.reserve(state, "attempt")
        with self.assertRaises(d.DeliveryError):
            d.reserve(state, "different-attempt")

    def test_wrong_or_extra_recipient_and_cc_bcc_rejected(self):
        with self.assertRaises(d.DeliveryError):
            d.validate_envelope(self.state, self.readers[0]["email"])
        with self.assertRaises(d.DeliveryError):
            d.validate_envelope(self.state, d.to_header(self.state), bcc=self.readers[0]["email"])
        with self.assertRaises(d.DeliveryError):
            d.validate_envelope(self.state, d.to_header(self.state) + ", extra" + "@" + "example.invalid")

    def test_no_success_without_provider_and_sent(self):
        state = d.reserve(self.state, "attempt")
        bad = {**self.accepted, "sent_verified": False}
        with self.assertRaises(d.DeliveryError):
            d.record_result(state, "attempt", {"first": self.accepted, "second": bad})

    def test_no_retry_from_unproven_failure(self):
        state = d.reserve(self.state, "attempt")
        bad = {**self.rejected, "definitive_rejection": False}
        with self.assertRaises(d.DeliveryError):
            d.record_result(state, "attempt", {"first": self.accepted, "second": bad})

    def test_recipient_set_is_snapshotted_and_counter_conflict_rejected(self):
        digest = self.state["recipient_set_hash"]
        self.readers.append({"id": "third", "email": "third" + "@" + "example.invalid"})
        self.assertEqual(len(self.state["recipients"]), 2)
        self.assertEqual(self.state["recipient_set_hash"], digest)
        state = d.reserve(self.state, "attempt")
        state = d.record_result(state, "attempt", {"first": self.accepted, "second": self.accepted})
        with self.assertRaises(d.DeliveryError):
            d.advance_once(state, 99)

    def test_explicit_authorization_disabled_delivery_clock_and_self_test(self):
        from test_core import fixtures
        profile, _ = fixtures()
        early = datetime(2030, 1, 2, 8, 59, tzinfo=timezone.utc)
        on_time = datetime(2030, 1, 2, 9, 0, tzinfo=timezone.utc)
        key = profile["id"] + "/2030-01-02"
        with self.assertRaises(d.DeliveryError):
            d.assert_send_allowed(profile, key, on_time)
        with self.assertRaises(d.DeliveryError):
            d.assert_send_allowed(profile, key, on_time, user_authorized=True)
        profile["delivery"]["enabled"] = True
        with self.assertRaises(d.DeliveryError):
            d.assert_send_allowed(profile, key, early, user_authorized=True)
        d.assert_send_allowed(profile, key, on_time, user_authorized=True)
        with self.assertRaises(d.DeliveryError):
            d.assert_send_allowed(profile, key, on_time, user_authorized=True, scheduled=True)
        profile["delivery"]["enabled"] = False
        d.assert_send_allowed(profile, "test/transport", early, user_authorized=True, self_test=True)
        profile["delivery"]["recipients"][0]["email"] = "other" + "@" + "example.invalid"
        with self.assertRaises(d.DeliveryError):
            d.assert_send_allowed(profile, "test/transport", early, user_authorized=True, self_test=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
