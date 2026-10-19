"""RFC email package only. This module cannot create a provider draft or send mail."""
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import format_datetime
import hashlib
import re

from .core import digest, require
from .delivery import new_delivery, to_header, validate_envelope


def package(profile, issue_key, number, markup, plain, assets, now):
    editorial_hash = digest({"html": markup, "plain": plain})
    state = new_delivery(issue_key, number, profile["delivery"]["recipients"], editorial_hash)
    alternative = EmailMessage(policy=policy.SMTP)
    alternative.set_content(plain)
    alternative.add_alternative(markup, subtype="html")
    if assets:
        message = EmailMessage(policy=policy.SMTP)
        message.make_related()
        message.attach(alternative)
        for asset in assets:
            message.add_related(asset["data"], maintype="image", subtype=asset["mime_type"].split("/")[1],
                                cid="<" + asset["cid"] + ">", disposition="inline", filename=asset["filename"])
    else:
        message = alternative
    message["From"] = profile["delivery"]["sender"]
    message["To"] = to_header(state)
    message["Subject"] = f'{profile["title"]} · {profile["labels"]["issue"]} {number:03d} · {issue_key.rsplit("/", 1)[-1]}'
    message["Date"] = format_datetime(now)
    state["sender"] = profile["delivery"]["sender"]
    state["subject"] = str(message["Subject"])
    raw = message.as_bytes()
    verify(raw, state, markup, plain, assets)
    return raw, state


def verify(raw, delivery, markup, plain, assets):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    require(not message.defects, "Malformed MIME")
    require(all(len(message.get_all(header, [])) == 1 for header in ("From", "To", "Subject")), "Missing or repeated envelope headers")
    require(str(message["From"]).casefold() == delivery["sender"].casefold()
            and str(message["Subject"]) == delivery["subject"], "Sender or subject differs from prepared content")
    validate_envelope(delivery, str(message.get("To", "")), str(message.get("Cc", "")), str(message.get("Bcc", "")))
    require(message.get_content_type() == ("multipart/related" if assets else "multipart/alternative"), "Wrong MIME root")
    alternative = next(message.iter_parts()) if assets else message
    if assets:
        children = list(message.iter_parts())
        require(len(children) == 1 + len(assets) and all(x.get_content_maintype() == "image" for x in children[1:]),
                "Unexpected MIME root parts")
    require(alternative.get_content_type() == "multipart/alternative", "Missing plain/HTML alternative")
    parts = list(alternative.iter_parts())
    require([x.get_content_type() for x in parts] == ["text/plain", "text/html"], "Missing plain or HTML body")
    for part, expected in zip(parts, (plain, markup)):
        require(part.get_content().replace("\r\n", "\n").rstrip("\n") == expected.rstrip("\n"), "MIME body changed")
    found = {}
    for part in message.walk():
        if part.get_content_maintype() == "image":
            cid = str(part.get("Content-ID", "")).strip("<>")
            require(cid and cid not in found and part.get_content_disposition() == "inline", "Invalid inline CID")
            found[cid] = (part.get_content_type(), hashlib.sha256(part.get_payload(decode=True)).hexdigest())
    expected = {x["cid"]: (x["mime_type"], x["sha256"]) for x in assets}
    require(found == expected, "Inline image bytes or types differ")
    require(set(re.findall(r'src="cid:([^\"]+)"', markup)) == set(expected), "HTML CID mismatch")
