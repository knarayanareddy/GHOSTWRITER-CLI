from pathlib import Path

from gw.logging import _MaxLevelFilter, configure_logging, redact_many
from gw.models import ApprovedDraft, VoiceProfile
from gw.publishers.bluesky import BlueskyPublisher
from gw.publishers.ghost import GhostPublisher
from gw.publishers.mastodon import MastodonPublisher
from gw.publishers.substack import SubstackPublisher

from tests.unit.test_publishers_live_paths import Store


def test_models_load_and_validation(tmp_path: Path):
    profile = VoiceProfile("1.0", "now", "hash", {})
    path = tmp_path / "p.json"
    profile.save(path)
    assert VoiceProfile.load(path).corpus_hash == "hash"
    draft = ApprovedDraft("content", ["mastodon"])
    dpath = tmp_path / "d.json"
    draft.save(dpath)
    assert ApprovedDraft.load(dpath).content == "content"
    try:
        ApprovedDraft("bad", [], state="GENERATED")
    except ValueError:
        pass


def test_logging_helpers(tmp_path: Path):
    configure_logging("debug", tmp_path / "gw.log")
    assert redact_many(["password=abc"])[0].endswith("<redacted>")
    assert _MaxLevelFilter(20).filter(type("R", (), {"levelno": 10})())


def test_publisher_error_branches():
    store = Store()
    assert not BlueskyPublisher(store).publish(ApprovedDraft("x" * 301, ["bluesky"])).success
    class PublishedStore(Store):
        def get(self, platform):
            data = super().get(platform)
            data["status"] = "published"
            return data
    assert not GhostPublisher(PublishedStore()).publish(ApprovedDraft("x", ["ghost"])).success
    assert not SubstackPublisher(PublishedStore()).publish(ApprovedDraft("x", ["substack"])).success
    assert MastodonPublisher(type("S", (), {"get": lambda self, p: {"instance_url": "https://m", "access_token": "t"}})(), dry_run=True).publish(ApprovedDraft("x", ["mastodon"])).success
