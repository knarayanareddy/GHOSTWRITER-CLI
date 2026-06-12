from pathlib import Path

from gw.config import ConfigManager


def test_config_default_and_switch(tmp_path: Path):
    manager = ConfigManager(tmp_path)
    cfg = manager.ensure()
    assert cfg.active_profile == "default"
    assert manager.config_path.exists()
    assert manager.list_profiles() == ["default"]


def test_config_migration_backup(tmp_path: Path):
    manager = ConfigManager(tmp_path)
    tmp_path.mkdir(exist_ok=True)
    manager.config_path.write_text('''[meta]\nschema_version = "0.9"\nactive_profile = "default"\n\n[profile.default]\nollama_model = "llama3"\nvoice_profile_path = "x"\ndefault_platforms = ["mastodon"]\n''', encoding="utf-8")
    cfg = manager.load()
    assert cfg.schema_version == "1.0"
    assert manager.config_path.with_suffix(".toml.backup").exists()
