# Testing Guide

GhostWriter uses unit, component, and security tests.

## Run all tests

```bash
pytest -q
```

## Coverage gate

```bash
pytest --cov=gw --cov-report=term-missing --cov-fail-under=85
```

## Static analysis

```bash
ruff check gw tests
mypy gw
bandit -q -r gw -c pyproject.toml
```

## Test layout

```text
tests/
├── unit/          Isolated module tests
├── component/     CLI and flow tests
├── security/      Redaction/security invariant tests
└── fixtures/      Synthetic corpus only
```

## Security test expectations

Tests should verify:

- credentials do not appear in logs
- prompt injection markers are removed
- voice profiles do not contain verbatim corpus text
- no plaintext credential fallback files
- Mastodon thread idempotency keys are unique
- Bluesky facets use UTF-8 byte offsets
- staged drafts are erased after successful publish

## External services

Unit/component tests must not require real credentials or live platform APIs. Use mocked HTTP clients and synthetic data.

## Manual smoke tests

```bash
export GHOSTWRITER_CONFIG_DIR="$(mktemp -d)"
ghostwriter doctor --json
ghostwriter train --corpus tests/fixtures/synthetic_corpus.md --min-tokens 10
```

For write flow, ensure Ollama is running:

```bash
ollama serve
ollama pull llama3
ghostwriter write --prompt "Write a two paragraph test draft"
```
