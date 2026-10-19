#!/usr/bin/env python3
"""Allowlist, text/secret checks and SHA256 manifest. Offline; prints no matched secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = re.compile(r"[A-Za-z0-9_.+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PATTERNS = {
    "private path": re.compile(r"[/]Users/[^\s/]+/|[/]workspace/(?:shared|library-files)/"),
    "live service identifier": re.compile(r"\b(?:libfile|link|thread|ccarenv|cecfg|jawbone|sched|automation)_[A-Za-z0-9_-]{12,}\b", re.I),
    "UUID identifier": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "provider credential": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|ya29\.[A-Za-z0-9_-]{20,})\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "credential assignment": re.compile(r'''(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)["']?\s*[:=]\s*["'][A-Za-z0-9_+/.=-]{12,}["']''', re.I),
    "embedded binary or opaque payload": re.compile(r"[A-Za-z0-9+/=_-]{512,}"),
}


def scan_text(name, content):
    errors = []
    if len(content) > 65536:
        errors.append(name + ": source exceeds 64 KiB")
    try:
        value = content.decode("utf-8")
    except UnicodeDecodeError:
        return [name + ": non-UTF-8 source"]
    if "\0" in value:
        errors.append(name + ": binary NUL")
    for match in ADDRESS.finditer(value):
        if match.group(1).lower() != "example.invalid":
            errors.append(name + ": non-synthetic email address")
            break
    for label, pattern in PATTERNS.items():
        if pattern.search(value):
            errors.append(name + ": possible " + label)
    return errors


def run_git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def inspect(root=ROOT, staged=False):
    errors, files = [], {}
    if staged:
        manifest = run_git(root, "show", ":MANIFEST.txt").decode()
    else:
        manifest = (root / "MANIFEST.txt").read_text(encoding="utf-8")
    names = [x.strip() for x in manifest.splitlines() if x.strip() and not x.startswith("#")]
    if len(names) != len(set(names)) or not names:
        errors.append("Manifest must have unique explicit paths")
    allowed = set(names)
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or name.startswith(".git/") or name.startswith(".local/"):
            errors.append("Invalid manifest path")
            continue
        if staged:
            modes = run_git(root, "ls-files", "-s", "--", name).decode().split()
            if not modes or modes[0] != "100644":
                errors.append(name + ": missing regular staged text file")
                continue
            files[name] = run_git(root, "show", ":" + name)
        else:
            actual = root / name
            if actual.is_symlink() or any(x.is_symlink() for x in actual.parents):
                errors.append(name + ": symlink")
            elif not actual.is_file():
                errors.append(name + ": missing source")
            else:
                files[name] = actual.read_bytes()
    if staged:
        tracked = set(run_git(root, "ls-files", "-z").decode().strip("\0").split("\0")) - {""}
        errors.extend(name + ": tracked outside allowlist" for name in sorted(tracked - allowed))
    else:
        for directory, dirs, filenames in os.walk(root):
            for name in list(dirs):
                path = Path(directory) / name
                if name in {".git", ".local", "__pycache__"}:
                    dirs.remove(name)
                elif path.is_symlink():
                    errors.append(str(path.relative_to(root)) + ": directory symlink")
                    dirs.remove(name)
            for name in filenames:
                relative = (Path(directory) / name).relative_to(root).as_posix()
                if relative not in allowed:
                    errors.append(relative + ": file outside distribution allowlist")
        if (root / ".git").is_dir():
            tracked = set(run_git(root, "ls-files", "-z").decode().strip("\0").split("\0")) - {""}
            errors.extend(name + ": tracked outside allowlist" for name in sorted(tracked - allowed))
    for name, content in files.items():
        errors.extend(scan_text(name, content))
    ignore = files.get(".gitignore", b"").decode("utf-8", errors="replace")
    ignore_lines = set(ignore.splitlines())
    if "*" not in ignore_lines or any("!/" + name not in ignore_lines for name in names):
        errors.append("Git ignore must explicitly allow each manifest file")
    for name in ("examples/profile.json", "examples/capabilities.json", "examples/issue.json"):
        try:
            example = json.loads(files[name])
            if name.endswith("profile.json") and (example["delivery"]["enabled"] is not False or example["schedule"]["enabled"] is not False):
                errors.append("Example sending and scheduling must be disabled")
            if name.endswith("issue.json") and example["synthetic"] is not True:
                errors.append("Example issue must be synthetic")
            if name.endswith("capabilities.json") and any(check["status"] != "unverified" for check in example["checks"].values()):
                errors.append("Example capabilities must remain unverified")
        except (ValueError, KeyError, TypeError):
            errors.append(name + ": invalid or missing example")
    report = [{"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
              for name, content in sorted(files.items())]
    return sorted(set(errors)), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--manifest", action="store_true", help="Print the complete reviewed SHA256 manifest as JSON")
    args = parser.parse_args()
    try:
        errors, report = inspect(staged=args.staged)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, "FAIL: Cannot inspect distribution: " + str(exc) + "\n")
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        return 1
    if args.manifest:
        print(json.dumps({"scope": "staged" if args.staged else "working_tree", "files": report}, indent=2))
    else:
        print(f"PASS: {len(report)} allowlisted UTF-8 sources; offline privacy checks only. Manual review still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
