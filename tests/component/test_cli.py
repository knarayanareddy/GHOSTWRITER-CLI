from pathlib import Path

from click.testing import CliRunner
from gw.cli import cli


def test_cli_train_and_profile_list(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GHOSTWRITER_CONFIG_DIR", str(tmp_path / "config"))
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("This is synthetic local text. " * 100, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["train", "--corpus", str(corpus), "--min-tokens", "10"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["profile", "list"])
    assert result.exit_code == 0
    assert "default" in result.output


def test_cli_doctor_json(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GHOSTWRITER_CONFIG_DIR", str(tmp_path / "config"))
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--json"])
    assert result.exit_code == 0
    assert "ghostwriter_version" in result.output
