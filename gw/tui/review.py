"""Textual-based draft review and explicit approval gate.

The primary review UI uses Textual, as required by ADR-003 and the design
specification. A small click-based fallback is retained only for environments
where Textual cannot be imported (for example minimal test sandboxes) so the
CLI remains usable and the approval state machine remains enforced.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import click

from gw.models import APPROVED, REJECTED

try:  # pragma: no cover - exercised when textual is installed in an interactive terminal.
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Button, Footer, Header, Static, TextArea
except Exception:  # noqa: BLE001 - dependency-light fallback for non-Textual environments.
    App = None
    ComposeResult = object
    Horizontal = Vertical = Button = Footer = Header = Static = TextArea = None


@dataclass(frozen=True)
class ReviewResult:
    state: str
    content: str


if App is not None:  # pragma: no cover - difficult to run headless across all CI terminals.

    class _DraftReviewApp(App[ReviewResult]):  # type: ignore[misc]
        """Textual app for reviewing, editing, approving, or rejecting a draft."""

        CSS = """
        Screen { layout: vertical; }
        #body { height: 1fr; padding: 1; }
        #draft { height: 1fr; border: round $accent; }
        #buttons { height: auto; align: center middle; padding: 1 0; }
        Button { margin: 0 1; }
        #hint { padding: 0 1; color: $text-muted; }
        """
        BINDINGS = [
            ("ctrl+a", "approve", "Approve"),
            ("ctrl+r", "reject", "Reject"),
            ("escape", "reject", "Reject"),
        ]

        def __init__(self, draft: str) -> None:
            super().__init__()
            self.initial_draft = draft

        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            with Vertical(id="body"):
                yield Static("Review and edit the generated draft. Approval is required before publishing.", id="hint")
                yield TextArea(self.initial_draft, id="draft")
                with Horizontal(id="buttons"):
                    yield Button("Approve", id="approve", variant="success")
                    yield Button("Reject", id="reject", variant="error")
            yield Footer()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "approve":
                self.action_approve()
            elif event.button.id == "reject":
                self.action_reject()

        def action_approve(self) -> None:
            editor = self.query_one("#draft", TextArea)
            self.exit(ReviewResult(APPROVED, editor.text.strip()))

        def action_reject(self) -> None:
            editor = self.query_one("#draft", TextArea)
            self.exit(ReviewResult(REJECTED, editor.text.strip()))


class DraftReviewTUI:
    """Interactive draft reviewer with edit/approve/reject transitions."""

    def review(self, draft: str) -> ReviewResult:
        if App is not None and is_interactive():
            result = _DraftReviewApp(draft).run()
            return result if result is not None else ReviewResult(REJECTED, draft)
        return self._fallback_review(draft)

    def _fallback_review(self, draft: str) -> ReviewResult:
        content = draft
        while True:
            click.echo("\n--- Generated Draft ---\n", err=True)
            click.echo(content, err=True)
            click.echo("\n-----------------------", err=True)
            choice = click.prompt("Approve, edit, or reject? [a/e/r]", default="r", err=True).strip().lower()
            if choice in {"a", "approve"}:
                return ReviewResult(APPROVED, content)
            if choice in {"r", "reject"}:
                return ReviewResult(REJECTED, content)
            if choice in {"e", "edit"}:
                edited = click.edit(content)
                if edited is not None:
                    content = edited.strip()
                    click.echo("Draft edited. Review the updated draft before approving.", err=True)
                    continue
                click.echo("Editor closed without changes.", err=True)


def final_publish_confirm(platform: str) -> bool:
    """Final publish gate. Default is always No."""
    return click.confirm(f"Publish to {platform}?", default=False, err=True)


def is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stderr.isatty()
