import httpx
from gw import cli as cli_module
from gw.auth.store import CredentialStore
from gw.cli import _prompt_credentials
from gw.publishers.bluesky import build_facets
from gw.publishers.mastodon import MastodonPublisher


class Store:
    def get(self, platform):
        return {"instance_url": "https://mastodon.example", "access_token": "secret-token"}


class ThreadClient:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(kwargs)
        idx = len(self.calls)
        return httpx.Response(
            201,
            json={"id": str(idx), "url": f"https://mastodon.example/{idx}"},
            request=httpx.Request("POST", url),
        )


def test_mastodon_thread_uses_unique_idempotency_key_per_chunk():
    client = ThreadClient()
    draft_text = "One sentence is short. " * 40
    publisher = MastodonPublisher(Store(), client=client, sleeper=lambda _: None, character_limit=100)
    result = publisher.publish(type("Draft", (), {"content": draft_text, "idempotency_key": "base-key"})())
    assert result.success
    keys = [call["headers"]["Idempotency-Key"] for call in client.calls]
    assert len(keys) > 1
    assert len(keys) == len(set(keys))
    assert keys[0] == "base-key-1"


class FacetClient:
    def get(self, url, params):
        return httpx.Response(
            200,
            json={"did": "did:plc:alice"},
            request=httpx.Request("GET", url),
        )


def test_bluesky_facets_for_links_and_mentions_with_utf8_offsets():
    text = "Café https://example.com hi @alice.test"
    facets = build_facets(text, FacetClient())
    assert len(facets) == 2
    link = facets[0]
    mention = facets[1]
    assert link["features"][0]["$type"] == "app.bsky.richtext.facet#link"
    assert link["index"]["byteStart"] == len("Café ".encode())
    assert mention["features"][0]["did"] == "did:plc:alice"


def test_published_credentials_store_explicit_confirmation(monkeypatch):
    prompts = iter(["https://ghost.example", "key:secret", "published"])
    monkeypatch.setattr(cli_module.click, "prompt", lambda *a, **k: next(prompts))
    monkeypatch.setattr(cli_module.click, "confirm", lambda *a, **k: True)
    values = _prompt_credentials("ghost")
    assert values["status"] == "published"
    assert values["confirmed_publish"] == "true"


def test_keychain_missing_warns_on_first_encrypted_fallback(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(CredentialStore, "_load_keyring", staticmethod(lambda: None))
    from gw.auth.store import _CryptoBackend

    from tests.unit.test_auth import FakeCrypto

    monkeypatch.setattr(_CryptoBackend, "load", classmethod(lambda cls: FakeCrypto()))
    store = CredentialStore(config_dir=tmp_path, passphrase_provider=lambda: "pw")
    store.set("mastodon", {"access_token": "tok"})
    assert "OS keychain unavailable" in caplog.text
