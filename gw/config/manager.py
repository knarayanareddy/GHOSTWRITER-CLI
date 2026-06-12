"""Config management with schema versioning and backup-before-migration."""

from __future__ import annotations

import importlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gw.errors import ConfigError

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on py3.10 without tomli
    try:
        import tomli as tomllib
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ConfigError("TOML parser unavailable. Install `tomli` on Python 3.10.") from exc

CURRENT_SCHEMA_VERSION = "1.0"
APP_NAME = "ghostwriter"


@dataclass
class ProfileConfig:
    name: str
    ollama_model: str = "llama3"
    voice_profile_path: str = ""
    default_platforms: list[str] = field(default_factory=lambda: ["mastodon"])
    mastodon_character_limit: int = 500
    ghost_default_status: str = "draft"


@dataclass
class GhostWriterConfig:
    schema_version: str = CURRENT_SCHEMA_VERSION
    active_profile: str = "default"
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.profiles:
            self.profiles["default"] = ProfileConfig(name="default")

    def profile(self, name: str | None = None) -> ProfileConfig:
        key = name or self.active_profile
        try:
            return self.profiles[key]
        except KeyError as exc:
            raise ConfigError(f"Profile '{key}' not found.", recovery_hint="Run `ghostwriter profile list`.") from exc


class ConfigManager:
    """Load, write, and migrate GhostWriter TOML config."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or default_config_dir()
        self.config_path = self.config_dir / "config.toml"
        self.profiles_dir = self.config_dir / "profiles"
        self.drafts_dir = self.config_dir / "drafts"

    def ensure(self) -> GhostWriterConfig:
        if not self.config_path.exists():
            cfg = self.default_config()
            self.write(cfg)
            return cfg
        return self.load()

    def default_config(self) -> GhostWriterConfig:
        profile_path = str((self.profiles_dir / "default.json").expanduser())
        return GhostWriterConfig(
            schema_version=CURRENT_SCHEMA_VERSION,
            active_profile="default",
            profiles={"default": ProfileConfig(name="default", voice_profile_path=profile_path)},
        )

    def load(self) -> GhostWriterConfig:
        try:
            with self.config_path.open("rb") as fh:
                data = tomllib.load(fh)
        except OSError as exc:
            raise ConfigError("Could not read GhostWriter config.", recovery_hint="Check config file permissions.") from exc
        cfg = self._from_toml(data)
        if cfg.schema_version != CURRENT_SCHEMA_VERSION:
            cfg = self.migrate(cfg.schema_version)
        return cfg

    def write(self, cfg: GhostWriterConfig) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
            self.drafts_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.config_path.with_suffix(".toml.tmp")
            tmp.write_text(self._to_toml(cfg), encoding="utf-8")
            tmp.replace(self.config_path)
        except OSError as exc:
            raise ConfigError("Cannot write GhostWriter config to disk.", recovery_hint="Check disk space and permissions.") from exc

    def migrate(self, from_version: str) -> GhostWriterConfig:
        backup = self.config_path.with_suffix(self.config_path.suffix + ".backup")
        try:
            shutil.copy2(self.config_path, backup)
            module_name = f"gw.config.migrations.v{from_version.replace('.', '_')}_to_v{CURRENT_SCHEMA_VERSION.replace('.', '_')}"
            migration = importlib.import_module(module_name)
            new_text = migration.migrate(self.config_path.read_text(encoding="utf-8"))
            self.config_path.write_text(new_text, encoding="utf-8")
            return self.load()
        except Exception as exc:  # noqa: BLE001 - migration failure is user-facing config failure.
            raise ConfigError(
                f"Config migration failed. Backup at {backup}.",
                recovery_hint="Restore the .backup file or reset config with `ghostwriter config reset`.",
            ) from exc

    def list_profiles(self) -> list[str]:
        return sorted(self.ensure().profiles)

    def switch_profile(self, name: str) -> None:
        cfg = self.ensure()
        if name not in cfg.profiles:
            raise ConfigError(f"Profile '{name}' not found.")
        cfg.active_profile = name
        self.write(cfg)

    def delete_profile(self, name: str) -> None:
        if name == "default":
            raise ConfigError("The default profile cannot be deleted.")
        cfg = self.ensure()
        if name not in cfg.profiles:
            raise ConfigError(f"Profile '{name}' not found.")
        del cfg.profiles[name]
        if cfg.active_profile == name:
            cfg.active_profile = "default"
        self.write(cfg)

    def reset(self) -> GhostWriterConfig:
        cfg = self.default_config()
        self.write(cfg)
        return cfg

    def _from_toml(self, data: dict[str, Any]) -> GhostWriterConfig:
        meta = data.get("meta", {})
        profiles_data = data.get("profile", {})
        profiles: dict[str, ProfileConfig] = {}
        for name, raw in profiles_data.items():
            profiles[str(name)] = ProfileConfig(
                name=str(name),
                ollama_model=str(raw.get("ollama_model", "llama3")),
                voice_profile_path=str(raw.get("voice_profile_path", self.profiles_dir / f"{name}.json")),
                default_platforms=[str(x) for x in raw.get("default_platforms", ["mastodon"])],
                mastodon_character_limit=int(raw.get("mastodon_character_limit", 500)),
                ghost_default_status=str(raw.get("ghost_default_status", "draft")),
            )
        return GhostWriterConfig(
            schema_version=str(meta.get("schema_version", "0.0")),
            active_profile=str(meta.get("active_profile", "default")),
            profiles=profiles,
        )

    @staticmethod
    def _quote(value: str) -> str:
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

    def _to_toml(self, cfg: GhostWriterConfig) -> str:
        lines = [
            "[meta]",
            f"schema_version = {self._quote(cfg.schema_version)}",
            f"active_profile = {self._quote(cfg.active_profile)}",
            "",
        ]
        for name in sorted(cfg.profiles):
            profile = cfg.profiles[name]
            platforms = ", ".join(self._quote(p) for p in profile.default_platforms)
            lines.extend(
                [
                    f"[profile.{name}]",
                    f"ollama_model = {self._quote(profile.ollama_model)}",
                    f"voice_profile_path = {self._quote(profile.voice_profile_path)}",
                    f"default_platforms = [{platforms}]",
                    f"mastodon_character_limit = {profile.mastodon_character_limit}",
                    f"ghost_default_status = {self._quote(profile.ghost_default_status)}",
                    "",
                ]
            )
        return "\n".join(lines)


def default_config_dir() -> Path:
    explicit = os.environ.get("GHOSTWRITER_CONFIG_DIR")
    if explicit:
        return Path(explicit).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / APP_NAME
    return Path.home() / ".config" / APP_NAME
