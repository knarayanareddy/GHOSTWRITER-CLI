"""Local-only Ollama REST client."""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from urllib.parse import urlparse

import httpx

from gw.errors import OllamaConnectionError, OllamaModelError, OllamaTimeoutError

LOG = logging.getLogger(__name__)
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class OllamaClient:
    """Isolated Ollama API abstraction; defaults to loopback only."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", *, allow_remote: bool = False) -> None:
        parsed = urlparse(base_url)
        host = parsed.hostname or ""
        if host not in LOCAL_HOSTS and not allow_remote:
            raise ValueError(
                "Remote Ollama hosts are disabled by default. Use --allow-remote-ollama only if you accept the privacy risk."
            )
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Ollama base URL must be http(s).")
        if host not in LOCAL_HOSTS and allow_remote:
            LOG.warning("remote Ollama host enabled; corpus-derived prompt metrics may leave this machine host_redacted=true")
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        timeout_seconds: int = 60,
        stream: bool = True,
    ) -> Generator[str, None, None]:
        """Stream generated tokens from Ollama /api/generate."""

        payload = {"model": model, "prompt": prompt, "stream": stream}
        timeout = httpx.Timeout(timeout_seconds)
        try:
            if stream:
                with httpx.stream("POST", f"{self.base_url}/api/generate", json=payload, timeout=timeout) as response:
                    self._raise_for_ollama(response)
                    for line in response.iter_lines():
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if "error" in item:
                            raise OllamaModelError(
                                f"Ollama model error for '{model}'.",
                                recovery_hint=f"Run `ollama pull {model}` and try again.",
                            )
                        token = item.get("response")
                        if token:
                            yield str(token)
                        if item.get("done"):
                            break
            else:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(f"{self.base_url}/api/generate", json=payload)
                self._raise_for_ollama(response)
                data = response.json()
                if "error" in data:
                    raise OllamaModelError(
                        f"Ollama model error for '{model}'.", recovery_hint=f"Run `ollama pull {model}` and try again."
                    )
                yield str(data.get("response", ""))
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                "Ollama is not running. Start it with `ollama serve`.",
                recovery_hint="Install Ollama, run `ollama serve`, and pull the configured model.",
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Ollama generation exceeded {timeout_seconds} seconds.",
                recovery_hint="Try a smaller model, shorter prompt, or raise --timeout.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise OllamaModelError(
                    f"Model '{model}' not found. Run `ollama pull {model}`.",
                    recovery_hint=f"Run `ollama pull {model}`.",
                ) from exc
            raise OllamaConnectionError("Ollama returned an unexpected HTTP error.") from exc

    @staticmethod
    def _raise_for_ollama(response: httpx.Response) -> None:
        if response.status_code == 404:
            raise OllamaModelError("Ollama model not found.", recovery_hint="Run `ollama list` and update your profile model.")
        response.raise_for_status()

    def list_models(self, *, timeout_seconds: int = 5) -> list[str]:
        """Return locally available Ollama models; never contacts non-local by default."""
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_seconds)) as client:
                response = client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [str(m.get("name")) for m in data.get("models", []) if m.get("name")]
        except Exception as exc:  # noqa: BLE001 - doctor should report availability, not crash.
            LOG.debug("ollama list models failed error=%s", exc)
            return []
