# Architecture

GhostWriter is a local-first CLI application organized into small modules with explicit trust boundaries.

## System context

```text
Local corpus --> Voice Engine --> Voice Profile
Voice Profile + User Prompt --> Prompt Builder --> Ollama on 127.0.0.1
Ollama draft --> Review TUI --> Approved staged draft
Approved staged draft --> Publisher adapter --> Platform API
Session temp files / successful staged draft --> Eraser
```

## Package layout

```text
gw/
├── cli.py              Command entry point and top-level flows
├── models.py           Shared dataclasses
├── errors.py           Domain exceptions and exit codes
├── logging.py          Sanitized logging
├── voice/              Corpus analysis and profile generation
├── prompt/             Prompt building and injection mitigation
├── llm/                Ollama client
├── tui/                Textual review UI + fallback
├── publishers/         Mastodon, Bluesky, Ghost, Substack adapters
├── auth/               Credential storage
├── config/             TOML config management and migrations
└── eraser/             Best-effort secure deletion
```

## Main components

### CLI

`gw/cli.py` owns command parsing and orchestration. It converts domain exceptions into documented exit codes and keeps machine-readable data on stdout where possible.

### Voice Engine

`gw/voice/engine.py` validates corpus paths, reads UTF-8 `.txt` / `.md` files, and generates a `VoiceProfile`.

Privacy invariant: no verbatim corpus text in the profile.

### Prompt Builder

`gw/prompt/builder.py` converts profile metrics into natural-language style instructions and sanitizes user prompts by removing injection markers and truncating to 2,000 characters.

### Ollama Client

`gw/llm/ollama.py` wraps the Ollama REST API. It defaults to loopback and blocks remote hosts without an explicit override.

### Review TUI

`gw/tui/review.py` provides a Textual app for review/edit/approve/reject. A minimal fallback preserves functionality when Textual is unavailable or terminal interactivity is limited.

### Publishers

Publisher adapters implement non-throwing `publish()` methods and return `PublishResult`.

- Mastodon: REST status API, thread splitting, per-chunk idempotency
- Bluesky: AT Protocol, grapheme limit, rich-text facets
- Ghost: Admin API JWT
- Substack: unofficial API with warnings

### Credential Store

`gw/auth/store.py` uses OS keychain first. If unavailable, it encrypts credentials with AES-256-GCM using a passphrase-derived key.

### Config Manager

`gw/config/manager.py` reads/writes TOML config, manages schema versions, and backs up before migrations.

### Eraser

`gw/eraser/secure.py` overwrites and unlinks ephemeral files. It warns for filesystems where overwrite semantics are weak.

## Trust zones

| Zone | Trust level | Examples |
|---|---|---|
| Local machine | trusted | corpus, config, profiles, temp files |
| Local Ollama | trusted if bound to loopback | generation endpoint |
| Platform APIs | semi-trusted | Mastodon, Bluesky, Ghost, Substack |
| Internet | untrusted | all other destinations |

## Failure principles

- Domain failures become clear user-facing messages.
- Publisher adapters return `PublishResult` rather than raising.
- Cleanup uses `finally` for session files.
- Partial publish success is reported; it is not silently treated as success.

## Decision records

See [ADR index](adr/README.md).
