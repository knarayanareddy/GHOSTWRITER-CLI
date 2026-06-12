# Changelog

All notable changes to GhostWriter CLI are documented here. The project follows SemVer 2.0.0.

## 1.0.1 - 2026-06-12

### Fixed

- Mastodon thread publishing now uses a unique idempotency key per thread chunk.
- Ghost/Substack credential setup can explicitly authorize live `published` status.
- Bluesky publishing now emits AT Protocol rich-text facets for links and resolvable mentions.
- Successful non-dry-run publishes securely erase the staged approved draft.
- Credential fallback now warns when OS keychain is unavailable before encrypted-file creation.

### Changed

- Draft review now uses a Textual app when Textual is available, with the click fallback retained for minimal/non-interactive environments.
- Added Homebrew and AUR packaging templates.

## 1.0.0 - 2026-06-12

### Added

- Voice engine for local `.txt`/`.md` corpus analysis.
- Non-verbatim voice profile schema v1.0.
- Prompt builder with injection marker sanitization.
- Local-only Ollama REST client.
- Terminal draft review flow with explicit approval gate.
- Mastodon, Bluesky, Ghost, and Substack publisher adapters.
- OS keychain credential store with AES-256-GCM encrypted-file fallback.
- Config manager with TOML schema versioning and backup-before-migration.
- Secure eraser for session temp files.
- `doctor`, `version`, `profile`, `auth`, and `config` CLI commands.
- CI/release workflow definitions, ADRs, SECURITY policy, tests, and benchmark placeholder.
