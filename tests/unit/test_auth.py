import base64
from pathlib import Path

import pytest
from gw.auth.store import CredentialStore, _CryptoBackend
from gw.errors import CredentialNotFoundError


class FakeKeyring:
    def __init__(self):
        self.data = {}

    def set_password(self, service, platform, payload):
        self.data[(service, platform)] = payload

    def get_password(self, service, platform):
        return self.data.get((service, platform))

    def delete_password(self, service, platform):
        del self.data[(service, platform)]


class FakeCrypto:
    def encrypt(self, plaintext: bytes, passphrase: str):
        return {"cipher": "FAKE", "ciphertext": base64.b64encode(plaintext).decode("ascii")}

    def decrypt(self, payload, passphrase: str) -> bytes:
        return base64.b64decode(payload["ciphertext"])


def test_keyring_store_set_get_revoke(monkeypatch, tmp_path: Path):
    keyring = FakeKeyring()
    monkeypatch.setattr(CredentialStore, "_load_keyring", staticmethod(lambda: keyring))
    store = CredentialStore(config_dir=tmp_path)
    store.set("mastodon", {"access_token": "abc", "instance_url": "https://m.example"})
    assert store.get("mastodon")["access_token"] == "abc"
    assert store.test("mastodon") is True
    store.revoke("mastodon")
    with pytest.raises(CredentialNotFoundError):
        store.get("mastodon")


def test_encrypted_fallback_never_plaintext(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_CryptoBackend, "load", classmethod(lambda cls: FakeCrypto()))
    store = CredentialStore(config_dir=tmp_path, prefer_keyring=False, passphrase_provider=lambda: "pw")
    store.set("bluesky", {"handle": "h", "app_password": "secret"})
    raw = (tmp_path / "credentials.enc").read_text(encoding="utf-8")
    assert "secret" not in raw
    assert store.get("bluesky")["handle"] == "h"
