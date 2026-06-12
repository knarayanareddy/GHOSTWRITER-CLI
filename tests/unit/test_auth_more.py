from pathlib import Path

import pytest
from gw.auth.store import CredentialStore, _CryptoBackend
from gw.errors import NoSecureCredentialBackendError

from tests.unit.test_auth import FakeCrypto, FakeKeyring


class FailingKeyring(FakeKeyring):
    def set_password(self, *args):
        raise RuntimeError("keychain down")

    def get_password(self, *args):
        raise RuntimeError("keychain down")


def test_keyring_failure_falls_back_to_encrypted(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(CredentialStore, "_load_keyring", staticmethod(lambda: FailingKeyring()))
    monkeypatch.setattr(_CryptoBackend, "load", classmethod(lambda cls: FakeCrypto()))
    store = CredentialStore(config_dir=tmp_path, passphrase_provider=lambda: "pw")
    store.set("mastodon", {"access_token": "tok"})
    assert store.get("mastodon")["access_token"] == "tok"


def test_missing_encrypted_store_raises(tmp_path: Path):
    store = CredentialStore(config_dir=tmp_path, prefer_keyring=False)
    from gw.errors import CredentialNotFoundError
    with pytest.raises(CredentialNotFoundError):
        store.get("mastodon")


def test_crypto_backend_load_error(monkeypatch):
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name.startswith("cryptography"):
            raise ImportError("no crypto")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(NoSecureCredentialBackendError):
        _CryptoBackend.load()
