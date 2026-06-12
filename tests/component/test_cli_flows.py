from pathlib import Path

from click.testing import CliRunner
from gw import cli as cli_module
from gw.cli import cli
from gw.config import ConfigManager, ProfileConfig
from gw.models import APPROVED, VoiceProfile
from gw.tui.review import ReviewResult


class FakeOllama:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, *args, **kwargs):
        yield "Generated draft"


class FakeReview:
    def review(self, draft):
        return ReviewResult(APPROVED, draft)


class FakeStore:
    data = {}

    def set(self, platform, values):
        self.data[platform] = values

    def get(self, platform):
        return self.data[platform]

    def revoke(self, platform):
        self.data.pop(platform, None)

    def test(self, platform):
        return platform in self.data


class FakePublisher:
    platform = "mastodon"

    def publish(self, draft):
        return type("Result", (), {"platform": "mastodon", "success": True, "url": "https://m/1", "error": None, "__dict__": {"platform": "mastodon", "success": True, "url": "https://m/1", "error": None}})()


def test_cli_write_and_publish_flow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GHOSTWRITER_CONFIG_DIR", str(tmp_path / "config"))
    manager = ConfigManager(tmp_path / "config")
    cfg = manager.ensure()
    profile_path = Path(cfg.profile().voice_profile_path)
    VoiceProfile("1.0", "now", "hash", {"token_count": 10}).save(profile_path)
    monkeypatch.setattr(cli_module, "OllamaClient", FakeOllama)
    monkeypatch.setattr(cli_module, "DraftReviewTUI", FakeReview)
    runner = CliRunner()
    result = runner.invoke(cli, ["write", "--prompt", "topic"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "config" / "drafts" / "staged.json").exists()

    monkeypatch.setattr(cli_module, "final_publish_confirm", lambda platform: True)
    monkeypatch.setattr(cli_module, "CredentialStore", lambda: FakeStore())
    monkeypatch.setattr(cli_module, "build_publisher", lambda *a, **k: FakePublisher())
    result = runner.invoke(cli, ["publish", "--platform", "mastodon"])
    assert result.exit_code == 0, result.output
    assert "mastodon" in result.output


def test_cli_auth_commands(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(cli_module, "CredentialStore", lambda: fake)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["auth", "set", "mastodon"],
        input="https://m.example\ntoken\n",
    )
    assert result.exit_code == 0, result.output
    assert "mastodon" in fake.data
    result = runner.invoke(cli, ["auth", "test", "mastodon"])
    assert result.exit_code == 0
    assert "credentials_present" in result.output
    result = runner.invoke(cli, ["auth", "revoke", "mastodon"], input="y\n")
    assert result.exit_code == 0


def test_cli_profile_switch_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOSTWRITER_CONFIG_DIR", str(tmp_path / "config"))
    manager = ConfigManager(tmp_path / "config")
    cfg = manager.ensure()
    cfg.profiles["alt"] = ProfileConfig(name="alt", voice_profile_path=str(tmp_path / "alt.json"))
    manager.write(cfg)
    runner = CliRunner()
    result = runner.invoke(cli, ["profile", "switch", "alt"])
    assert result.exit_code == 0
    result = runner.invoke(cli, ["profile", "delete", "alt"], input="y\n")
    assert result.exit_code == 0
