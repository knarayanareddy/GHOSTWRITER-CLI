from pathlib import Path

from gw.eraser.secure import Eraser, _filesystem_type


def test_eraser_nonexistent_and_file_tree(tmp_path: Path):
    eraser = Eraser()
    eraser.erase_file(tmp_path / "missing")
    file_path = tmp_path / "file.tmp"
    file_path.write_text("x", encoding="utf-8")
    eraser.erase_tree(file_path)
    assert not file_path.exists()


def test_filesystem_type_returns_value(tmp_path: Path):
    assert _filesystem_type(tmp_path) is None or isinstance(_filesystem_type(tmp_path), str)
