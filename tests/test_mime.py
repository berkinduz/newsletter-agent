from copy import deepcopy
from email import policy
from email.parser import BytesParser
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

from sincap import core, mime, render
from test_core import fixtures, NOW


def png_fixture(color):
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", 2, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" + bytes(color) * 2)) + chunk(b"IEND", b""))


class TextRenderTests(unittest.TestCase):
    def test_escaped_content_plain_alternative_and_no_network(self):
        profile, issue = fixtures()
        issue["articles"][0]["title"] = '<script>alert("fixture")</script>'
        with patch("socket.socket", side_effect=AssertionError("No network allowed")):
            rows, _, key = core.select_articles(profile, issue, core.new_history(), NOW, demo=True)
            markup, plain, assets, _ = render.render(profile, issue, rows, 1, Path("missing"))
            raw, delivery = mime.package(profile, key, 1, markup, plain, assets, NOW)
        self.assertIn("&lt;script&gt;", markup)
        self.assertNotIn("<script>", markup)
        self.assertNotIn("$SECTIONS", markup)
        self.assertIn('<table role="presentation"', markup)
        self.assertIn("font-size:30px", markup)
        self.assertIn("font-size:26px", markup)
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(parsed.get_content_type(), "multipart/alternative")
        self.assertEqual(delivery["status"], "prepared")
        changed = raw.replace(b"owner@example.invalid", b"other@example.invalid", 1)
        with self.assertRaisesRegex(ValueError, "Sender"):
            mime.verify(changed, delivery, markup, plain, assets)

    def test_length_and_visual_omission_rules(self):
        profile, issue = fixtures()
        profile["length"]["max_words"] = 10
        with self.assertRaisesRegex(ValueError, "word range"):
            render.render(profile, issue, issue["articles"], 1, Path("missing"))
        profile, issue = fixtures()
        issue["synthetic"] = False
        with self.assertRaisesRegex(ValueError, "real image search"):
            render.render(profile, issue, issue["articles"], 1, Path("missing"))


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Existing Pillow decoder unavailable; real-image support remains unverified")
class InlineImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile, self.issue = fixtures()
        third = deepcopy(self.issue["articles"][0])
        third.update(id="third-fixture", event_key="third-event", url="https://science.example.invalid/third")
        self.issue["articles"].append(third)
        for index, article in enumerate(self.issue["articles"]):
            path = self.root / (str(index) + ".png")
            path.write_bytes(png_fixture((index * 40, 30, 20)))
            _, actual = render.inspect_image(path)
            article["image"] = {"file": path.name, "article_id": article["id"], "event_key": article["event_key"],
                "issue_date": self.issue["issue_date"], "use_scope": "contract_test", "role": "story",
                "source_page": article["url"], "observed_on": article["url"], "image_url": "https://media.example.invalid/fixture.png",
                "observed_via": "img", "access_status": "normal_public_access", "alt": "Synthetic two-pixel PNG for transport tests",
                "credit": "Synthetic test fixture", "rights_note": "Generated in this test; no news photo", "selection_reason": "CID transport test only",
                "review": {"pixels_viewed": True, "context_verified": True, "date_verified": True, "credit_verified": True,
                           "rights_verified_for_scope": True, "note": "Synthetic review flags; this is not a real editorial review"}, **actual}
            article["image_decision"] = {"status": "selected", "reason": "Synthetic CID test", "attempts": []}

    def rendered(self):
        return render.render(self.profile, self.issue, self.issue["articles"], 1, self.root)

    def test_three_cids_keep_exact_bytes_and_story_order(self):
        markup, plain, assets, _ = self.rendered()
        raw, delivery = mime.package(self.profile, "test/2030-01-02", 1, markup, plain, assets, NOW)
        mime.verify(raw, delivery, markup, plain, assets)
        self.assertEqual(len(assets), 3)
        for article in self.issue["articles"]:
            start = markup.index('data-source="' + article["id"] + '"')
            positions = [markup.index(marker, start) for marker in ('<h3', '<img', 'data-role="image-credit"', 'data-role="story-summary"', 'class="comment"')]
            self.assertEqual(positions, sorted(positions))
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        images = [x for x in parsed.walk() if x.get_content_maintype() == "image"]
        self.assertEqual([x.get_payload(decode=True) for x in images], [x["data"] for x in assets])

    def test_changed_binding_hash_rights_or_scope_is_rejected(self):
        image = self.issue["articles"][0]["image"]
        for field, value in (("sha256", "0" * 64), ("event_key", "different"), ("use_scope", "newsletter"), ("file", "../outside.png")):
            old = image[field]
            image[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.rendered()
            image[field] = old
        image["review"]["rights_verified_for_scope"] = False
        with self.assertRaisesRegex(ValueError, "Missing image review"):
            self.rendered()

    def test_invalid_bytes_and_symlink_stop_import(self):
        path = self.root / "bad.png"
        path.write_bytes(b"not an image")
        with self.assertRaises(ValueError):
            render.inspect_image(path)
        path.unlink()
        path.symlink_to(self.root / "0.png")
        with self.assertRaises(ValueError):
            render.inspect_image(path)
