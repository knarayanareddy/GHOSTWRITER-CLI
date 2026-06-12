"""Best-effort secure erasure for session-ephemeral files."""

from __future__ import annotations

import logging
import os
import platform
import shutil
from pathlib import Path

LOG = logging.getLogger(__name__)
_WARNED = False


class Eraser:
    """Overwrite ephemeral files with random bytes before unlinking."""

    def erase_file(self, path: Path) -> None:
        target = path.expanduser()
        if not target.exists() or not target.is_file():
            return
        self._warn_if_copy_on_write_fs(target)
        try:
            size = target.stat().st_size
            with target.open("r+b", buffering=0) as fh:
                remaining = size
                chunk_size = 1024 * 1024
                while remaining > 0:
                    chunk = os.urandom(min(chunk_size, remaining))
                    fh.write(chunk)
                    remaining -= len(chunk)
                fh.flush()
                os.fsync(fh.fileno())
            target.unlink()
        except OSError as exc:
            LOG.warning("secure erase failed path_redacted=true error=%s", type(exc).__name__)
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass

    def erase_tree(self, path: Path) -> None:
        target = path.expanduser()
        if not target.exists():
            return
        if target.is_file():
            self.erase_file(target)
            return
        for child in sorted(target.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                self.erase_file(child)
            elif child.is_dir():
                try:
                    child.rmdir()
                except OSError:
                    pass
        try:
            target.rmdir()
        except OSError:
            shutil.rmtree(target, ignore_errors=True)

    @staticmethod
    def _warn_if_copy_on_write_fs(path: Path) -> None:
        global _WARNED
        if _WARNED:
            return
        fs = _filesystem_type(path)
        if fs in {"apfs", "btrfs", "zfs", "overlay"} or platform.system() == "Darwin":
            LOG.warning(
                "secure overwrite guarantees are reduced on SSD/COW filesystems; full-disk encryption is recommended fs=%s",
                fs or "unknown",
            )
            _WARNED = True


def _filesystem_type(path: Path) -> str | None:
    if platform.system() != "Linux":
        return "apfs" if platform.system() == "Darwin" else None
    try:
        mounts: list[tuple[str, str]] = []
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 3:
                    mounts.append((parts[1], parts[2]))
        resolved = str(path.resolve())
        best: tuple[str, str | None] = ("", None)
        for mount, fs in mounts:
            if resolved.startswith(mount) and len(mount) > len(best[0]):
                best = (mount, fs)
        return best[1]
    except OSError:
        return None
