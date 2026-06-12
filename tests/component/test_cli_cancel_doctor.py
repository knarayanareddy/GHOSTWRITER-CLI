from click.testing import CliRunner
from gw.cli import cli, main


def test_cli_cancel_paths_and_doctor(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOSTWRITER_CONFIG_DIR", str(tmp_path / "config"))
    runner = CliRunner()
    assert runner.invoke(cli, ["config", "reset"], input="n\n").exit_code == 0
    assert runner.invoke(cli, ["profile", "delete", "default"], input="n\n").exit_code == 0
    assert runner.invoke(cli, ["auth", "revoke", "mastodon"], input="n\n").exit_code == 0
    assert runner.invoke(cli, ["doctor"]).exit_code == 0


def test_main_error_paths():
    assert main(["badcommand"]) == 64
