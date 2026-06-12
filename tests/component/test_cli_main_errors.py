from pathlib import Path

import click
from gw.cli import cli, main
from gw.errors import GhostWriterError


def _add_command_once(name, func):
    if name not in cli.commands:
        cli.add_command(click.Command(name, callback=func))


def test_main_handled_error_paths(tmp_path: Path):
    def boom_gw():
        raise GhostWriterError("handled")
    def boom_file():
        raise FileNotFoundError("missing")
    def boom_os():
        raise OSError("io")
    def boom_unknown():
        raise RuntimeError("bad")
    _add_command_once("boom-gw", boom_gw)
    _add_command_once("boom-file", boom_file)
    _add_command_once("boom-os", boom_os)
    _add_command_once("boom-unknown", boom_unknown)
    assert main(["boom-gw"]) == 1
    assert main(["boom-file"]) == 74
    assert main(["boom-os"]) == 74
    assert main(["--log-file", str(tmp_path / "gw.log"), "boom-unknown"]) == 1
