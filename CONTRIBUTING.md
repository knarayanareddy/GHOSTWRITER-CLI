# Contributing to GhostWriter CLI

Thank you for contributing. GhostWriter handles private writing and credentials, so changes must preserve privacy and safety by default.

## Before opening a PR

1. Read the design spec: [`GHOSTWRITER-CLIdesigndoc.md`](GHOSTWRITER-CLIdesigndoc.md)
2. Read the development guide: [`docs/development.md`](docs/development.md)
3. Run the full local gates:

```bash
ruff check gw tests
mypy gw
bandit -q -r gw -c pyproject.toml
pytest --cov=gw --cov-report=term-missing --cov-fail-under=85
```

## Pull request requirements

A PR should include:

- clear description of behavior change
- tests for new behavior
- documentation updates for user-visible changes
- security/privacy impact notes
- ADR update if changing architecture or normative requirements

## Non-negotiable rules

- No plaintext credentials on disk.
- No corpus content in network payloads.
- No telemetry or automatic phone-home behavior.
- No publish without human confirmation.
- No raw prompts, corpus excerpts, credentials, or full corpus paths in logs.

## Commit style

Conventional commits are recommended:

```text
feat: add publisher adapter
fix: correct mastodon idempotency keys
docs: expand publisher setup guide
test: cover encrypted credential fallback
```

## Security issues

Do not open public issues for vulnerabilities. Follow [`SECURITY.md`](SECURITY.md).
