from pathlib import Path

from gw.eraser import Eraser


def test_eraser_deletes_file(tmp_path: Path):
    p = tmp_path / "secret.tmp"
    p.write_text("draft content", encoding="utf-8")
    Eraser().erase_file(p)
    assert not p.exists()


def test_eraser_deletes_tree(tmp_path: Path):
    d = tmp_path / "gw-session-x"
    d.mkdir()
    (d / "draft.tmp").write_text("draft", encoding="utf-8")
    Eraser().erase_tree(d)
    assert not d.exists()
