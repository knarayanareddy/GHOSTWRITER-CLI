"""Unofficial Substack publisher. Fragile by design; emits WARN on use."""

from __future__ import annotations

import logging

from gw.models import ApprovedDraft, PublishResult
from gw.publishers.base import HttpPublisherBase

LOG = logging.getLogger(__name__)


class SubstackPublisher(HttpPublisherBase):
    platform = "substack"

    def publish(self, draft: ApprovedDraft) -> PublishResult:
        LOG.warning("Substack uses an unofficial API and may break without notice platform=substack")
        try:
            creds = self.credential_store.get(self.platform)
            base_url = creds["base_url"].rstrip("/")
            session_cookie = creds["session_cookie"]
            status = creds.get("status", "draft")
            if status == "published" and creds.get("confirmed_publish") != "true":
                return PublishResult(platform=self.platform, success=False, error="Substack publish requires explicit confirmation.")
            if self.dry_run:
                return PublishResult(platform=self.platform, success=True, attempts=0, metadata={"dry_run": True, "status": status})

            def send():  # type: ignore[no-untyped-def]
                return self.client.post(
                    f"{base_url}/api/v1/posts",
                    headers={"Cookie": session_cookie, "Content-Type": "application/json"},
                    json={"draft_title": draft.content.strip().splitlines()[0][:80] if draft.content.strip() else "Untitled", "body": draft.content, "status": status},
                )

            response, attempts, error = self._retry_request(draft, send)
            if response is None or response.status_code >= 400:
                return PublishResult(platform=self.platform, success=False, error=self._error_from_response(response, error), status_code=response.status_code if response else None, attempts=attempts)
            data = response.json()
            return PublishResult(platform=self.platform, success=True, url=data.get("canonical_url") or data.get("url"), attempts=attempts)
        except Exception as exc:  # noqa: BLE001
            LOG.error("publish failed platform=substack error=%s", type(exc).__name__)
            return PublishResult(platform=self.platform, success=False, error=str(exc), attempts=1)
