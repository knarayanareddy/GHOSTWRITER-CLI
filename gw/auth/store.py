"""Secure credential storage: OS keychain first, AES-256-GCM encrypted file fallback."""

from __future__ import annotations

import base64
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any, cast

from gw.config import default_config_dir
from gw.errors import CredentialNotFoundError, NoSecureCredentialBackendError

LOG = logging.getLogger(__name__)
SERVICE = "ghostwriter-cli"
PBKDF2_ITERATIONS = 390_000


@dataclass
class CredentialRecord:
    platform: str
    values: dict[str, str]


class CredentialStore:
    """Store credentials without plaintext-on-disk fallback."""

    def __init__(
        self,
        *,
        config_dir: Path | None = None,
        passphrase_provider: Callable[[], str] | None = None,
        prefer_keyring: bool = True,
    ) -> None:
        self.config_dir = config_dir or default_config_dir()
        self.encrypted_path = self.config_dir / "credentials.enc"
        self.passphrase_provider = passphrase_provider or (lambda: getpass("GhostWriter credential passphrase: "))
        self.prefer_keyring = prefer_keyring
        self._keyring = self._load_keyring() if prefer_keyring else None
        self._fallback_warning_emitted = False

    def set(self, platform: str, values: dict[str, str]) -> None:
        payload = json.dumps(values, sort_keys=True)
        if self._keyring is not None:
            try:
                self._keyring.set_password(SERVICE, platform, payload)
                return
            except Exception as exc:  # noqa: BLE001
                LOG.warning("OS keychain unavailable; falling back to encrypted file backend=%s", type(exc).__name__)
        self._warn_first_time_encrypted_fallback()
        data = self._read_encrypted_all(allow_missing=True)
        data[platform] = values
        self._write_encrypted_all(data)

    def get(self, platform: str) -> dict[str, str]:
        if self._keyring is not None:
            try:
                raw = self._keyring.get_password(SERVICE, platform)
                if raw:
                    return dict(json.loads(raw))
            except Exception as exc:  # noqa: BLE001
                LOG.warning("OS keychain read failed; trying encrypted fallback backend=%s", type(exc).__name__)
        data = self._read_encrypted_all(allow_missing=False)
        try:
            return dict(data[platform])
        except KeyError as exc:
            raise CredentialNotFoundError(
                f"No credentials for {platform}. Run `ghostwriter auth set {platform}`.",
                recovery_hint=f"Run `ghostwriter auth set {platform}`.",
            ) from exc

    def revoke(self, platform: str) -> None:
        removed = False
        if self._keyring is not None:
            try:
                self._keyring.delete_password(SERVICE, platform)
                removed = True
            except Exception as exc:  # noqa: BLE001 - absence is fine.
                LOG.debug("keychain credential delete skipped backend=%s", type(exc).__name__)
        try:
            data = self._read_encrypted_all(allow_missing=True)
            if platform in data:
                del data[platform]
                self._write_encrypted_all(data)
                removed = True
        except NoSecureCredentialBackendError:
            if not removed:
                raise
        if not removed:
            raise CredentialNotFoundError(f"No credentials for {platform}.")

    def test(self, platform: str) -> bool:
        values = self.get(platform)
        return bool(values)

    def _warn_first_time_encrypted_fallback(self) -> None:
        if self._fallback_warning_emitted or self.encrypted_path.exists():
            return
        if self.prefer_keyring and self._keyring is None:
            LOG.warning(
                "OS keychain unavailable; creating AES-256-GCM encrypted credential file fallback. "
                "You will be prompted for a passphrase."
            )
            self._fallback_warning_emitted = True

    @staticmethod
    def _load_keyring() -> Any | None:
        try:
            import keyring

            return keyring
        except Exception:  # noqa: BLE001
            return None

    def _read_encrypted_all(self, *, allow_missing: bool) -> dict[str, dict[str, str]]:
        if not self.encrypted_path.exists():
            if allow_missing:
                return {}
            raise CredentialNotFoundError(
                "Encrypted credential store does not exist.",
                recovery_hint="Run `ghostwriter auth set <platform>` to create it.",
            )
        crypto = _CryptoBackend.load()
        passphrase = self.passphrase_provider()
        try:
            raw = json.loads(self.encrypted_path.read_text(encoding="utf-8"))
            plaintext = crypto.decrypt(raw, passphrase)
            data = json.loads(plaintext.decode("utf-8"))
            return {str(k): {str(kk): str(vv) for kk, vv in dict(v).items()} for k, v in data.items()}
        except Exception as exc:  # noqa: BLE001
            raise NoSecureCredentialBackendError(
                "Could not decrypt credential store.",
                recovery_hint="Check your passphrase or revoke/recreate credentials.",
            ) from exc

    def _write_encrypted_all(self, data: dict[str, dict[str, str]]) -> None:
        crypto = _CryptoBackend.load()
        passphrase = self.passphrase_provider()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        encrypted = crypto.encrypt(payload, passphrase)
        tmp = self.encrypted_path.with_suffix(".enc.tmp")
        tmp.write_text(json.dumps(encrypted, sort_keys=True), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.encrypted_path)


class _CryptoBackend:
    """Thin wrapper around cryptography's AESGCM and PBKDF2HMAC."""

    def __init__(self, AESGCM: Any, hashes: Any, PBKDF2HMAC: Any, default_backend: Any) -> None:
        self.AESGCM = AESGCM
        self.hashes = hashes
        self.PBKDF2HMAC = PBKDF2HMAC
        self.default_backend = default_backend

    @classmethod
    def load(cls) -> _CryptoBackend:
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            return cls(AESGCM, hashes, PBKDF2HMAC, default_backend)
        except Exception as exc:  # noqa: BLE001
            raise NoSecureCredentialBackendError(
                "No secure credential backend available. Install `keyring` or `cryptography`.",
                recovery_hint="Install dependencies with `pip install ghostwriter-cli[keychain]` or enable OS keychain.",
            ) from exc

    def derive_key(self, passphrase: str, salt: bytes) -> bytes:
        kdf = self.PBKDF2HMAC(
            algorithm=self.hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=self.default_backend(),
        )
        return cast(bytes, kdf.derive(passphrase.encode("utf-8")))

    def encrypt(self, plaintext: bytes, passphrase: str) -> dict[str, str | int]:
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self.derive_key(passphrase, salt)
        ciphertext = self.AESGCM(key).encrypt(nonce, plaintext, None)
        return {
            "version": 1,
            "kdf": "PBKDF2-HMAC-SHA256",
            "iterations": PBKDF2_ITERATIONS,
            "cipher": "AES-256-GCM",
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

    def decrypt(self, payload: dict[str, str | int], passphrase: str) -> bytes:
        if payload.get("cipher") != "AES-256-GCM":
            raise ValueError("Unsupported credential cipher")
        salt = base64.b64decode(str(payload["salt"]))
        nonce = base64.b64decode(str(payload["nonce"]))
        ciphertext = base64.b64decode(str(payload["ciphertext"]))
        key = self.derive_key(passphrase, salt)
        return cast(bytes, self.AESGCM(key).decrypt(nonce, ciphertext, None))
