import httpx
from gw.models import ApprovedDraft
from gw.publishers.bluesky import BlueskyPublisher
from gw.publishers.ghost import GhostPublisher
from gw.publishers.substack import SubstackPublisher


class Store:
    def get(self, platform):
        return {
            "bluesky": {"handle": "h", "app_password": "p"},
            "ghost": {"admin_api_url": "https://ghost.example", "admin_api_key": "kid:" + "0" * 64},
            "substack": {"base_url": "https://sub.example", "session_cookie": "sid=s"},
        }[platform]


class Client:
    def __init__(self, responses):
        self.responses = list(responses)

    def post(self, url, **kwargs):
        payload = self.responses.pop(0)
        return httpx.Response(payload[0], json=payload[1], request=httpx.Request("POST", url))


def test_bluesky_success_path():
    client = Client([
        (200, {"accessJwt": "jwt", "did": "did:plc:123"}),
        (200, {"uri": "at://did/post/1"}),
    ])
    result = BlueskyPublisher(Store(), client=client).publish(ApprovedDraft("short", ["bluesky"]))
    assert result.success
    assert result.url == "at://did/post/1"


def test_ghost_success_path():
    client = Client([(201, {"posts": [{"url": "https://ghost/p"}]})])
    result = GhostPublisher(Store(), client=client).publish(ApprovedDraft("Title\nBody", ["ghost"]))
    assert result.success
    assert result.url == "https://ghost/p"


def test_substack_success_path(caplog):
    client = Client([(200, {"canonical_url": "https://sub/p"})])
    result = SubstackPublisher(Store(), client=client).publish(ApprovedDraft("Title\nBody", ["substack"]))
    assert result.success
    assert result.url == "https://sub/p"
    assert "unofficial" in caplog.text
