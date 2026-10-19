"""Offline shared-issue recipient and send-attempt guards; caller must persist atomically before any provider action."""
from copy import deepcopy
from datetime import datetime
from email.utils import getaddresses
import hashlib
import json
import re
from zoneinfo import ZoneInfo


class DeliveryError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise DeliveryError(message)


def snapshot(recipients):
    require(isinstance(recipients, list) and recipients, "Recipient list required")
    result = []
    ids, emails = set(), set()
    for recipient in recipients:
        rid, email = recipient.get("id"), recipient.get("email")
        require(isinstance(rid, str) and rid.strip() and rid not in ids, "Unique recipient id required")
        require(isinstance(email, str) and not any(c in email for c in "\r\n"), "Invalid address")
        parsed = getaddresses([email])
        require(len(parsed) == 1 and parsed[0][1] == email and email.count("@") == 1
                and not any(c.isspace() for c in email) and "." in email.rsplit("@", 1)[1],
                "Bare verified address required")
        email = email.casefold()
        require(email not in emails, "Duplicate recipient address")
        ids.add(rid)
        emails.add(email)
        result.append({"id": rid, "email": email})
    return result


def new_delivery(issue_key, issue_number, recipients, editorial_sha256):
    require(isinstance(issue_key, str) and issue_key, "Issue key required")
    require(type(issue_number) is int and issue_number > 0, "Issue number required")
    require(bool(re.fullmatch(r"[a-f0-9]{64}", editorial_sha256)), "Editorial content hash required")
    recipients = snapshot(recipients)
    digest = hashlib.sha256(json.dumps(sorted(recipients, key=lambda x: x["id"]),
                                    sort_keys=True).encode()).hexdigest()
    return {"issue_key": issue_key, "issue_number": issue_number,
            "editorial_sha256": editorial_sha256, "strategy": "shared_envelope",
            "recipients": recipients, "recipient_set_hash": digest, "status": "prepared",
            "outcomes": {x["id"]: {"status": "pending"} for x in recipients},
            "attempts": [], "number_advanced": False}


def eligible_recipient_ids(state):
    if any(x["status"] in {"sending", "uncertain"} for x in state["attempts"]):
        return []
    return [x["id"] for x in state["recipients"]
            if state["outcomes"][x["id"]]["status"] in {"pending", "definitively_rejected"}]


def to_header(state, recipient_ids=None):
    scope = recipient_ids if recipient_ids is not None else [x["id"] for x in state["recipients"]]
    require(scope and len(scope) == len(set(scope)), "Unique envelope scope required")
    require(set(scope) <= set(state["outcomes"]), "Unknown envelope recipient")
    return ", ".join(x["email"] for x in state["recipients"] if x["id"] in scope)


def validate_envelope(state, to, cc="", bcc="", recipient_ids=None):
    require(not cc and not bcc, "Unexpected Cc/Bcc")
    require(isinstance(to, str) and not any(c in to for c in "\r\n"), "Invalid To header")
    expected = [email.casefold() for _, email in getaddresses([to_header(state, recipient_ids)])]
    actual = [email.casefold() for _, email in getaddresses([to])]
    require(len(actual) == len(expected) and set(actual) == set(expected), "Draft/Sent recipient scope mismatch")


def reserve(state, attempt_id, recipient_ids=None):
    require(isinstance(attempt_id, str) and attempt_id, "Attempt id required")
    require(not any(x["attempt_id"] == attempt_id for x in state["attempts"]),
            "Attempt already reserved; reconcile instead of sending again")
    eligible = eligible_recipient_ids(state)
    scope = eligible if recipient_ids is None else recipient_ids
    require(eligible and set(scope) == set(eligible) and len(scope) == len(set(scope)),
            "Send scope must contain only all pending/definitively rejected recipients")
    result = deepcopy(state)
    result["attempts"].append({"attempt_id": attempt_id, "recipient_ids": list(scope), "status": "sending"})
    result["status"] = "sending"
    return result


def record_result(state, attempt_id, outcomes, reconcile=False):
    attempt = next((x for x in state["attempts"] if x["attempt_id"] == attempt_id), None)
    require(attempt is not None and set(outcomes) == set(attempt["recipient_ids"]), "Attempt scope mismatch")
    if attempt.get("result") == outcomes:
        return deepcopy(state)
    require("result" not in attempt or (reconcile and attempt["status"] == "uncertain"),
            "Conflicting attempt result")
    for rid, outcome in outcomes.items():
        status = outcome.get("status")
        require(status in {"provider_accepted", "definitively_rejected", "uncertain"}, "Unknown outcome")
        require(isinstance(outcome.get("evidence"), str) and outcome["evidence"].strip(), "Outcome evidence required")
        if status == "provider_accepted":
            require(outcome.get("sent_verified") is True and outcome.get("provider_message_id"),
                    "Provider id and matching Sent proof required")
        if status == "definitively_rejected":
            require(outcome.get("definitive_rejection") is True, "Definitive non-acceptance proof required")
        if attempt.get("result", {}).get(rid, {}).get("status") == "provider_accepted":
            require(attempt["result"][rid] == outcome, "Confirmed recipient outcome cannot be overwritten")
    result = deepcopy(state)
    current = next(x for x in result["attempts"] if x["attempt_id"] == attempt_id)
    current["result"] = deepcopy(outcomes)
    current["status"] = "uncertain" if any(x["status"] == "uncertain" for x in outcomes.values()) else "resolved"
    result["outcomes"].update(deepcopy(outcomes))
    statuses = [x["status"] for x in result["outcomes"].values()]
    if "uncertain" in statuses:
        result["status"] = "partial_uncertain" if "provider_accepted" in statuses else "send_uncertain"
    elif all(x == "provider_accepted" for x in statuses):
        result["status"] = "sent"
    elif "provider_accepted" in statuses:
        result["status"] = "partial"
    else:
        result["status"] = "failed"
    return result


def advance_once(state, next_issue_number):
    result = deepcopy(state)
    if result["number_advanced"]:
        return result, next_issue_number
    if any(x["status"] == "provider_accepted" for x in result["outcomes"].values()):
        require(next_issue_number == result["issue_number"], "Issue counter conflict")
        result["number_advanced"] = True
        return result, next_issue_number + 1
    return result, next_issue_number


def assert_send_allowed(profile, issue_key, now, user_authorized=False, self_test=False, scheduled=False):
    """An additional offline guard, never a substitute for actual user/tool approval."""
    require(user_authorized is True, "Explicit user authorization required")
    require(isinstance(now, datetime) and now.tzinfo is not None, "Real timezone-aware clock required")
    if self_test:
        recipients = snapshot(profile["delivery"]["recipients"])
        require(issue_key.startswith("test/") and len(recipients) == 1
                and recipients[0]["email"] == profile["delivery"]["sender"].casefold(),
                "Self-test must use test state and the verified sender's own address")
        return
    require(profile["delivery"]["enabled"] is True, "Production delivery disabled")
    if scheduled:
        require(profile["schedule"]["enabled"] is True, "Regular scheduling disabled")
    local = now.astimezone(ZoneInfo(profile["timezone"]))
    require(issue_key == profile["id"] + "/" + local.date().isoformat(), "Wrong daily issue key")
    hour, minute = map(int, profile["schedule"]["daily_at"].split(":"))
    require((local.hour, local.minute) >= (hour, minute), "Before configured delivery time")
