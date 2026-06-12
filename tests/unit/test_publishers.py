import httpx
from gw.models import ApprovedDraft
from gw.publishers.bluesky import grapheme_len
from gw.publishers.mastodon import MastodonPublisher, split_thread


class Store:
    def get(self, platform):
        return {"instance_url": "https://mastodon.example", "access_token": "secret-token"}


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.responses.pop(0)


def response(status, payload):
    return httpx.Response(status, json=payload, request=httpx.Request("POST", "https://example.test"))


def test_mastodon_retries_transient_then_succeeds():
    client = Client([response(429, {"error": "rate"}), response(201, {"id": "1", "url": "https://m/1"})])
    publisher = MastodonPublisher(Store(), client=client, sleeper=lambda _: None)
    result = publisher.publish(ApprovedDraft("hello world", ["mastodon"]))
    assert result.success is True
    assert result.attempts == 2
    assert len(client.calls) == 2


def test_mastodon_does_not_retry_401():
    client = Client([response(401, {"error": "bad auth"})])
    publisher = MastodonPublisher(Store(), client=client, sleeper=lambda _: None)
    result = publisher.publish(ApprovedDraft("hello world", ["mastodon"]))
    assert result.success is False
    assert result.attempts == 1
    assert len(client.calls) == 1


def test_thread_split_never_exceeds_limit_with_indicator_margin():
    chunks = split_thread("One sentence is short. " * 80, 100)
    assert len(chunks) > 1
    assert all(len(c) <= 92 for c in chunks)


def test_grapheme_len_combining_mark_fallback_or_library():
    assert grapheme_len("e\u0301") == 1
