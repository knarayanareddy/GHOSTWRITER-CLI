"""Publisher protocol, retry helpers, and factory."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from gw.auth import CredentialStore
from gw.models import ApprovedDraft, PublishResult

LOG = logging.getLogger(__name__)
TRANSIENT = {429, 502, 503}
PERMANENT = {401, 403, 404, 422}


class Publisher(Protocol):
    platform: str

    def publish(self, draft: ApprovedDraft) -> PublishResult:
        """Publish an approved draft. Must never raise."""


class HttpPublisherBase:
    platform = "base"

    def __init__(
        self,
        credential_store: CredentialStore,
        *,
        client: httpx.Client | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        dry_run: bool = False,
    ) -> None:
        self.credential_store = credential_store
        self.client = client or httpx.Client(timeout=httpx.Timeout(15.0))
        self.sleeper = sleeper
        self.dry_run = dry_run

    def _retry_request(self, draft: ApprovedDraft, send: Callable[[], httpx.Response]) -> tuple[httpx.Response | None, int, str | None]:
        delays = [0, 1, 2]
        last_error: str | None = None
        for index, delay in enumerate(delays, start=1):
            if delay:
                LOG.debug("retrying publish platform=%s attempt=%s delay=%s", self.platform, index, delay)
                self.sleeper(delay)
            try:
                response = send()
                if response.status_code in TRANSIENT and index < len(delays):
                    last_error = f"HTTP {response.status_code}"
                    continue
                return response, index, None
            except httpx.TimeoutException:
                last_error = "network timeout"
                return None, index, last_error
            except httpx.HTTPError as exc:
                last_error = type(exc).__name__
                return None, index, last_error
        return None, len(delays), last_error

    @staticmethod
    def _error_from_response(response: httpx.Response | None, error: str | None) -> str:
        if error:
            return error
        if response is None:
            return "unknown publish failure"
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                return str(body["error"])
        except Exception as exc:  # noqa: BLE001
            LOG.debug("publish response body was not structured json error=%s", type(exc).__name__)
        return f"HTTP {response.status_code}"


def build_publisher(platform: str, credential_store: CredentialStore, **kwargs: Any) -> Publisher:
    normalized = platform.lower()
    if normalized == "mastodon":
        from gw.publishers.mastodon import MastodonPublisher

        return MastodonPublisher(credential_store, **kwargs)
    if normalized == "bluesky":
        from gw.publishers.bluesky import BlueskyPublisher

        return BlueskyPublisher(credential_store, **kwargs)
    if normalized == "ghost":
        from gw.publishers.ghost import GhostPublisher

        return GhostPublisher(credential_store, **kwargs)
    if normalized == "substack":
        from gw.publishers.substack import SubstackPublisher

        return SubstackPublisher(credential_store, **kwargs)
    raise ValueError(f"Unsupported platform: {platform}")
