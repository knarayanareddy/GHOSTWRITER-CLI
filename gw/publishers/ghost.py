"""Ghost Admin API publisher."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from gw.models import ApprovedDraft, PublishResult
from gw.publishers.base import HttpPublisherBase

LOG = logging.getLogger(__name__)


class GhostPublisher(HttpPublisherBase):
    platform = "ghost"

    def publish(self, draft: ApprovedDraft) -> PublishResult:
        try:
            creds = self.credential_store.get(self.platform)
            api_url = creds["admin_api_url"].rstrip("/")
            admin_key = creds["admin_api_key"]
            status = creds.get("status", "draft")
            if status == "published" and creds.get("confirmed_publish") != "true":
                return PublishResult(platform=self.platform, success=False, error="Ghost published status requires explicit confirmation.")
            if self.dry_run:
                return PublishResult(platform=self.platform, success=True, attempts=0, metadata={"dry_run": True, "status": status})
            token = ghost_jwt(admin_key)
            lexical = {"root": {"children": [{"children": [{"text": draft.content, "type": "text"}], "type": "paragraph"}], "type": "root"}}

            def send():  # type: ignore[no-untyped-def]
                return self.client.post(
                    f"{api_url}/ghost/api/admin/posts/?source=html",
                    headers={"Authorization": f"Ghost {token}", "Content-Type": "application/json"},
                    json={"posts": [{"title": title_from_content(draft.content), "lexical": json.dumps(lexical), "status": status}]},
                )

            response, attempts, error = self._retry_request(draft, send)
            if response is None or response.status_code >= 400:
                return PublishResult(platform=self.platform, success=False, error=self._error_from_response(response, error), status_code=response.status_code if response else None, attempts=attempts)
            data = response.json()
            post = (data.get("posts") or [{}])[0]
            return PublishResult(platform=self.platform, success=True, url=post.get("url"), attempts=attempts)
        except Exception as exc:  # noqa: BLE001
            LOG.error("publish failed platform=ghost error=%s", type(exc).__name__)
            return PublishResult(platform=self.platform, success=False, error=str(exc), attempts=1)


def ghost_jwt(admin_key: str) -> str:
    key_id, secret = admin_key.split(":", 1)
    now = datetime.now(timezone.utc)
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=5)).timestamp()), "aud": "/admin/"}
    signing_input = f"{_b64json(header)}.{_b64json(payload)}".encode("ascii")
    signature = hmac.new(bytes.fromhex(secret), signing_input, hashlib.sha256).digest()
    return signing_input.decode("ascii") + "." + _b64(signature)


def _b64json(data: Mapping[str, object]) -> str:
    return _b64(json.dumps(data, separators=(",", ":")).encode("utf-8"))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def title_from_content(content: str) -> str:
    first = content.strip().splitlines()[0] if content.strip() else "Untitled"
    return first[:80]
