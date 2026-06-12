"""Mastodon REST API publisher."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx

from gw.models import ApprovedDraft, PublishResult
from gw.publishers.base import HttpPublisherBase

LOG = logging.getLogger(__name__)


class MastodonPublisher(HttpPublisherBase):
    platform = "mastodon"

    def __init__(self, *args, character_limit: int = 500, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.character_limit = character_limit

    def publish(self, draft: ApprovedDraft) -> PublishResult:
        try:
            creds = self.credential_store.get(self.platform)
            base_url = creds["instance_url"].rstrip("/")
            token = creds["access_token"]
            chunks = split_thread(draft.content, self.character_limit)
            if self.dry_run:
                return PublishResult(platform=self.platform, success=True, url=None, attempts=0, metadata={"dry_run": True, "thread_length": len(chunks)})
            posted_ids: list[str] = []
            urls: list[str] = []
            in_reply_to_id: str | None = None
            attempts_total = 0
            for idx, chunk in enumerate(chunks, start=1):
                status = f"{chunk} ({idx}/{len(chunks)})" if len(chunks) > 1 else chunk
                # Each post in a thread is a distinct create-status request.
                # Reusing the same idempotency key across chunks causes Mastodon
                # instances to reject chunk 2+ as duplicates of chunk 1.
                idempotency_key = f"{draft.idempotency_key}-{idx}"
                reply_to = in_reply_to_id

                def send(status_text: str = status, reply_id: str | None = reply_to, idem: str = idempotency_key) -> httpx.Response:
                    payload: dict[str, str] = {"status": status_text}
                    if reply_id:
                        payload["in_reply_to_id"] = reply_id
                    return self.client.post(
                        urljoin(base_url + "/", "api/v1/statuses"),
                        data=payload,
                        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem},
                    )

                response, attempts, error = self._retry_request(draft, send)
                attempts_total += attempts
                if response is None or response.status_code >= 400:
                    return PublishResult(
                        platform=self.platform,
                        success=False,
                        error=self._error_from_response(response, error),
                        status_code=response.status_code if response else None,
                        attempts=attempts_total,
                        partial=bool(posted_ids),
                        metadata={"succeeded_posts": posted_ids, "failed_index": idx},
                    )
                data = response.json()
                in_reply_to_id = str(data.get("id", "")) or None
                posted_ids.append(in_reply_to_id or "unknown")
                if data.get("url"):
                    urls.append(str(data["url"]))
            LOG.info("post published platform=mastodon thread_length=%s", len(chunks))
            return PublishResult(platform=self.platform, success=True, url=urls[0] if urls else None, attempts=attempts_total, metadata={"thread_length": len(chunks), "post_ids": posted_ids})
        except Exception as exc:  # noqa: BLE001 - publisher contract: never raise.
            LOG.error("publish failed platform=mastodon error=%s", type(exc).__name__)
            return PublishResult(platform=self.platform, success=False, error=str(exc), attempts=1)


def split_thread(content: str, limit: int) -> list[str]:
    """Split content at sentence boundaries, never mid-word when possible."""
    if len(content) <= limit:
        return [content]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
    chunks: list[str] = []
    current = ""
    # Reserve room for thread indicators like " (1/9)". Rebalanced after split.
    target = max(1, limit - 8)
    for sentence in sentences:
        if len(sentence) > target:
            words = sentence.split()
            for word in words:
                if current and len(current) + 1 + len(word) > target:
                    chunks.append(current)
                    current = word
                else:
                    current = f"{current} {word}".strip()
        elif current and len(current) + 1 + len(sentence) > target:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks or [content[:target]]
