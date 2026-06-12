"""Logging setup with privacy-preserving sanitization."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(token|api[_-]?key|password|secret|cookie)(\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(Authorization\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(sessionid|connect\.sid|jwt)(\s*[:=]\s*)[^\s,;]+"),
)
PATH_PATTERN = re.compile(r"(?<![\w.-])/(?:Users|home|tmp|private|var)/[^\s,;:]+")


class SanitizingFormatter(logging.Formatter):
    """Formatter that redacts credentials, prompts, and private paths."""

    def __init__(self) -> None:
        super().__init__(fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802 - logging API name
        return datetime.fromtimestamp(record.created, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def sanitize(value: object) -> str:
        text = str(value)
        for pattern in TOKEN_PATTERNS:
            text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2) if len(m.groups()) > 1 else ''}<redacted>", text)
        text = PATH_PATTERN.sub("<path-redacted>", text)
        return text

    def format(self, record: logging.LogRecord) -> str:
        original_msg = record.msg
        original_args = record.args
        record.msg = self.sanitize(record.getMessage())
        record.args = ()
        try:
            return super().format(record)
        finally:
            record.msg = original_msg
            record.args = original_args


class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def configure_logging(level: str = "info", log_file: Path | None = None) -> None:
    """Configure root logger. Logs are stderr by default; optional file sink."""

    numeric = getattr(logging, level.upper(), logging.INFO)
    formatter = SanitizingFormatter()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(numeric)

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    stream.setLevel(numeric)
    root.addHandler(stream)

    if log_file is not None:
        path = log_file.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(formatter)
        fh.setLevel(numeric)
        root.addHandler(fh)


def redact_many(values: Iterable[object]) -> list[str]:
    return [SanitizingFormatter.sanitize(v) for v in values]
