# GhostWriter CLI

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Local-first](https://img.shields.io/badge/privacy-local--first-purple.svg)](docs/privacy-security.md)

GhostWriter CLI is a **local-first, privacy-preserving AI writing assistant** for writers, bloggers, and indie creators. It learns a non-verbatim style fingerprint from your own local `.txt` / `.md` writing corpus, generates drafts through a **local Ollama model**, lets you review and edit drafts in a terminal UI, and publishes only after explicit confirmation.

> One-line spec: train on your private corpus, write in your voice with local Ollama, review before publishing, and keep corpus data off the network.

---

## Table of contents

- [Why GhostWriter?](#why-ghostwriter)
- [Current status](#current-status)
- [Core guarantees](#core-guarantees)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [End-to-end workflow](#end-to-end-workflow)
- [Command reference](#command-reference)
- [Data locations](#data-locations)
- [Publisher support](#publisher-support)
- [Security and privacy model](#security-and-privacy-model)
- [Development](#development)
- [Documentation map](#documentation-map)
- [Limitations](#limitations)
- [Support and security reporting](#support-and-security-reporting)
- [License](#license)

---

## Why GhostWriter?

Most AI writing tools force a trade-off:

1. **Generic output** — cloud LLMs do not have a durable understanding of your voice.
2. **Privacy exposure** — uploading journals, essays, drafts, client work, or manuscripts to external services can be unacceptable.

GhostWriter is designed around the opposite defaults:

- Your corpus stays on your machine.
- Voice profiles store metrics, not source passages.
- Generation goes through Ollama on `127.0.0.1` by default.
- Publishing is the only normal network operation, and it always requires explicit confirmation.
- There is no telemetry, analytics, crash reporting, or automatic update ping.

---

## Current status

GhostWriter CLI is implemented as a production-oriented beta package.

- Package version: `1.0.1`
- Python support: `>=3.10`
- Primary LLM backend: Ollama only
- Supported corpus input: UTF-8 `.txt` and `.md`
- Supported publishers: Mastodon, Bluesky, Ghost, Substack
- Design source of truth: [`GHOSTWRITER-CLIdesigndoc.md`](GHOSTWRITER-CLIdesigndoc.md)

---

## Core guarantees

- **No corpus copying:** corpus files are read in place.
- **No verbatim corpus in profiles:** voice profiles store metrics only; recurring n-grams are hashed.
- **Local generation by default:** Ollama defaults to `http://127.0.0.1:11434`.
- **Remote Ollama blocked by default:** remote hosts require `--allow-remote-ollama`.
- **No plaintext credentials:** OS keychain first; AES-256-GCM encrypted-file fallback.
- **Human approval required:** drafts must be approved before publishing.
- **Publish confirmation required:** every publish target prompts with default `No`.
- **No telemetry:** no analytics, crash beacons, automatic version checks, or background network calls.
- **Best-effort secure cleanup:** session temp files and successfully published staged drafts are erased using the eraser module.

---

## Features

### Voice and style analysis

`ghostwriter train` analyzes a local corpus and extracts:

- token count
- average sentence length
- sentence length distribution
- vocabulary richness
- hashed top n-grams
- tonal register heuristic
- punctuation fingerprint
- structural patterns

The output is a JSON voice profile under `~/.config/ghostwriter/profiles/` by default.

### Local draft generation

`ghostwriter write` combines:

- your voice profile metrics
- a sanitized user prompt
- a local Ollama model

It then opens the draft review flow. Approved drafts are staged for publishing.

### Draft review UI

When Textual is available in an interactive terminal, GhostWriter uses a Textual terminal application for draft review and editing. A minimal prompt fallback remains for non-interactive or minimal environments.

### Publisher adapters

- Mastodon REST API with thread splitting and per-post idempotency keys
- Bluesky AT Protocol with grapheme counting and rich-text facets for links / resolvable mentions
- Ghost Admin API with draft-first defaults
- Substack unofficial API support with warning on every use

### Secure credentials

- Primary: OS keychain through `keyring`
- Fallback: encrypted file at `~/.config/ghostwriter/credentials.enc`
- Fallback encryption: PBKDF2-HMAC-SHA256 + AES-256-GCM
- Credential values are never printed by `config show`, `doctor`, or logs.

---

## Requirements

### Runtime

| Requirement | Minimum | Recommended |
|---|---:|---:|
| Python | 3.10 | 3.12+ |
| Ollama | Latest stable | Latest stable |
| RAM | 8 GB for small local models | 16 GB+ |
| Disk | 5 GB+ for a 7B model | 10 GB+ |
| OS | macOS 12+, Linux | macOS 14+, Ubuntu 22.04+ |

### Ollama setup

Install Ollama, then run:

```bash
ollama serve
ollama pull llama3
```

The default profile uses `llama3`. You can change this in `~/.config/ghostwriter/config.toml`.

---

## Installation

### From this repository

```bash
git clone https://github.com/knarayanareddy/GHOSTWRITER-CLI.git
cd GHOSTWRITER-CLI
python -m pip install .
ghostwriter --version
```

### Editable development install

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pip install -e .
```

### With developer tools

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pip install -e ".[dev]"
```

### PyPI / Homebrew / AUR

The project includes release templates for all target channels:

- PyPI package name: `ghostwriter-cli`
- Homebrew formula template: [`packaging/homebrew/ghostwriter-cli.rb`](packaging/homebrew/ghostwriter-cli.rb)
- AUR PKGBUILD template: [`packaging/aur/PKGBUILD`](packaging/aur/PKGBUILD)

Until a tagged artifact is published, install from the repository as shown above. Release maintainers must replace placeholder SHA-256 values during publication.

---

## Quickstart

```bash
# 1. Check environment
ghostwriter doctor

# 2. Train on local UTF-8 .txt/.md writing samples
ghostwriter train --corpus ~/writing-samples

# 3. Generate and review a draft
ghostwriter write --prompt "Write a short post about building creative discipline"

# 4. Store credentials securely
ghostwriter auth set mastodon

# 5. Publish the approved staged draft after final confirmation
ghostwriter publish --platform mastodon
```

For a completely safe local smoke test using the synthetic fixture:

```bash
export GHOSTWRITER_CONFIG_DIR="$(mktemp -d)"
ghostwriter train --corpus tests/fixtures/synthetic_corpus.md --min-tokens 10
ghostwriter doctor --json
```

---

## End-to-end workflow

### 1. Prepare a corpus

Use your own `.txt` or `.md` files. The corpus should be representative of the voice you want GhostWriter to emulate.

Recommended:

- 5–50 writing samples
- 1,000+ tokens total
- UTF-8 encoding
- remove text you do not want reflected stylistically

Not supported in Phase 1:

- PDF
- DOCX
- HTML import
- image/audio/video input

### 2. Train a voice profile

```bash
ghostwriter train --corpus ~/writing-samples
```

Repeat `--corpus` for multiple paths:

```bash
ghostwriter train --corpus ~/essays --corpus ~/blog-posts --corpus ~/notes/style.md
```

The generated profile contains no verbatim source passages.

### 3. Generate a draft

```bash
ghostwriter write --prompt "Draft a 600-word essay about attention and craft" --save
```

GhostWriter will:

1. load the active profile
2. build natural-language style instructions from metrics
3. sanitize the prompt
4. call local Ollama
5. open the review UI
6. stage the draft only if approved

### 4. Configure credentials

```bash
ghostwriter auth set mastodon
ghostwriter auth set bluesky
ghostwriter auth set ghost
ghostwriter auth set substack
```

Ghost and Substack default to draft status. If you configure `published`, GhostWriter asks for a second explicit confirmation before storing `confirmed_publish = "true"`.

### 5. Publish

```bash
ghostwriter publish --platform mastodon
```

Multiple platforms:

```bash
ghostwriter publish --platform mastodon --platform bluesky
```

Each platform gets an explicit final confirmation prompt. After all attempted targets succeed in a non-dry-run publish, the staged draft file is securely erased.

---

## Command reference

### Global flags

```text
ghostwriter [OPTIONS] COMMAND [ARGS]...

Options:
  --profile TEXT                  Override active profile for this invocation.
  --log-level [debug|info|warn|warning|error]
  --log-file PATH                 Write logs to file.
  --no-color                      Disable ANSI color output.
  --dry-run                       Execute all steps except actual publish calls.
  --yes                           Auto-confirm non-destructive prompts only; never publishes.
  --version                       Show version and exit.
  --help                          Show help.
```

### `train`

```bash
ghostwriter train --corpus <path> [--corpus <path> ...] [--output <path>] [--min-tokens N] [--max-tokens N] [--force]
```

Analyzes UTF-8 `.txt` / `.md` files and writes a voice profile.

### `write`

```bash
ghostwriter write --prompt <text> [--timeout N] [--json] [--save]
```

Generates a draft through local Ollama and opens review UI.

Remote Ollama is blocked unless explicitly allowed:

```bash
ghostwriter write \
  --prompt "Draft a newsletter intro" \
  --ollama-base-url http://remote-host:11434 \
  --allow-remote-ollama
```

Only use this if you understand that prompt data may leave the machine.

### `publish`

```bash
ghostwriter publish --platform mastodon
```

Supported platform values:

- `mastodon`
- `bluesky`
- `ghost`
- `substack`

### `auth`

```bash
ghostwriter auth set <platform>
ghostwriter auth test <platform>
ghostwriter auth revoke <platform>
```

### `profile`

```bash
ghostwriter profile list
ghostwriter profile switch <name>
ghostwriter profile delete <name>
```

### `config`

```bash
ghostwriter config show
ghostwriter config reset
```

### `doctor`

```bash
ghostwriter doctor
ghostwriter doctor --json > doctor-report.json
```

`doctor --json` is designed to be safe to share. It does not include credentials or corpus paths.

---

## Data locations

Default config directory:

```text
~/.config/ghostwriter/
```

Typical layout:

```text
~/.config/ghostwriter/
├── config.toml
├── credentials.enc          # only if encrypted fallback is used
├── profiles/
│   └── default.json
└── drafts/
    ├── staged.json          # ephemeral approved draft waiting for publish
    └── <timestamp>-slug.md  # optional saved draft when --save is used
```

Override for testing or isolation:

```bash
export GHOSTWRITER_CONFIG_DIR=/tmp/ghostwriter-test
```

---

## Publisher support

| Platform | Status | Auth | Notes |
|---|---|---|---|
| Mastodon | Implemented | OAuth access token | Long posts split into reply threads. |
| Bluesky | Implemented | Handle + app password | 300 grapheme limit; link and resolvable mention facets. |
| Ghost | Implemented | Admin API key | Defaults to draft; live publish requires explicit credential opt-in and final publish confirmation. |
| Substack | Implemented with caveat | Session cookie | Unofficial API; warnings emitted on every use. |

Detailed setup: [`docs/publisher-setup.md`](docs/publisher-setup.md)

---

## Security and privacy model

GhostWriter has a strict local-first model:

- Training reads local files only.
- Writing contacts only local Ollama by default.
- Publishing contacts only selected platform APIs.
- Logs are sanitized for credentials, raw prompts, and sensitive paths.
- Credential fallback encryption uses PBKDF2 + AES-256-GCM.
- Secure deletion is best effort and weaker on SSD/COW filesystems.

Read more:

- [`docs/privacy-security.md`](docs/privacy-security.md)
- [`SECURITY.md`](SECURITY.md)
- [`GHOSTWRITER-CLIdesigndoc.md`](GHOSTWRITER-CLIdesigndoc.md)

---

## Development

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pip install -e ".[dev]"
ruff check gw tests
mypy gw
bandit -q -r gw -c pyproject.toml
pytest --cov=gw --cov-report=term-missing --cov-fail-under=85
```

Project layout:

```text
gw/                    Runtime package
tests/                 Unit, component, and security tests
docs/                  User, developer, architecture, and release docs
packaging/             Homebrew/AUR templates
benchmarks/results/    Versioned benchmark records
.github/workflows/     CI and release workflows
```

Developer guide: [`docs/development.md`](docs/development.md)

---

## Documentation map

| Document | Purpose |
|---|---|
| [`docs/getting-started.md`](docs/getting-started.md) | First successful local run. |
| [`docs/usage.md`](docs/usage.md) | CLI workflows and command examples. |
| [`docs/configuration.md`](docs/configuration.md) | Config files, schema, profiles, env vars. |
| [`docs/publisher-setup.md`](docs/publisher-setup.md) | Platform credential setup. |
| [`docs/privacy-security.md`](docs/privacy-security.md) | Threat model and data handling. |
| [`docs/architecture.md`](docs/architecture.md) | Component architecture and data flow. |
| [`docs/development.md`](docs/development.md) | Local dev setup and coding standards. |
| [`docs/testing.md`](docs/testing.md) | Test strategy and CI gates. |
| [`docs/release.md`](docs/release.md) | Release and rollback process. |
| [`docs/packaging.md`](docs/packaging.md) | PyPI, Homebrew, and AUR packaging. |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common errors and fixes. |
| [`docs/faq.md`](docs/faq.md) | Frequently asked questions. |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records. |

---

## Limitations

- Voice modeling is prompt-layer only; no model fine-tuning.
- Corpus input is limited to UTF-8 `.txt` and `.md`.
- Secure deletion is best effort on SSD/APFS/btrfs/COW filesystems.
- Substack has no official stable API; integration may break.
- Homebrew/AUR files are release templates until a tagged artifact is published.

---

## Support and security reporting

- General support: [`SUPPORT.md`](SUPPORT.md)
- Contributions: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Vulnerabilities: [`SECURITY.md`](SECURITY.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

---

## License

GhostWriter CLI is released under the [MIT License](LICENSE).
