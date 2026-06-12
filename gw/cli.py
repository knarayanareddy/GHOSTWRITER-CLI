"""GhostWriter CLI entry point."""

from __future__ import annotations

import json
import logging
import os
import platform as platform_module
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import click

from gw import __version__
from gw.auth import CredentialStore
from gw.config import ConfigManager, default_config_dir
from gw.eraser import Eraser
from gw.errors import (
    EX_ERR,
    EX_INTERRUPTED,
    EX_IOERR,
    EX_OK,
    EX_USAGE,
    GhostWriterError,
)
from gw.llm import OllamaClient
from gw.logging import configure_logging
from gw.models import APPROVED, ApprovedDraft, VoiceProfile
from gw.prompt import PromptBuilder
from gw.publishers import build_publisher
from gw.tui import DraftReviewTUI, final_publish_confirm
from gw.tui.review import is_interactive
from gw.voice import VoiceEngine

LOG = logging.getLogger(__name__)
PLATFORMS = ("mastodon", "bluesky", "ghost", "substack")


class ContextObj(dict[str, Any]):
    @property
    def config_manager(self) -> ConfigManager:
        return cast(ConfigManager, self["config_manager"])


def _ctx() -> click.Context:
    return click.get_current_context()


@click.group(context_settings={"help_option_names": ["--help"]}, invoke_without_command=True)
@click.option("--profile", "profile_name", help="Override active profile for this invocation.")
@click.option("--log-level", type=click.Choice(["debug", "info", "warn", "warning", "error"], case_sensitive=False), default="info", show_default=True)
@click.option("--log-file", type=click.Path(path_type=Path), help="Write logs to file (default: stderr only).")
@click.option("--no-color", is_flag=True, help="Disable ANSI color output.")
@click.option("--dry-run", is_flag=True, help="Execute all steps except actual publish calls.")
@click.option("--yes", is_flag=True, help="Auto-confirm non-destructive prompts only; never publishes.")
@click.version_option(__version__, "--version", prog_name="ghostwriter")
@click.pass_context
def cli(ctx: click.Context, profile_name: str | None, log_level: str, log_file: Path | None, no_color: bool, dry_run: bool, yes: bool) -> None:
    """Local-first, privacy-preserving AI writing assistant."""

    normalized_level = "warning" if log_level == "warn" else log_level
    configure_logging(normalized_level, log_file)
    ctx.obj = ContextObj(
        profile_name=profile_name,
        log_level=normalized_level,
        log_file=log_file,
        no_color=no_color,
        dry_run=dry_run,
        yes=yes,
        config_manager=ConfigManager(),
    )
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), err=True)


@cli.command()
@click.option("--corpus", "corpus_paths", type=click.Path(path_type=Path), multiple=True, required=True, help="Corpus file or directory. May be repeated.")
@click.option("--output", type=click.Path(path_type=Path), help="Override output voice profile path.")
@click.option("--min-tokens", type=int, default=1000, show_default=True)
@click.option("--max-tokens", type=int, default=500_000, show_default=True)
@click.option("--force", is_flag=True, help="Analyze corpus above --max-tokens.")
@click.pass_context
def train(ctx: click.Context, corpus_paths: tuple[Path, ...], output: Path | None, min_tokens: int, max_tokens: int, force: bool) -> None:
    """Analyze corpus and build voice profile."""

    manager: ConfigManager = ctx.obj["config_manager"]
    cfg = manager.ensure()
    profile = cfg.profile(ctx.obj.get("profile_name"))
    output_path = output or Path(profile.voice_profile_path)
    voice = VoiceEngine().analyze(list(corpus_paths), output_path, min_tokens=min_tokens, max_tokens=max_tokens, force=force)
    click.echo(json.dumps({"profile_path": str(output_path.expanduser()), "schema_version": voice.schema_version, "token_count": voice.metrics.get("token_count")}), err=False)


@cli.command()
@click.option("--prompt", "prompt_text", required=True, help="Topic or instruction for the draft.")
@click.option("--timeout", type=int, default=60, show_default=True)
@click.option("--ollama-base-url", default="http://127.0.0.1:11434", show_default=True)
@click.option("--allow-remote-ollama", is_flag=True, help="Allow non-local Ollama host after accepting privacy risk.")
@click.option("--json", "json_output", is_flag=True, help="Print machine-readable draft result to stdout.")
@click.option("--save", is_flag=True, help="Save approved draft as markdown in the drafts directory.")
@click.pass_context
def write(
    ctx: click.Context,
    prompt_text: str,
    timeout: int,
    ollama_base_url: str,
    allow_remote_ollama: bool,
    json_output: bool,
    save: bool,
) -> None:
    """Generate a draft in your voice; opens review TUI before staging."""

    manager: ConfigManager = ctx.obj["config_manager"]
    cfg = manager.ensure()
    profile_cfg = cfg.profile(ctx.obj.get("profile_name"))
    profile_path = Path(profile_cfg.voice_profile_path).expanduser()
    if not profile_path.exists():
        raise GhostWriterError(
            f"Voice profile not found for profile '{profile_cfg.name}'.",
            recovery_hint="Run `ghostwriter train --corpus <path>` first.",
        )
    voice_profile = VoiceProfile.load(profile_path)
    built_prompt = PromptBuilder().build(voice_profile, prompt_text)
    client = OllamaClient(ollama_base_url, allow_remote=allow_remote_ollama)
    session_dir = Path(tempfile.gettempdir()) / f"gw-session-{os.urandom(8).hex()}"
    session_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    prompt_tmp = session_dir / "prompt.tmp"
    draft_tmp = session_dir / "draft.tmp"
    try:
        prompt_tmp.write_text(built_prompt, encoding="utf-8")
        os.chmod(prompt_tmp, 0o600)
        chunks = []
        click.echo("Generating draft with local Ollama...", err=True)
        for token in client.generate(profile_cfg.ollama_model, built_prompt, timeout_seconds=timeout, stream=True):
            chunks.append(token)
        draft = "".join(chunks).strip()
        draft_tmp.write_text(draft, encoding="utf-8")
        os.chmod(draft_tmp, 0o600)

        if json_output and not is_interactive():
            click.echo(json.dumps({"state": "GENERATED", "draft": draft}, ensure_ascii=False))
            click.echo("Non-interactive --json output did not stage an approved draft.", err=True)
            return

        review = DraftReviewTUI().review(draft)
        if review.state != APPROVED:
            click.echo("Draft rejected; nothing staged.", err=True)
            return
        approved = ApprovedDraft(content=review.content, platforms=profile_cfg.default_platforms)
        staged_path = manager.drafts_dir / "staged.json"
        approved.save(staged_path)
        if save:
            md_path = manager.drafts_dir / f"{_timestamp()}-{_slug(review.content)}.md"
            md_path.write_text(review.content + "\n", encoding="utf-8")
            click.echo(f"Saved approved draft: {md_path}", err=True)
        if json_output:
            click.echo(json.dumps({"state": approved.state, "staged_path": str(staged_path), "draft": approved.content}, ensure_ascii=False))
        else:
            click.echo(f"Approved draft staged for publishing: {staged_path}", err=True)
    finally:
        Eraser().erase_tree(session_dir)


@cli.command()
@click.option("--platform", "platforms", type=click.Choice(PLATFORMS), multiple=True, help="Target platform. May be repeated. Defaults to draft platforms/profile defaults.")
@click.pass_context
def publish(ctx: click.Context, platforms: tuple[str, ...]) -> None:
    """Publish an approved staged draft with final confirmation."""

    manager: ConfigManager = ctx.obj["config_manager"]
    cfg = manager.ensure()
    profile_cfg = cfg.profile(ctx.obj.get("profile_name"))
    staged_path = manager.drafts_dir / "staged.json"
    if not staged_path.exists():
        raise GhostWriterError("No approved staged draft found.", recovery_hint="Run `ghostwriter write --prompt ...` and approve the draft first.")
    draft = ApprovedDraft.load(staged_path)
    targets = list(platforms or draft.platforms or profile_cfg.default_platforms)
    store = CredentialStore()
    results = []
    for target in targets:
        if not final_publish_confirm(target):
            click.echo(f"Skipped {target} (not confirmed).", err=True)
            continue
        publisher = build_publisher(
            target,
            store,
            dry_run=bool(ctx.obj.get("dry_run")),
            character_limit=profile_cfg.mastodon_character_limit if target == "mastodon" else None,
        ) if target == "mastodon" else build_publisher(target, store, dry_run=bool(ctx.obj.get("dry_run")))
        result = publisher.publish(draft)
        results.append(result)
        if result.success:
            click.echo(f"Published to {target}: {result.url or '(no URL returned)'}", err=True)
        else:
            click.echo(f"Failed to publish to {target}: {result.error}", err=True)
    if results and all(result.success for result in results) and not ctx.obj.get("dry_run"):
        Eraser().erase_file(staged_path)
        click.echo("Approved staged draft securely erased after successful publish.", err=True)
    click.echo(json.dumps([r.__dict__ for r in results], ensure_ascii=False))


@cli.group()
def profile() -> None:
    """Manage writing profiles."""


@profile.command("list")
@click.pass_context
def profile_list(ctx: click.Context) -> None:
    manager: ConfigManager = ctx.obj["config_manager"]
    cfg = manager.ensure()
    click.echo(json.dumps({"active_profile": cfg.active_profile, "profiles": sorted(cfg.profiles)}))


@profile.command("switch")
@click.argument("name")
@click.pass_context
def profile_switch(ctx: click.Context, name: str) -> None:
    ctx.obj["config_manager"].switch_profile(name)
    click.echo(f"Switched active profile to {name}.", err=True)


@profile.command("delete")
@click.argument("name")
@click.pass_context
def profile_delete(ctx: click.Context, name: str) -> None:
    if not click.confirm(f"Delete profile '{name}'?", default=False, err=True):
        click.echo("Profile deletion cancelled.", err=True)
        return
    ctx.obj["config_manager"].delete_profile(name)
    click.echo(f"Deleted profile {name}.", err=True)


@cli.group()
def auth() -> None:
    """Store, revoke, and test platform credentials."""


@auth.command("set")
@click.argument("platform", type=click.Choice(PLATFORMS))
def auth_set(platform: str) -> None:
    values = _prompt_credentials(platform)
    CredentialStore().set(platform, values)
    click.echo(f"Stored credentials for {platform} in secure credential store.", err=True)


@auth.command("revoke")
@click.argument("platform", type=click.Choice(PLATFORMS))
def auth_revoke(platform: str) -> None:
    if not click.confirm(f"Revoke credentials for {platform}?", default=False, err=True):
        click.echo("Credential revoke cancelled.", err=True)
        return
    CredentialStore().revoke(platform)
    click.echo(f"Revoked credentials for {platform}.", err=True)


@auth.command("test")
@click.argument("platform", type=click.Choice(PLATFORMS))
def auth_test(platform: str) -> None:
    ok = CredentialStore().test(platform)
    click.echo(json.dumps({"platform": platform, "credentials_present": ok}))


@cli.group()
def config() -> None:
    """Manage configuration."""


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    manager: ConfigManager = ctx.obj["config_manager"]
    cfg = manager.ensure()
    data = {
        "meta": {"schema_version": cfg.schema_version, "active_profile": cfg.active_profile},
        "profile": {name: profile.__dict__ for name, profile in cfg.profiles.items()},
        "config_path": str(manager.config_path),
    }
    click.echo(json.dumps(data, indent=2))


@config.command("reset")
@click.pass_context
def config_reset(ctx: click.Context) -> None:
    if not click.confirm("Reset GhostWriter config to defaults?", default=False, err=True):
        click.echo("Config reset cancelled.", err=True)
        return
    ctx.obj["config_manager"].reset()
    click.echo("Config reset to defaults.", err=True)


@cli.command("version")
@click.option("--check", is_flag=True, help="User-initiated version check (no automatic telemetry).")
def version_cmd(check: bool) -> None:
    """Print version and build metadata."""

    payload: dict[str, Any] = {"name": "ghostwriter-cli", "version": __version__, "python": sys.version.split()[0]}
    if check:
        payload["check"] = "No automatic version checks are performed. Compare with PyPI manually if desired."
    click.echo(json.dumps(payload))


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Print machine-readable diagnostics.")
def doctor(json_output: bool) -> None:
    """Check runtime dependencies (Ollama, keyring, config)."""

    manager = ConfigManager()
    issues: list[str] = []
    try:
        cfg = manager.ensure()
        schema = cfg.schema_version
    except Exception as exc:  # noqa: BLE001
        schema = "unavailable"
        issues.append(f"config: {type(exc).__name__}")
    ollama = OllamaClient()
    models = ollama.list_models()
    if not models:
        issues.append("ollama unavailable or no models installed")
    keyring_available = CredentialStore._load_keyring() is not None  # noqa: SLF001
    payload = {
        "python_version": sys.version.split()[0],
        "ghostwriter_version": __version__,
        "os": platform_module.platform(),
        "architecture": platform_module.machine(),
        "ollama_available": bool(models),
        "ollama_models": models,
        "keyring_available": keyring_available,
        "config_schema_version": schema,
        "config_dir": str(default_config_dir()),
        "issues": issues,
    }
    if json_output:
        click.echo(json.dumps(payload, indent=2))
    else:
        for key, value in payload.items():
            click.echo(f"{key}: {value}", err=True)


def _prompt_credentials(platform: str) -> dict[str, str]:
    if platform == "mastodon":
        return {
            "instance_url": click.prompt("Mastodon instance URL", err=True),
            "access_token": click.prompt("Mastodon OAuth access token", hide_input=True, err=True),
        }
    if platform == "bluesky":
        return {
            "handle": click.prompt("Bluesky handle", err=True),
            "app_password": click.prompt("Bluesky app password", hide_input=True, err=True),
        }
    if platform == "ghost":
        admin_api_url = click.prompt("Ghost Admin API base URL", err=True)
        admin_api_key = click.prompt("Ghost Admin API key (id:secret)", hide_input=True, err=True)
        status = click.prompt("Ghost status", default="draft", err=True)
        return {
            "admin_api_url": admin_api_url,
            "admin_api_key": admin_api_key,
            "status": status,
            "confirmed_publish": _confirmed_publish_value("Ghost", status),
        }
    base_url = click.prompt("Substack base URL", err=True)
    session_cookie = click.prompt("Substack session cookie", hide_input=True, err=True)
    status = click.prompt("Substack status", default="draft", err=True)
    return {
        "base_url": base_url,
        "session_cookie": session_cookie,
        "status": status,
        "confirmed_publish": _confirmed_publish_value("Substack", status),
    }


def _confirmed_publish_value(platform_label: str, status: str) -> str:
    if status.strip().lower() != "published":
        return "false"
    allowed = click.confirm(
        f"Allow stored {platform_label} credentials to create live published posts?",
        default=False,
        err=True,
    )
    return "true" if allowed else "false"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(content: str) -> str:
    first = content.strip().splitlines()[0] if content.strip() else "draft"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", first.lower()).strip("-")
    return slug[:50] or "draft"


def main(argv: list[str] | None = None) -> int:
    try:
        cli.main(args=argv, prog_name="ghostwriter", standalone_mode=False)
        return EX_OK
    except KeyboardInterrupt:
        click.echo("Session ended by user. Cleanup has run where applicable. exit_code=130", err=True)
        return EX_INTERRUPTED
    except click.UsageError as exc:
        click.echo(f"Usage error: {exc}. exit_code={EX_USAGE}", err=True)
        return EX_USAGE
    except GhostWriterError as exc:
        click.echo(f"Error: {exc}. {exc.recovery_hint} exit_code={exc.exit_code}", err=True)
        LOG.debug("handled GhostWriterError", exc_info=True)
        return exc.exit_code
    except FileNotFoundError as exc:
        click.echo(f"Error: File not found: {exc}. Check the path and try again. exit_code={EX_IOERR}", err=True)
        return EX_IOERR
    except PermissionError as exc:
        click.echo(f"Error: Permission denied: {exc}. Check filesystem permissions. exit_code={EX_IOERR}", err=True)
        return EX_IOERR
    except OSError as exc:
        click.echo(f"Error: I/O failure: {type(exc).__name__}. exit_code={EX_IOERR}", err=True)
        LOG.debug("OSError", exc_info=True)
        return EX_IOERR
    except Exception as exc:  # noqa: BLE001
        log_file = None
        try:
            ctx = click.get_current_context(silent=True)
            if ctx and ctx.obj:
                log_file = ctx.obj.get("log_file")
        except Exception as ctx_exc:  # noqa: BLE001
            LOG.debug("could not inspect click context error=%s", type(ctx_exc).__name__)
        if log_file:
            logging.getLogger(__name__).error("unhandled exception", exc_info=True)
            click.echo(f"Unexpected error. Full details were logged to {log_file}. exit_code={EX_ERR}", err=True)
        else:
            click.echo(f"Unexpected error: {type(exc).__name__}. Run with --log-file for stack trace. exit_code={EX_ERR}", err=True)
        return EX_ERR


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
