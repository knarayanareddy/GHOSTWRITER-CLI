# Development Guide

## Setup

```bash
git clone https://github.com/knarayanareddy/GHOSTWRITER-CLI.git
cd GHOSTWRITER-CLI
python -m pip install --require-hashes -r requirements.txt
python -m pip install -e ".[dev]"
```

Use an isolated config directory while developing:

```bash
export GHOSTWRITER_CONFIG_DIR="$PWD/.tmp-config"
```

Do not commit `.tmp-config` or any real credentials.

## Run locally

```bash
ghostwriter doctor --json
ghostwriter train --corpus tests/fixtures/synthetic_corpus.md --min-tokens 10
```

## Quality gates

Run before every PR:

```bash
ruff check gw tests
mypy gw
bandit -q -r gw -c pyproject.toml
pytest --cov=gw --cov-report=term-missing --cov-fail-under=85
```

## Coding standards

- Python 3.10+ compatible syntax.
- Keep runtime dependencies pinned in `pyproject.toml`.
- Keep release lock hashes in `requirements.txt`.
- No telemetry or automatic network calls.
- No raw corpus, raw prompts, or credentials in logs.
- Publisher adapters should never raise from `publish()`; return `PublishResult`.
- Prefer small, testable functions.

## Adding a command

1. Add command in `gw/cli.py`.
2. Add or reuse domain errors in `gw/errors.py`.
3. Keep user-facing progress/errors on stderr.
4. Keep machine-readable output on stdout.
5. Add tests under `tests/component/`.
6. Update `README.md` and `docs/usage.md`.

## Adding a publisher

1. Create `gw/publishers/<platform>.py`.
2. Implement non-throwing `publish()` returning `PublishResult`.
3. Add factory routing in `gw/publishers/base.py`.
4. Add credential prompts in `_prompt_credentials()`.
5. Add docs in `docs/publisher-setup.md`.
6. Add tests for success, retry, auth failure, timeout, dry run.
7. Confirm final publish gate is still outside the adapter in CLI flow.

## Adding config schema fields

1. Add field to `ProfileConfig` / config parsing.
2. Add TOML serialization.
3. If schema changes incompatibly, add migration module in `gw/config/migrations/`.
4. Backup-before-migrate is required.
5. Update `docs/configuration.md`.

## Dependency updates

1. Update `pyproject.toml`.
2. Regenerate `requirements.txt` with hashes using `pip-compile --generate-hashes`.
3. Run full quality gates.
4. Review licenses and security advisories.

## Documentation updates

Any change to command behavior, security assumptions, config schema, publisher behavior, or release flow must include documentation updates.
