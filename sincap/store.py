"""Versioned local JSON store. One shared filesystem only; not a cross-Cloud database."""
import json
import os
from pathlib import Path
import tempfile

from .core import require


class LocalStore:
    def __init__(self, path):
        self.path = Path(path)
        require(not self.path.is_symlink() and all(not x.is_symlink() for x in self.path.parents),
                "State symlinks are forbidden")

    def create(self, data):
        require(isinstance(data, dict), "State data must be an object")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.path.open("xb") as stream:
            os.chmod(self.path, 0o600)
            stream.write(self.encode(0, data))
            stream.flush()
            os.fsync(stream.fileno())
        self.sync_parent()
        return self.read()

    @staticmethod
    def encode(version, data):
        return (json.dumps({"version": version, "data": data}, ensure_ascii=False,
                           sort_keys=True, indent=2) + "\n").encode()

    def read(self):
        require(not self.path.is_symlink(), "State symlinks are forbidden")
        result = json.loads(self.path.read_text(encoding="utf-8"))
        require(type(result.get("version")) is int and result["version"] >= 0
                and isinstance(result.get("data"), dict), "Invalid versioned state")
        return result

    def cas(self, expected_version, data):
        """Reserve before a provider call, then commit outcomes + history together.

        A leftover lock requires investigation. Never treat a timeout as permission
        to clear it, reset the ledger, or repeat a mail operation.
        """
        require(type(expected_version) is int and expected_version >= 0 and isinstance(data, dict), "Invalid CAS arguments")
        lock = self.path.with_name(self.path.name + ".lock")
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        temporary = None
        try:
            os.close(fd)
            current = self.read()
            require(current["version"] == expected_version, "State version conflict; reread and recompute")
            payload = self.encode(expected_version + 1, data)
            out, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".state-")
            with os.fdopen(out, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self.sync_parent()
            require(self.path.read_bytes() == payload, "State readback mismatch; reconcile before proceeding")
            return self.read()
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
            lock.unlink()

    def sync_parent(self):
        if os.name == "posix":
            fd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
