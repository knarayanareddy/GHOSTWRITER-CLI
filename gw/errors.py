"""Domain exceptions and exit code constants for GhostWriter."""

from __future__ import annotations

EX_OK = 0
EX_ERR = 1
EX_USAGE = 64
EX_DATA = 65
EX_UNAVAIL = 69
EX_CANTCREATE = 73
EX_IOERR = 74
EX_NOPERM = 77
EX_CONFIG = 78
EX_INTERRUPTED = 130


class GhostWriterError(Exception):
    """Base class for expected, user-facing GhostWriter errors."""

    exit_code = EX_ERR
    recovery_hint = "Run `ghostwriter doctor` for diagnostics."

    def __init__(self, message: str, *, recovery_hint: str | None = None) -> None:
        super().__init__(message)
        if recovery_hint is not None:
            self.recovery_hint = recovery_hint


class CorpusError(GhostWriterError):
    """Corpus validation or analysis failure."""

    exit_code = EX_DATA


class ConfigError(GhostWriterError):
    """Configuration schema/load/migration failure."""

    exit_code = EX_CONFIG


class CredentialError(GhostWriterError):
    """Credential storage or retrieval failure."""

    exit_code = EX_NOPERM


class CredentialNotFoundError(CredentialError):
    """No stored credentials exist for a requested platform."""


class NoSecureCredentialBackendError(CredentialError):
    """No secure keychain or encrypted-file backend can be used."""


class OllamaConnectionError(GhostWriterError):
    """Ollama is not reachable."""

    exit_code = EX_UNAVAIL


class OllamaTimeoutError(GhostWriterError):
    """Ollama generation timed out."""

    exit_code = EX_UNAVAIL


class OllamaModelError(GhostWriterError):
    """Requested Ollama model is not installed or failed."""

    exit_code = EX_UNAVAIL


class PublishError(GhostWriterError):
    """Publishing flow failure."""

    exit_code = EX_ERR
