from gw.tui import DraftReviewTUI, final_publish_confirm
from gw.tui import review as review_module


def test_tui_approve(monkeypatch):
    monkeypatch.setattr(review_module.click, "prompt", lambda *a, **k: "a")
    result = DraftReviewTUI().review("draft")
    assert result.content == "draft"


def test_tui_edit_then_approve(monkeypatch):
    answers = iter(["e", "a"])
    monkeypatch.setattr(review_module.click, "prompt", lambda *a, **k: next(answers))
    monkeypatch.setattr(review_module.click, "edit", lambda content: "edited draft")
    result = DraftReviewTUI().review("draft")
    assert result.content == "edited draft"


def test_final_publish_confirm(monkeypatch):
    monkeypatch.setattr(review_module.click, "confirm", lambda *a, **k: True)
    assert final_publish_confirm("mastodon") is True
