from click.testing import CliRunner
from gw import cli as cli_module
from gw.cli import cli

from tests.component.test_cli_flows import FakeStore


def test_cli_auth_set_other_platforms(monkeypatch):
    fake = FakeStore()
    monkeypatch.setattr(cli_module, "CredentialStore", lambda: fake)
    runner = CliRunner()
    assert runner.invoke(cli, ["auth", "set", "bluesky"], input="handle\napp-pass\n").exit_code == 0
    assert runner.invoke(cli, ["auth", "set", "ghost"], input="https://ghost\nkey\ndraft\n").exit_code == 0
    assert runner.invoke(cli, ["auth", "set", "substack"], input="https://sub\ncookie\ndraft\n").exit_code == 0
    assert set(fake.data) == {"bluesky", "ghost", "substack"}
