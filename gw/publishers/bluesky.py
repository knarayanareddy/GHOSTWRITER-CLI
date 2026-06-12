"""Bluesky AT Protocol publisher."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from gw.models import ApprovedDraft, PublishResult
from gw.publishers.base import HttpPublisherBase

LOG = logging.getLogger(__name__)

try:
    import grapheme
except Exception:  # noqa: BLE001
    grapheme = None

BLUESKY_BASE = "https://bsky.social"
URL_RE = re.compile(r"https?://[^\s<>()]+[^\s<>().,!?;:'\"]")
MENTION_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z][A-Za-z0-9.-]*)")


class BlueskyPublisher(HttpPublisherBase):
    platform = "bluesky"

    def publish(self, draft: ApprovedDraft) -> PublishResult:
        try:
            creds = self.credential_store.get(self.platform)
            handle = creds["handle"]
            app_password = creds["app_password"]
            if grapheme_len(draft.content) > 300:
                return PublishResult(platform=self.platform, success=False, error="Bluesky content exceeds 300 graphemes.")
            if self.dry_run:
                return PublishResult(platform=self.platform, success=True, attempts=0, metadata={"dry_run": True})
            session = self.client.post(
                f"{BLUESKY_BASE}/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": app_password},
            )
            if session.status_code >= 400:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=f"HTTP {session.status_code}",
                    status_code=session.status_code,
                )
            sdata = session.json()
            access_jwt = sdata["accessJwt"]
            did = sdata["did"]
            rkey = (
                datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                + "-"
                + hashlib.sha256(draft.idempotency_key.encode()).hexdigest()[:8]
            )
            facets = build_facets(draft.content, self.client)

            def send():  # type: ignore[no-untyped-def]
                record: dict[str, Any] = {
                    "$type": "app.bsky.feed.post",
                    "text": draft.content,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                if facets:
                    record["facets"] = facets
                return self.client.post(
                    f"{BLUESKY_BASE}/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": f"Bearer {access_jwt}"},
                    json={
                        "repo": did,
                        "collection": "app.bsky.feed.post",
                        "rkey": rkey,
                        "record": record,
                    },
                )

            response, attempts, error = self._retry_request(draft, send)
            if response is None or response.status_code >= 400:
                return PublishResult(
                    platform=self.platform,
                    success=False,
                    error=self._error_from_response(response, error),
                    status_code=response.status_code if response else None,
                    attempts=attempts,
                )
            data = response.json()
            return PublishResult(
                platform=self.platform,
                success=True,
                url=str(data.get("uri")) if data.get("uri") else None,
                attempts=attempts,
            )
        except Exception as exc:  # noqa: BLE001
            LOG.error("publish failed platform=bluesky error=%s", type(exc).__name__)
            return PublishResult(platform=self.platform, success=False, error=str(exc), attempts=1)


def build_facets(text: str, client: Any | None = None) -> list[dict[str, Any]]:
    """Build AT Protocol rich-text facets for links and @mentions.

    AT Protocol byte ranges are UTF-8 byte offsets, not Python codepoint
    indexes. Links can be emitted directly. Mentions require DID resolution;
    unresolved handles are skipped instead of sending invalid facets.
    """

    facets: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for match in URL_RE.finditer(text):
        start, end = match.span()
        occupied.append((start, end))
        facets.append(
            {
                "index": _byte_range(text, start, end),
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": match.group(0)}],
            }
        )
    for match in MENTION_RE.finditer(text):
        start, end = match.span()
        if any(start >= used_start and end <= used_end for used_start, used_end in occupied):
            continue
        handle = match.group(1)
        did = resolve_handle(handle, client)
        if not did:
            continue
        facets.append(
            {
                "index": _byte_range(text, start, end),
                "features": [{"$type": "app.bsky.richtext.facet#mention", "did": did}],
            }
        )
    return sorted(facets, key=lambda item: int(item["index"]["byteStart"]))


def resolve_handle(handle: str, client: Any | None) -> str | None:
    """Resolve a Bluesky handle to DID for mention facets."""

    if client is None or not hasattr(client, "get"):
        return None
    try:
        response = client.get(f"{BLUESKY_BASE}/xrpc/com.atproto.identity.resolveHandle", params={"handle": handle})
        if response.status_code >= 400:
            return None
        did = response.json().get("did")
        return str(did) if did else None
    except Exception as exc:  # noqa: BLE001
        LOG.debug("Bluesky DID resolution failed handle_redacted=true error=%s", type(exc).__name__)
        return None


def _byte_range(text: str, start: int, end: int) -> dict[str, int]:
    return {
        "byteStart": len(text[:start].encode("utf-8")),
        "byteEnd": len(text[:end].encode("utf-8")),
    }


def grapheme_len(text: str) -> int:
    if grapheme is not None:
        return int(grapheme.length(text))
    # Fallback is imperfect for ZWJ sequences but avoids byte/len counting of combining marks.
    import unicodedata

    count = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        count += 1
    return count
