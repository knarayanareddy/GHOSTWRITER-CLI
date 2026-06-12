"""Shared dataclasses for GhostWriter components."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVED = "APPROVED"
GENERATED = "GENERATED"
EDITED = "EDITED"
REJECTED = "REJECTED"
PUBLISHED = "PUBLISHED"


@dataclass(frozen=True)
class VoiceProfile:
    """Persisted voice/style metrics, never corpus text."""

    schema_version: str
    created_at: str
    corpus_hash: str
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "corpus_hash": self.corpus_hash,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceProfile:
        return cls(
            schema_version=str(data["schema_version"]),
            created_at=str(data["created_at"]),
            corpus_hash=str(data["corpus_hash"]),
            metrics=dict(data.get("metrics", {})),
        )

    @classmethod
    def load(cls, path: Path) -> VoiceProfile:
        with path.expanduser().open("r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def save(self, path: Path) -> None:
        target = path.expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")
        tmp.replace(target)


@dataclass(frozen=True)
class ApprovedDraft:
    """Draft that has passed the explicit approval gate."""

    content: str
    platforms: list[str]
    state: str = APPROVED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    idempotency_key: str = ""

    def __post_init__(self) -> None:
        if self.state != APPROVED:
            raise ValueError("ApprovedDraft requires state='APPROVED'")
        if not self.idempotency_key:
            bucket = self.created_at[:16]  # minute bucket is stable for retries.
            seed = f"{self.content}|{','.join(sorted(self.platforms))}|{bucket}".encode()
            object.__setattr__(self, "idempotency_key", hashlib.sha256(seed).hexdigest())

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "platforms": self.platforms,
            "state": self.state,
            "created_at": self.created_at,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovedDraft:
        return cls(
            content=str(data["content"]),
            platforms=list(data.get("platforms", [])),
            state=str(data.get("state", APPROVED)),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            idempotency_key=str(data.get("idempotency_key", "")),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
            fh.write("\n")
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> ApprovedDraft:
        with path.open("r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


@dataclass(frozen=True)
class PublishResult:
    """Non-throwing publisher result."""

    platform: str
    success: bool
    url: str | None = None
    error: str | None = None
    status_code: int | None = None
    attempts: int = 1
    partial: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
