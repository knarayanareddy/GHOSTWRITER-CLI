from click.testing import CliRunner
from gw.cli import cli, main


def test_cli_version_config_reset_and_show(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOSTWRITER_CONFIG_DIR", str(tmp_path / "config"))
    runner = CliRunner()
    assert runner.invoke(cli, ["version"]).exit_code == 0
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "schema_version" in result.output
    result = runner.invoke(cli, ["config", "reset"], input="y\n")
    assert result.exit_code == 0


def test_main_usage_error_returns_spec_code():
    assert main(["train"]) == 64
