"""Offline glue for an agent's Gmail and Library calls. No network or tool client."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path

from . import delivery, mime
from .core import digest, require


def new_installation(profile_id):
    return {"schema_version": 1, "profile_id": profile_id, "repository_remote": None, "repository_revision": None,
            "runtime": None, "mail": None,
            "shared_state": {"library_file_id": None, "probe_library_file_id": None, "last_observed_version": None,
                             "cross_task_test": "unverified"},
            "scheduler": {"automation_id": None, "target_verified": False,
                          "scheduled_test": "unverified"}}


def mail_connection(link_id, returned_profile):
    """Call only with the selected account's successful get_profile result."""
    require(isinstance(link_id, str) and link_id.strip(), "Use the discovered account link")
    email = returned_profile.get("email")
    delivery.snapshot([{"id": "self", "email": email}])
    return {"link_id": link_id, "email": email.casefold(),
            "checked_at": datetime.now(timezone.utc).isoformat()}


def _verify(bundle):
    state = bundle["delivery"]
    require(state["editorial_sha256"] == digest({"html": bundle["html"], "plain": bundle["plain"]}),
            "Prepared editorial hash differs")
    for asset in bundle["assets"]:
        require(hashlib.sha256(asset["data"]).hexdigest() == asset["sha256"], "Prepared image bytes differ")
    mime.verify(bundle["raw"], state, bundle["html"], bundle["plain"], bundle["assets"])


def load_bundle(directory):
    """Load a prepare output, including its persisted envelope and image hashes."""
    root = Path(directory)
    state = json.loads((root / "delivery.json").read_text(encoding="utf-8"))
    assets = []
    for item in state["assets"]:
        name = item["filename"]
        require(isinstance(name, str) and Path(name).name == name and name not in {".", ".."},
                "Invalid prepared asset filename")
        path = root / "assets" / name
        require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents), "Asset symlink forbidden")
        assets.append({**item, "data": path.read_bytes()})
    bundle = {"delivery": state, "assets": assets, "raw": (root / "newsletter.eml").read_bytes(),
              "html": (root / "newsletter.html").read_text(encoding="utf-8"),
              "plain": (root / "newsletter.txt").read_text(encoding="utf-8")}
    _verify(bundle)
    return bundle


def self_test_bundle(bundle, connection, test_key):
    """Retarget a reviewed preview to the verified sender only; never sends it."""
    _verify(bundle)
    require(isinstance(test_key, str) and test_key.startswith("test/") and "\n" not in test_key
            and "\r" not in test_key, "A unique test/ key is required")
    email = connection["email"]
    recipients = delivery.snapshot([{"id": "self", "email": email}])
    result = deepcopy(bundle)
    state = delivery.new_delivery(test_key, 1, recipients, bundle["delivery"]["editorial_sha256"])
    state.update(sender=email, subject="[TEST Sincap Post] " + test_key)
    message = BytesParser(policy=policy.SMTP).parsebytes(bundle["raw"])
    for header, value in (("From", email), ("To", email), ("Subject", state["subject"])):
        message.replace_header(header, value)
    result.update(delivery=state, raw=message.as_bytes())
    _verify(result)
    return result


def bundle_contract(bundle):
    """Small private manifest; persist raw MIME as a separate immutable file."""
    _verify(bundle)
    return {"delivery": deepcopy(bundle["delivery"]), "html": bundle["html"], "plain": bundle["plain"],
            "raw_sha256": hashlib.sha256(bundle["raw"]).hexdigest(),
            "assets": [{key: value for key, value in asset.items() if key != "data"} for asset in bundle["assets"]]}


def restore_bundle(raw, contract):
    """Rehydrate in a different task using exact retained bytes and contract."""
    require(hashlib.sha256(raw).hexdigest() == contract["raw_sha256"], "Retained MIME bytes differ")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    image_bytes = {str(part.get("Content-ID", "")).strip("<>"): part.get_payload(decode=True)
                   for part in message.walk() if part.get_content_maintype() == "image"}
    result = {key: deepcopy(contract[key]) for key in ("delivery", "html", "plain")}
    result.update(raw=raw, assets=[{**item, "data": image_bytes[item["cid"]]} for item in contract["assets"]])
    _verify(result)
    return result


def gmail_draft_args(bundle, connection):
    """Arguments for gmail_create_draft; pass programmatically, never print bytes."""
    _verify(bundle)
    require(bundle["delivery"]["sender"].casefold() == connection["email"].casefold(),
            "Prepared sender differs from the verified account")
    require(connection.get("link_id"), "Missing discovered account link")

    def part(node):
        result = {"mime_type": node.get_content_type()}
        if node.is_multipart():
            result["parts"] = [part(child) for child in node.iter_parts()]
        elif node.get_content_maintype() == "text":
            result.update(charset="utf-8", body={"content": node.get_content()})
        else:
            require(node.get_content_type() in {"image/png", "image/jpeg"}, "Unsupported inline type")
            result.update(body={"base64_url_content": base64.urlsafe_b64encode(node.get_payload(decode=True)).decode()},
                          content_disposition="inline", content_id=str(node["Content-ID"]),
                          filename=node.get_filename())
        return result

    state = bundle["delivery"]
    return {"link_id": connection["link_id"], "from_address": state["sender"],
            "to": delivery.to_header(state), "subject": state["subject"],
            "payload": part(BytesParser(policy=policy.default).parsebytes(bundle["raw"]))}


def verify_gmail_raw(bundle, raw_base64url):
    """Verify the provider's full raw message, not create_draft's success flag."""
    _verify(bundle)
    require(isinstance(raw_base64url, str) and raw_base64url, "Complete provider raw body required")
    raw = base64.b64decode(raw_base64url + "=" * (-len(raw_base64url) % 4), altchars=b"-_", validate=True)
    mime.verify(raw, bundle["delivery"], bundle["html"], bundle["plain"], bundle["assets"])
    return True


def library_candidate(snapshot, data, operation_id):
    """Domain version is separate from Library's provider version."""
    require(type(snapshot.get("version")) is int and snapshot["version"] >= 0
            and isinstance(snapshot.get("data"), dict) and isinstance(data, dict), "Complete state snapshot required")
    require(isinstance(operation_id, str) and operation_id.strip(), "Unique operation id required")
    return {"version": snapshot["version"] + 1, "data": deepcopy(data), "last_operation": operation_id}


def library_replace_args(file_id, provider_version, candidate_path):
    """Arguments for guarded replace; the agent obtains the exact current version."""
    require(isinstance(file_id, str) and file_id.strip(), "Use the returned Library file reference")
    require(type(provider_version) is int and provider_version >= 0, "Concrete integer provider version >= 0 required")
    path = Path(candidate_path).absolute()
    require(path.is_file() and not path.is_symlink() and all(not p.is_symlink() for p in path.parents),
            "Regular private candidate file required")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    require(type(candidate.get("version")) is int and candidate["version"] > 0
            and isinstance(candidate.get("data"), dict) and candidate.get("last_operation"), "Invalid CAS candidate")
    return {"library_file_id": file_id, "file": str(path), "expected_current_version": provider_version}


def verify_library_commit(candidate, complete_readback, before_version, after_version):
    require(type(before_version) is int and before_version >= 0 and type(after_version) is int
            and after_version > before_version, "No newer provider version was read")
    require(digest(candidate) == digest(complete_readback), "Remote readback differs; reconcile before continuing")
    require(candidate.get("last_operation"), "Missing committed operation id")
    return True


def reserve_bundle(snapshot, bundle, attempt_id):
    """Build one CAS candidate. Only its successful remote readback permits send."""
    _verify(bundle)
    state = bundle["delivery"]
    data = deepcopy(snapshot["data"])
    for name in ("deliveries", "test_deliveries"):
        require(not any(row["status"] in {"sending", "send_uncertain", "partial_uncertain"}
                        for row in data.get(name, {}).values()), "Reconcile the outstanding send first")
    bucket = data.setdefault("test_deliveries" if state["issue_key"].startswith("test/") else "deliveries", {})
    require(state["issue_key"] not in bucket, "Issue already recorded; reconcile instead of creating another draft/send")
    bucket[state["issue_key"]] = delivery.reserve(state, attempt_id)
    return library_candidate(snapshot, data, attempt_id)


def scheduled_test_prompt(library_file_id, repository_revision, test_key):
    """Private prompt for a scheduler that can actually reach this project's runtime."""
    require(all(isinstance(x, str) and x.strip() for x in (library_file_id, repository_revision, test_key))
            and test_key.startswith("test/"), "Recorded state/revision and test key required")
    return ("Sincap Post kurulumunun tek seferlik scheduled self-test aşamasını yürüt. "
            "docs/onboarding.md içindeki scheduled test adımlarını izle. "
            f"Kanonik Library kaydı: {library_file_id}; beklenen repo sürümü: {repository_revision}; "
            f"test anahtarı: {test_key}. Gerçek tetiklenme saatini ve runtime/repo kimliğini doğrula. "
            "Repo/shell, aynı tam kayıt, sürüm korumalı CAS, doğru hesap veya açık test yetkisi yoksa "
            "mail göndermeden somut engeli bildir. Kayıttaki gerçek saat kapısını uygula. "
            "Yalnız doğrulanmış gönderenin kendi adresine, bu test anahtarı için tek taslak/gönderim. "
            "Önce mevcut test sonucunu oku; sending/sent/uncertain kaydında tekrar gönderme. "
            "Provider ve Sent kanıtını aynı kayda CAS ile işle; üretim geçmişini/sayısını ilerletme. "
            "Başka proje, hesap, dispatcher veya otomasyon devralma. Düzenli yayını kendiliğinden açma.")
