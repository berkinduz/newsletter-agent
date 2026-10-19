"""Escaped email HTML/plain and checked inline image assets; no network requests."""
import hashlib
import html
import math
from pathlib import Path
import re
from string import Template

from .core import public_url, require, text

ROOT = Path(__file__).resolve().parents[1]
STYLE = "font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.65;color:#63686d;"
LINK = "color:#23734c;text-decoration:underline;"


def inspect_image(path):
    require(path.is_file() and not path.is_symlink(), "Regular image file required")
    require(0 < path.stat().st_size <= 10 * 1024 * 1024, "Image exceeds 10 MiB or is empty")
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        raise ValueError("Actual image bytes must be PNG or JPEG")
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Image decoder unavailable; record the gap, do not install or pretend success") from exc
    with Image.open(path) as image:
        require(0 < image.width * image.height <= 40_000_000, "Image pixel limit exceeded")
        require(image.format == {"image/png": "PNG", "image/jpeg": "JPEG"}[mime], "Image type mismatch")
        image.verify()
    with Image.open(path) as image:
        image.load()
        width, height = image.size
    return data, {"sha256": hashlib.sha256(data).hexdigest(), "mime_type": mime,
                  "width": width, "height": height, "size_bytes": len(data)}


def checked_asset(article, issue, images_root):
    image = article["image"]
    require(image.get("article_id") == article["id"] and image.get("event_key") == article["event_key"]
            and image.get("issue_date") == issue["issue_date"], "Image belongs to another article/event/day")
    require(image.get("use_scope") == ("contract_test" if issue["synthetic"] else "newsletter"),
            "Test image cannot become a production asset")
    for field in ("source_page", "observed_on", "image_url"):
        public_url(text(image, field))
    require(image.get("observed_via") in {"img", "srcset", "og:image", "rss:media"}, "Image URL was not observed")
    require(image.get("access_status") == "normal_public_access", "Image access is blocked or unverified")
    require(image.get("role") in {"story", "explanatory"}, "Invalid image role")
    for field in ("alt", "credit", "rights_note", "selection_reason"):
        text(image, field)
    require(len(image["credit"]) <= 160, "Use a short image credit")
    review = image.get("review", {})
    for field in ("pixels_viewed", "context_verified", "date_verified", "credit_verified", "rights_verified_for_scope"):
        require(review.get(field) is True, "Missing image review: " + field)
    text(review, "note")
    relative = Path(text(image, "file"))
    require(not relative.is_absolute() and ".." not in relative.parts, "Image must stay inside images root")
    base = images_root.resolve()
    path = images_root / relative
    require(not path.is_symlink() and all(not parent.is_symlink() for parent in path.parents), "Image symlink forbidden")
    path = path.resolve()
    require(base in path.parents, "Image escapes images root")
    data, actual = inspect_image(path)
    require(all(image.get(key) == value for key, value in actual.items()), "Image hash/type/size/dimensions differ")
    cid = "image-" + hashlib.sha256(article["id"].encode()).hexdigest()[:24]
    suffix = ".png" if actual["mime_type"] == "image/png" else ".jpg"
    return {"cid": cid, "filename": cid + suffix, "data": data, **actual}


def check_visual_decision(profile, issue, article, topic):
    decision = article.get("image_decision", {})
    text(decision, "reason")
    image = article.get("image")
    if image:
        require(profile["images"]["enabled"] and decision.get("status") == "selected", "Image choice differs from profile")
    elif issue["synthetic"] or not profile["images"]["enabled"]:
        require(decision.get("status") == "text_only", "Explicit text-only decision required")
    else:
        require(decision.get("status") == "unavailable", "Record the real image search and obstacle")
        attempts = decision.get("attempts", [])
        require(isinstance(attempts, list), "Image search attempts required")
        seen = set()
        for attempt in attempts:
            public_url(text(attempt, "url"))
            text(attempt, "reason")
            require(attempt.get("result") in {"blocked", "unavailable", "unsuitable"}, "Invalid image search result")
            seen.add(attempt["url"])
        require(len(seen) >= (2 if topic["visual_priority"] else 1), "Inspect source and relevant alternatives before omitting an image")


def render(profile, issue, articles, issue_number, images_root):
    esc = html.escape
    assets, sections, plain = [], [], []
    plain.extend([profile["title"], f'{profile["labels"]["issue"]} {issue_number:03d} · {issue["issue_date"]}',
                  profile["greeting"], text(issue, "opening")])
    word_text = [issue["opening"]]
    sources = {x["id"]: x for x in profile["sources"]}
    for topic in profile["topics"]:
        items = [x for x in articles if x["topic"] == topic["id"]]
        if not items:
            continue
        rows = []
        plain.append(topic["title"])
        for article in items:
            check_visual_decision(profile, issue, article, topic)
            source = sources[article["source_id"]]
            metadata = f'{article["kind"]} · {article["published_at"][:10]} · {source["name"]}'
            image_html = ""
            if article.get("image"):
                asset = checked_asset(article, issue, images_root)
                require(not any(x["sha256"] == asset["sha256"] for x in assets), "Do not reuse the same image in different stories")
                assets.append(asset)
                image = article["image"]
                image_html = (
                    '<table role="presentation" width="100%" style="border-collapse:collapse;margin:22px 0 24px;"><tr><td>'
                    f'<img data-image-role="{esc(image["role"])}" src="cid:{asset["cid"]}" width="640" '
                    f'alt="{esc(image["alt"])}" style="display:block;width:100%;max-width:640px;height:auto;border:0;">'
                    f'<p data-role="image-credit" style="{STYLE}margin:10px 0 0;"><a href="{esc(image["source_page"])}" '
                    f'style="{LINK}">{esc(image["credit"])}</a></p></td></tr></table>')
            comment = article.get("comment", "")
            comment_html = (
                '<div class="comment" style="margin:20px 0 18px;border-left:2px solid #c8d1cb;padding-left:16px;color:#50565a;">'
                f'<p style="font-size:15px;font-style:italic;margin:0 0 6px;">{esc(profile["labels"]["comment"])}</p>'
                f'<p style="margin:0;">{esc(comment)}</p></div>') if comment else ""
            rows.append(f'<tr><td data-source="{esc(article["id"])}" style="padding:0 0 32px;">'
                        '<h3 class="story-headline" style="font-family:Georgia,serif;font-size:30px;line-height:1.28;'
                        f'font-weight:400;color:#252a2f;margin:0 0 10px;">{esc(article["title"])}</h3>'
                        f'<p style="{STYLE}margin:0 0 17px;">{esc(metadata)}</p>{image_html}'
                        f'<p data-role="story-summary" style="margin:0 0 17px;">{esc(article["summary"])}</p>{comment_html}'
                        f'<p style="{STYLE}"><a href="{esc(article["url"])}" style="{LINK}">'
                        f'{esc(profile["labels"]["source"])}: {esc(source["name"])}</a></p></td></tr>')
            plain.extend([article["title"], metadata, article["summary"]])
            if comment:
                plain.append(profile["labels"]["comment"] + ": " + comment)
            if article.get("image"):
                plain.append(article["image"]["credit"] + " — " + article["image"]["source_page"])
            plain.append(article["url"])
            word_text.extend([article["summary"], comment])
        sections.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                        f'data-section="{esc(topic["id"])}" style="width:100%;border-collapse:collapse;">'
                        '<tr><td style="padding:36px 0 22px;"><h2 class="section-title" '
                        'style="font-family:Arial,sans-serif;font-size:15px;line-height:1.4;font-weight:700;'
                        'color:#23734c;letter-spacing:1px;text-transform:uppercase;border-top:1px solid #82af93;padding-top:20px;margin:0;">'
                        f'{esc(topic["title"])}</h2></td></tr>{"".join(rows)}</table>')
    require(sum(x["size_bytes"] for x in assets) <= 20 * 1024 * 1024, "Total inline images exceed 20 MiB")
    words = len(re.findall(r"\S+", " ".join(word_text)))
    require(profile["length"]["min_words"] <= words <= profile["length"]["max_words"], "Issue outside configured word range")
    question = text(issue, "closing_question")
    plain.extend([question, *profile["signature"]])
    values = {"LANGUAGE": profile["language"], "TITLE": profile["title"], "ISSUE_LABEL": profile["labels"]["issue"],
              "NUMBER": f"{issue_number:03d}", "DATE": issue["issue_date"], "GREETING": profile["greeting"],
              "OPENING": issue["opening"], "MINUTES": str(max(1, math.ceil(words / 200))),
              "MINUTES_LABEL": profile["labels"]["minutes"], "LINKS_EXTRA": profile["labels"]["links_extra"], "QUESTION": question}
    values = {key: esc(value) for key, value in values.items()}
    values.update(SECTIONS="".join(sections), SIGNATURE="<br>".join(esc(x) for x in profile["signature"]))
    markup = Template((ROOT / "templates/newsletter.html").read_text(encoding="utf-8")).substitute(values)
    return markup, "\n\n".join(plain) + "\n", assets, words
