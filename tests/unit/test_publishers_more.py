from gw.models import ApprovedDraft
from gw.publishers import build_publisher
from gw.publishers.bluesky import BlueskyPublisher
from gw.publishers.ghost import GhostPublisher, ghost_jwt, title_from_content
from gw.publishers.substack import SubstackPublisher


class MultiStore:
    def get(self, platform):
        return {
            "bluesky": {"handle": "user.test", "app_password": "pw"},
            "ghost": {"admin_api_url": "https://ghost.example", "admin_api_key": "a:" + "0" * 64},
            "substack": {"base_url": "https://sub.example", "session_cookie": "sid=secret"},
            "mastodon": {"instance_url": "https://m.example", "access_token": "tok"},
        }[platform]


def test_publishers_dry_run_success(caplog):
    draft = ApprovedDraft("Hello world", ["bluesky", "ghost", "substack"])
    store = MultiStore()
    assert BlueskyPublisher(store, dry_run=True).publish(draft).success
    assert GhostPublisher(store, dry_run=True).publish(draft).success
    assert SubstackPublisher(store, dry_run=True).publish(draft).success
    assert "unofficial API" in caplog.text


def test_publisher_factory_and_helpers():
    store = MultiStore()
    assert build_publisher("ghost", store, dry_run=True).platform == "ghost"
    assert title_from_content("A title\nBody") == "A title"
    token = ghost_jwt("kid:" + "0" * 64)
    assert token.count(".") == 2
