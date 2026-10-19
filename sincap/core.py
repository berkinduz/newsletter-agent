"""Pure validation and selection. Source reading and durable persistence are adapters."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from .delivery import snapshot


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(record, key):
    value = record.get(key)
    require(isinstance(value, str) and value.strip(), "Missing text: " + key)
    return value


def instant(value):
    require(isinstance(value, str), "Timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def public_url(value):
    require(isinstance(value, str) and not any(c.isspace() for c in value), "Invalid URL")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    require(parsed.scheme == "https" and "." in host and not parsed.username
            and not parsed.password and parsed.port in {None, 443}, "Public HTTPS URL required")
    require(not host.endswith((".local", ".internal", ".localhost")), "Private hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        require(address.is_global, "Private IP address")
    require(not any(re.search(r"token|secret|auth|signature|api.?key|^x-amz-", key, re.I)
                    for key, _ in parse_qsl(parsed.query)), "Credential-bearing URL")
    return parsed


def canonical_url(value):
    parsed = public_url(value)
    query = sorted((key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=True)
                   if not key.lower().startswith("utm_")
                   and key.lower() not in {"fbclid", "gclid"})
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", parsed.hostname.lower(), path, urlencode(query), ""))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def validate_profile(profile):
    require(profile.get("schema_version") == 1, "Unknown profile schema")
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", text(profile, "id")), "Invalid profile id")
    for key in ("title", "language", "greeting"):
        text(profile, key)
    ZoneInfo(text(profile, "timezone"))
    for field in ("topics", "sources"):
        rows = profile.get(field)
        require(isinstance(rows, list) and rows and all(isinstance(x, dict) for x in rows),
                "Nonempty list required: " + field)
        ids = [text(row, "id") for row in rows]
        require(len(ids) == len(set(ids)), "Duplicate " + field + " id")
    for topic in profile["topics"]:
        text(topic, "title")
        require(type(topic.get("visual_priority")) is bool, "Visual preference required")
    for source in profile["sources"]:
        text(source, "name")
        source_host = public_url(text(source, "url")).hostname
        article_hosts = source.get("article_hosts", [source_host])
        require(isinstance(article_hosts, list) and article_hosts and all(isinstance(x, str) and x
                and public_url("https://" + x).hostname == x for x in article_hosts), "Invalid article hosts")
        require(type(source.get("enabled")) is bool, "Source enabled flag required")
        require(type(source.get("priority")) is int and source["priority"] > 0, "Invalid source priority")
    excluded = profile.get("excluded_sources")
    require(isinstance(excluded, list) and all(isinstance(x, str) for x in excluded), "Excluded sources required")
    length = profile["length"]
    for key in ("target_minutes", "min_words", "max_words", "max_articles"):
        require(type(length.get(key)) is int and length[key] > 0, "Invalid length: " + key)
    require(length["min_words"] <= length["max_words"], "Invalid word range")
    hours = profile["freshness"].get("initial_lookback_hours")
    require(type(hours) is int and 1 <= hours <= 168, "Lookback must be 1–168 hours")
    require(type(profile["images"].get("enabled")) is bool, "Image preference required")
    signature = profile.get("signature")
    require(isinstance(signature, list) and signature and all(isinstance(x, str) and x.strip()
            for x in signature), "Signature lines required")
    for key in ("issue", "source", "comment", "minutes", "links_extra"):
        text(profile["labels"], key)
    delivery = profile["delivery"]
    require(type(delivery.get("enabled")) is bool, "Delivery flag required")
    snapshot([{"id": "sender", "email": delivery["sender"]}])
    snapshot(delivery["recipients"])
    schedule = profile["schedule"]
    require(type(schedule.get("enabled")) is bool, "Schedule flag required")
    require(bool(re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", schedule.get("daily_at", ""))),
            "Daily time must be HH:MM")
    return profile


def new_history():
    return {"schema_version": 1, "last_cutoff": None, "next_issue_number": 1,
            "published": [], "issue_keys": []}


def article_keys(article):
    keys = {"url:" + canonical_url(text(article, "url")), "event:" + text(article, "event_key")}
    doi = article.get("doi")
    if doi:
        doi = doi.lower().removeprefix("https://doi.org/").removeprefix("doi:")
        require(bool(re.fullmatch(r"10\.[0-9]{4,9}/\S+", doi)), "Invalid DOI")
        keys.add("doi:" + doi)
    return keys


def select_articles(profile, issue, history, now, demo=False):
    validate_profile(profile)
    require(issue.get("schema_version") == 1 and history.get("schema_version") == 1, "Unknown issue/history schema")
    require(type(issue.get("synthetic")) is bool, "Synthetic flag required")
    require(demo == issue["synthetic"], "Use --demo only for synthetic input")
    require(issue.get("language") == profile["language"], "Issue language differs from profile")
    today = now.astimezone(ZoneInfo(profile["timezone"])).date()
    require(date.fromisoformat(issue["issue_date"]) == today, "Issue must belong to today's profile timezone")
    issue_key = profile["id"] + "/" + today.isoformat()
    require(issue_key not in history["issue_keys"], "This daily issue is already published")
    cutoff = instant(history["last_cutoff"]) if history["last_cutoff"] else (
        now - timedelta(hours=profile["freshness"]["initial_lookback_hours"]))
    researched = instant(issue["researched_at"])
    require(cutoff < researched <= now, "New research after the last successful cutoff is required")
    require(type(history["next_issue_number"]) is int and history["next_issue_number"] > 0, "Invalid issue counter")
    sources = {x["id"]: x for x in profile["sources"]}
    topics = {x["id"] for x in profile["topics"]}
    rows = issue.get("articles")
    require(isinstance(rows, list) and all(isinstance(x, dict) for x in rows), "Articles must be objects")
    ids = [text(row, "id") for row in rows]
    require(len(ids) == len(set(ids)), "Duplicate article id")
    selected, omitted, used = [], [], set()
    ordered = sorted(rows, key=lambda x: sources.get(x.get("source_id"), {}).get("priority", 999999))
    for article in ordered:
        reason = None
        source = sources.get(article.get("source_id"))
        if not source or not source["enabled"] or article["source_id"] in profile["excluded_sources"]:
            reason = "source_disabled_or_unknown"
        elif article.get("topic") not in topics:
            reason = "topic_not_selected"
        elif article.get("body_read") is not True or not article.get("read_note"):
            reason = "body_not_verified"
        else:
            host = public_url(text(article, "url")).hostname
            source_host = public_url(source["url"]).hostname
            require(host in source.get("article_hosts", [source_host]), "Article host differs from selected source")
            require(demo or not any(x.endswith(".invalid") for x in (host, source_host)),
                    "Synthetic source cannot be used in production preparation")
            text(article, "read_note")
            for key in ("kind", "title", "summary", "revision"):
                text(article, key)
            keys = article_keys(article)
            published = instant(article["published_at"])
            require(published <= researched, "Publication is later than the recorded research")
            changed = article.get("new_development") is True
            eligible_date = published
            if changed:
                text(article, "development_note")
                eligible_date = instant(article["updated_at"])
                require(published <= eligible_date <= researched, "Invalid development date")
            previous = [entry for entry in history["published"] if keys & set(entry["keys"])]
            if eligible_date <= cutoff:
                reason = "outside_freshness_window"
            elif keys & used:
                reason = "duplicate_in_issue"
            elif previous and (not changed or any(entry["revision"] == article["revision"] for entry in previous)):
                reason = "already_published"
            elif len(selected) >= profile["length"]["max_articles"]:
                reason = "article_limit"
            else:
                used.update(keys)
                selected.append(deepcopy(article))
        if reason:
            omitted.append({"id": article["id"], "reason": reason})
    require(selected, "No readable, fresh, distinct articles; do not recycle yesterday's issue")
    return selected, omitted, issue_key


def record_publication(history, issue_key, researched_at, articles, delivery):
    """Pure state transition. Adapter commits it with delivery + counter in one CAS."""
    require(delivery["issue_key"] == issue_key, "Delivery issue mismatch")
    require(delivery["number_advanced"] is True, "Confirmed provider result required")
    require(any(x["status"] == "provider_accepted" for x in delivery["outcomes"].values()),
            "No confirmed provider acceptance")
    if issue_key in history["issue_keys"]:
        return deepcopy(history)
    require(history["next_issue_number"] == delivery["issue_number"], "Issue counter conflict")
    result = deepcopy(history)
    cutoff = instant(researched_at)
    require(not history["last_cutoff"] or cutoff > instant(history["last_cutoff"]), "Cutoff cannot regress")
    result["last_cutoff"] = cutoff.isoformat()
    result["next_issue_number"] += 1
    result["issue_keys"].append(issue_key)
    result["published"].extend({"keys": sorted(article_keys(x)), "revision": x["revision"],
                                 "issue_key": issue_key} for x in articles)
    return result


REQUIREMENTS = {
    "preview": (),
    "self-test": ("source_access", "html_preview", "mail_identity", "mail_draft_roundtrip", "durable_state"),
    "scheduled": ("source_access", "html_preview", "mail_identity", "mail_draft_roundtrip",
                  "durable_state", "self_test_delivery", "scheduler_execution"),
}


def capability_gaps(record, stage, now, profile=None):
    """Validate agent-recorded evidence; this function never probes connected apps."""
    require(record.get("schema_version") == 1, "Unknown capability schema")
    gaps = []
    if stage != "preview" and not all(record.get("context", {}).get(key)
                                     for key in ("runtime", "repository_revision")):
        gaps.append("runtime_and_repository_unverified")
    if stage != "preview" and profile is not None and record.get("context", {}).get("profile_sha256") != digest(profile):
        gaps.append("profile_evidence_mismatch")
    for name in REQUIREMENTS[stage]:
        check = record.get("checks", {}).get(name, {})
        if check.get("status") != "verified" or not check.get("evidence"):
            gaps.append(name + ":unverified")
            continue
        try:
            age = now - instant(check["checked_at"])
            require(timedelta(0) <= age <= timedelta(hours=24), "Stale evidence")
        except (ValueError, KeyError, TypeError):
            gaps.append(name + ":stale_or_invalid")
    return gaps
