"""Offline commands: init, doctor, prepare. No send or schedule command exists."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys

from .core import capability_gaps, digest, instant, new_history, require, select_articles, validate_profile
from .mime import package
from .onboarding import new_installation
from .render import render
from .store import LocalStore

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    if isinstance(data, dict):
        data = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data.encode() if isinstance(data, str) else data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create fresh local config; never overwrite existing state")
    init.add_argument("--directory", type=Path, default=Path(".local"))
    init.add_argument("--profile-id", default="my-newsletter")
    doctor = commands.add_parser("doctor", help="Check local prerequisites and recorded capability evidence")
    doctor.add_argument("--profile", type=Path, default=Path(".local/profile.json"))
    doctor.add_argument("--capabilities", type=Path, default=Path(".local/capabilities.json"))
    doctor.add_argument("--stage", choices=("preview", "self-test", "scheduled"), default="preview")
    prepare = commands.add_parser("prepare", help="Validate fresh agent-written input and create offline artifacts")
    prepare.add_argument("--profile", type=Path, default=Path(".local/profile.json"))
    prepare.add_argument("--input", type=Path, required=True)
    prepare.add_argument("--state", type=Path)
    prepare.add_argument("--images-root", type=Path, default=Path(".local/images"))
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--demo", action="store_true")
    prepare.add_argument("--at", help="Synthetic demo clock only; ISO timestamp with timezone")
    args = parser.parse_args()
    try:
        if args.command == "init":
            require(not args.directory.exists(), "Directory exists; inspect and preserve its current state")
            initial_profile = load(ROOT / "examples/profile.json")
            initial_profile["id"] = args.profile_id
            validate_profile(initial_profile)
            args.directory.mkdir(parents=True, mode=0o700)
            write(args.directory / "profile.json", initial_profile)
            write(args.directory / "capabilities.json", load(ROOT / "examples/capabilities.json"))
            write(args.directory / "installation.json", new_installation(args.profile_id))
            LocalStore(args.directory / "state.json").create({"profile_id": args.profile_id, "history": new_history(), "deliveries": {}})
            print("Local synthetic config created. Delivery and scheduling are disabled. No apps checked.")
            return 0
        profile = validate_profile(load(args.profile))
        now = datetime.now(timezone.utc)
        if args.command == "doctor":
            record = load(args.capabilities) if args.capabilities.exists() else {"schema_version": 1}
            gaps = capability_gaps(record, args.stage, now, profile)
            report = {"offline_profile": "valid", "stage": args.stage, "capability_gaps": gaps,
                      "image_decoder": "available" if importlib.util.find_spec("PIL") else "unavailable",
                      "delivery_enabled": profile["delivery"]["enabled"], "schedule_enabled": profile["schedule"]["enabled"],
                      "remote_probe_performed": False, "profile_sha256": digest(profile),
                      "meaning": "Recorded evidence only; agent must actually verify apps and this runtime."}
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2 if gaps else 0
        require(args.demo or args.at is None, "Clock override is allowed only with --demo")
        if args.at:
            now = instant(args.at)
        require(args.demo or args.state is not None, "Production preparation requires the existing canonical state")
        issue = load(args.input)
        if args.state:
            state = LocalStore(args.state).read()["data"]
            require(state["profile_id"] == profile["id"], "State belongs to another profile")
            require(not any(x["status"] in {"sending", "send_uncertain", "partial_uncertain"}
                            for x in state["deliveries"].values()), "Resolve the uncertain delivery before preparing another issue")
            history = state["history"]
        else:
            history = new_history()
        articles, omitted, issue_key = select_articles(profile, issue, history, now, demo=args.demo)
        markup, plain, assets, words = render(profile, issue, articles, history["next_issue_number"], args.images_root)
        raw, delivery = package(profile, issue_key, history["next_issue_number"], markup, plain, assets, now)
        require(not args.out.exists(), "Output exists; choose a new run directory instead of overwriting")
        args.out.mkdir(parents=True, mode=0o700)
        preview = markup
        if assets:
            (args.out / "assets").mkdir(mode=0o700)
        for asset in assets:
            write(args.out / "assets" / asset["filename"], asset["data"])
            preview = preview.replace("cid:" + asset["cid"], "assets/" + asset["filename"])
        write(args.out / "preview.html", preview)
        write(args.out / "newsletter.html", markup)
        write(args.out / "newsletter.txt", plain)
        write(args.out / "newsletter.eml", raw)
        delivery["assets"] = [{key: value for key, value in asset.items() if key != "data"} for asset in assets]
        write(args.out / "delivery.json", delivery)
        write(args.out / "report.json", {"schema_version": 1, "synthetic": args.demo, "issue_key": issue_key,
              "word_count": words, "article_ids": [x["id"] for x in articles], "omitted": omitted,
              "inline_images": len(assets), "editorial_sha256": delivery["editorial_sha256"],
              "history_changed": False, "provider_draft_created": False, "sent": False})
        print(json.dumps({"result": "offline_preview_only", "synthetic": args.demo, "articles": len(articles),
                          "words": words, "inline_images": len(assets), "sent": False}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, "FAIL: " + str(exc) + "\n")


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        raise SystemExit("Python 3.9+ is required")
    sys.exit(main())
