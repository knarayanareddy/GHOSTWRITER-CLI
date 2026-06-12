

---

Here is the complete replacement design document. Copy this verbatim into your repo.

---

```markdown
# GHOSTWRITER CLI
## Engineering Design Specification — Single Source of Truth

---

## DOCUMENT CONTROL

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Document ID**    | GW-SPEC-001                                |
| **Version**        | 2.0.0                                      |
| **Status**         | Approved — Active SSOT                     |
| **Owner**          | @knarayanareddy                            |
| **Reviewers**      | (list names/handles before merging)        |
| **Last Updated**   | 2026-06-12                                 |
| **License**        | MIT (or specify)                           |
| **Canonical Ref**  | `main/GHOSTWRITER-CLIdesigndoc.md`         |

> **Canonical Rule:** This document is the authoritative source for all
> architecture, interface, security, and release decisions. If code and
> this spec disagree, **this spec is wrong and must be updated via PR
> before the code ships.** Do not implement from README summaries or
> inline code comments alone.

---

## CHANGELOG

| Version | Date       | Author          | Summary                                   |
|---------|------------|-----------------|-------------------------------------------|
| 2.0.0   | 2026-06-12 | @knarayanareddy | Full rewrite — production spec structure  |
| 1.0.0   | (original) | @knarayanareddy | Initial design document                   |

---

## NORMATIVE LANGUAGE

This document uses RFC 2119 semantics throughout:

- **MUST** / **MUST NOT** — absolute requirement; non-compliance blocks
  merge
- **SHOULD** / **SHOULD NOT** — strong recommendation; deviation requires
  ADR
- **MAY** — optional; use engineering judgment

---

## TABLE OF CONTENTS

1. [Problem Statement & Product Vision](#1-problem-statement--product-vision)
2. [Goals, Non-Goals & Constraints](#2-goals-non-goals--constraints)
3. [Architecture Overview](#3-architecture-overview)
4. [Component Design](#4-component-design)
5. [CLI Contract — Commands, Flags, Exit Codes](#5-cli-contract)
6. [Data Architecture & Lifecycle](#6-data-architecture--lifecycle)
7. [Security Architecture](#7-security-architecture)
8. [Publisher Integration Contracts](#8-publisher-integration-contracts)
9. [Voice & Style Engine Contract](#9-voice--style-engine-contract)
10. [Logging & Observability](#10-logging--observability)
11. [Testing Architecture](#11-testing-architecture)
12. [CI/CD Pipeline & Release Contract](#12-cicd-pipeline--release-contract)
13. [Packaging & Distribution](#13-packaging--distribution)
14. [Performance Targets](#14-performance-targets)
15. [Error Handling & Failure Modes](#15-error-handling--failure-modes)
16. [Operational Readiness](#16-operational-readiness)
17. [Known Limitations & Technical Debt](#17-known-limitations--technical-debt)
18. [Future Roadmap (Phase 2+)](#18-future-roadmap-phase-2)
19. [Architecture Decision Records (ADR Index)](#19-architecture-decision-records)

---

## 1. Problem Statement & Product Vision

### 1.1 Problem

Writers, bloggers, and indie creators who want to maintain a consistent,
authentic voice across long-form content and multiple publishing platforms
currently face two painful tradeoffs:

1. **Generic AI output** — cloud-based LLM tools (ChatGPT, Claude, Jasper)
   produce content that does not reflect the user's personal style,
   vocabulary, and tonal fingerprint because they have no durable memory
   of that fingerprint.
2. **Privacy exposure** — submitting a personal corpus (journals,
   manuscripts, previous articles) to a cloud API is a meaningful privacy
   risk for personal or commercially sensitive writing.

### 1.2 Vision

**GhostWriter CLI** is a local-first, privacy-preserving AI writing
assistant that learns a writer's authentic voice from their own text corpus
and uses that voice model to generate, refine, and publish content — all
without sending private data to external services.

It runs entirely on the user's machine, uses a locally-hosted Ollama LLM,
and publishes to social/blog platforms only on explicit user command.

### 1.3 One-line Spec

> A terminal-based creative writing assistant that trains on your private
> corpus, generates content in your voice via Ollama, and publishes to
> Mastodon/Bluesky/Ghost/Substack — with zero corpus data ever leaving
> your machine.

---

## 2. Goals, Non-Goals & Constraints

### 2.1 Goals (MVP)

| # | Goal                                                                             | Priority |
|---|----------------------------------------------------------------------------------|----------|
| G1 | Analyze a local corpus to extract voice/style fingerprint                       | P0       |
| G2 | Generate draft content in the user's voice via local Ollama                     | P0       |
| G3 | Interactive TUI for draft review, editing, and approval before publish          | P0       |
| G4 | Publish to Mastodon, Bluesky, Ghost, Substack via platform APIs                 | P0       |
| G5 | Secure credential storage (OS keychain or encrypted file); never plaintext      | P0       |
| G6 | Corpus data MUST NOT leave the local machine at any point in the pipeline       | P0       |
| G7 | Ephemeral session data MUST be wiped after use; persistent data is user-controlled | P0    |
| G8 | Voice analysis completes in < 60 seconds for a typical corpus (< 500K tokens)   | P1       |
| G9 | Content generation completes in < 30 seconds per draft on target hardware       | P1       |
| G10| One-command install via pip / Homebrew / AUR                                    | P1       |

### 2.2 Non-Goals (Explicit Out-of-Scope)

| # | Non-Goal                                                                          |
|---|-----------------------------------------------------------------------------------|
| N1 | Cloud/SaaS deployment — GhostWriter is local-only                                |
| N2 | Multi-user or team collaboration                                                  |
| N3 | Training or fine-tuning model weights (only prompt-layer voice injection)         |
| N4 | Corpus backup, sync, or version control (user owns that entirely)                 |
| N5 | Image, audio, or video content generation                                         |
| N6 | Built-in analytics or usage dashboards                                            |
| N7 | Automatic publishing (publish step MUST always require explicit user approval)    |
| N8 | Support for Python < 3.10                                                         |

### 2.3 Hard Constraints

| Constraint                 | Requirement                                                  |
|----------------------------|--------------------------------------------------------------|
| **Runtime**                | Python 3.10+ MUST be the minimum supported version           |
| **LLM backend**            | Ollama MUST be the only LLM backend for MVP                  |
| **Corpus privacy**         | Corpus text MUST NEVER be sent to any external API or network |
| **Credentials**            | API tokens MUST NEVER be stored in plaintext on disk         |
| **Publish gate**           | A human confirmation step MUST precede every publish call    |
| **Telemetry**              | Zero telemetry, analytics, or crash reporting — non-negotiable |
| **Dependencies**           | All runtime deps MUST be listed in `pyproject.toml`; no implicit system deps |

---

## 3. Architecture Overview

### 3.1 System Context

```
┌─────────────────────────────────────────────────────────────┐
│                      USER'S MACHINE                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │   Corpus     │    │        GHOSTWRITER CLI           │  │
│  │   (local     │───▶│  ┌──────────┐  ┌─────────────┐  │  │
│  │   files)     │    │  │  Voice   │  │  Generator  │  │  │
│  └──────────────┘    │  │  Engine  │─▶│  (Ollama)   │  │  │
│                      │  └──────────┘  └──────┬──────┘  │  │
│  ┌──────────────┐    │                        │         │  │
│  │   Config /   │───▶│  ┌──────────────────── ▼──────┐ │  │
│  │   Profile    │    │  │        TUI (Textual)        │ │  │
│  │   Store      │    │  └──────────────┬─────────────┘ │  │
│  └──────────────┘    │                 │ (user approves)│  │
│                      │  ┌──────────────▼─────────────┐ │  │
│  ┌──────────────┐    │  │    Publisher Multiplexer   │ │  │
│  │   OS         │───▶│  └──────────────┬─────────────┘ │  │
│  │   Keychain / │    │                 │               │  │
│  │   Encrypted  │    └─────────────────┼───────────────┘  │
│  │   Token Store│                      │                   │
│  └──────────────┘           HTTPS only │                   │
└─────────────────────────────────────────┼───────────────────┘
                                          │
              ┌───────────────────────────┼────────────────────┐
              │  (Semi-trusted)           │    Platform APIs   │
              ├──────────────┬────────────┼────────┬───────────┤
              │  Mastodon    │  Bluesky   │  Ghost │ Substack  │
              └──────────────┴────────────┴────────┴───────────┘
```

### 3.2 Trust Zones

| Zone             | Trust Level   | What lives there                            | Rules                                            |
|------------------|---------------|---------------------------------------------|--------------------------------------------------|
| **Local Machine**| Fully trusted | Corpus, config, voice model, session data   | No data exits except explicit publish            |
| **Ollama API**   | Trusted       | LLM inference (localhost only)              | MUST bind to 127.0.0.1 only; never exposed       |
| **Platform APIs**| Semi-trusted  | Mastodon, Bluesky, Ghost, Substack          | HTTPS required; credentials from keychain only   |
| **Internet**     | Untrusted     | Everything else                             | No outbound connections except to approved APIs  |

### 3.3 Data Flow Phases

```
Phase 1: TRAIN
  Corpus files → Voice Engine → Voice Profile (local JSON)

Phase 2: WRITE
  Voice Profile + User Prompt → Prompt Builder → Ollama API (localhost)
  → Draft → TUI (review/edit/approve) → Staged Draft (local temp file)

Phase 3: PUBLISH
  Staged Draft → Publisher Multiplexer → Platform API (HTTPS)
  → Success/Failure → Secure Erase of temp artifacts

Phase 4: ERASE
  All session temp files → Secure Overwrite → Deletion
  (Persistent data: profiles, config, approved drafts — user-managed)
```

### 3.4 Component Ownership Matrix

| Component              | Module                    | Primary Concern                        | Owner      |
|------------------------|---------------------------|----------------------------------------|------------|
| Voice Engine           | `gw/voice/`               | Corpus analysis, style fingerprint     | Core team  |
| Prompt Builder         | `gw/prompt/`              | Voice injection into LLM prompts       | Core team  |
| Ollama Client          | `gw/llm/`                 | LLM API abstraction (localhost only)   | Core team  |
| TUI                    | `gw/tui/`                 | Draft review, approval gate            | Core team  |
| Publisher Multiplexer  | `gw/publishers/`          | Platform routing + retry               | Core team  |
| Config Manager         | `gw/config/`              | Profile storage, schema versioning     | Core team  |
| Credential Store       | `gw/auth/`                | OS keychain / encrypted token file     | Core team  |
| Eraser                 | `gw/eraser/`              | Secure overwrite + deletion            | Core team  |
| CLI Entry              | `gw/cli.py`               | Command parsing, top-level flow        | Core team  |

---

## 4. Component Design

### 4.1 Voice Engine (`gw/voice/`)

**Purpose:** Ingest a local corpus and extract a durable voice profile —
vocabulary distribution, sentence length distribution, punctuation style,
tonal register markers, and common structural patterns.

**Interface:**

```python
class VoiceEngine:
    def analyze(
        self,
        corpus_paths: list[Path],
        output_profile_path: Path,
        *,
        min_tokens: int = 1000,
        max_tokens: int = 500_000,
    ) -> VoiceProfile:
        """
        Analyze corpus files and write a VoiceProfile to disk.

        Raises:
            CorpusError: if corpus is below min_tokens
            CorpusError: if corpus exceeds max_tokens without --force flag
            FileNotFoundError: if any corpus_paths do not exist
        """
```

**VoiceProfile Schema (JSON):**

```json
{
  "schema_version": "1.0",
  "created_at": "<ISO-8601>",
  "corpus_hash": "<sha256 of sorted file paths + sizes — NOT content>",
  "metrics": {
    "avg_sentence_length": 18.4,
    "vocabulary_richness": 0.72,
    "top_n_grams": [...],
    "tonal_register": "conversational|formal|lyrical|technical",
    "punctuation_fingerprint": {...},
    "structural_patterns": [...]
  }
}
```

> **Privacy Rule:** The `corpus_hash` MUST be a hash of file paths and
> sizes only — never corpus content. Voice profiles MUST NOT contain any
> verbatim corpus text.

**Performance target:** < 60 seconds for corpus up to 500K tokens on a
2022 M1 MacBook Pro baseline (see §14).

---

### 4.2 Prompt Builder (`gw/prompt/`)

**Purpose:** Construct the LLM prompt that injects the user's voice profile
as context before the generation request.

**Hard Rules:**
- The prompt builder MUST sanitize user input to prevent prompt injection
  (see §7.3).
- Voice profile metrics MUST be translated to natural-language style
  instructions, not raw JSON injected verbatim.
- The builder MUST NOT include any verbatim corpus excerpts in the prompt.

**Prompt structure:**

```
[SYSTEM]
You are a writing assistant. Write in the following style:
<natural language description of voice metrics>

Do not explain. Do not add commentary. Output only the draft content.

[USER]
<user's topic/prompt — sanitized>
```

---

### 4.3 Ollama Client (`gw/llm/`)

**Purpose:** Isolated abstraction layer over the Ollama REST API. All LLM
calls MUST go through this module.

**Interface:**

```python
class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        ...

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        timeout_seconds: int = 60,
        stream: bool = True,
    ) -> Generator[str, None, None]:
        """
        Streams generated tokens.

        Raises:
            OllamaConnectionError: if Ollama is not running
            OllamaTimeoutError: if generation exceeds timeout_seconds
            OllamaModelError: if model is not available locally
        """
```

**Hard Rules:**
- `base_url` MUST default to `127.0.0.1` and MUST NOT be configurable to
  an external host without explicit `--allow-remote-ollama` flag AND a
  prominent security warning.
- No raw prompt text MUST appear in logs (see §10).

---

### 4.4 TUI — Draft Review (`gw/tui/`)

**Purpose:** Present the generated draft to the user for review, inline
editing, and explicit approval or rejection before any publish action.

**State Machine:**

```
GENERATED → [USER REVIEWS] → APPROVED → [PUBLISH GATE CONFIRM] → PUBLISHED
                          ↘ EDITED → APPROVED → ...
                          ↘ REJECTED → (draft discarded, session ends)
```

**Hard Rules:**
- A draft MUST NOT be published without passing through `APPROVED` state.
- The publish gate MUST display a final confirmation prompt (e.g.
  `Publish to Mastodon? [y/N]`) with default `N`.
- TUI MUST NOT auto-submit or auto-confirm after any timeout.

---

### 4.5 Publisher Multiplexer (`gw/publishers/`)

**Purpose:** Route an approved draft to one or more target platforms.

**Interface:**

```python
class Publisher(Protocol):
    platform: str

    def publish(self, draft: ApprovedDraft) -> PublishResult:
        """
        Attempt to publish. Must be idempotent via draft.idempotency_key.

        Returns: PublishResult(success=True|False, url=str|None, error=str|None)
        Raises:  Never — errors captured in PublishResult
        """
```

**Platform routing rules:**

| Platform  | Adapter Module                    | Auth Method           |
|-----------|-----------------------------------|-----------------------|
| Mastodon  | `gw/publishers/mastodon.py`       | OAuth access token    |
| Bluesky   | `gw/publishers/bluesky.py`        | App password / DID    |
| Ghost     | `gw/publishers/ghost.py`          | Admin API key (JWT)   |
| Substack  | `gw/publishers/substack.py`       | Session cookie / API  |

**Retry contract:**
- Transient failures (HTTP 429, 502, 503) MUST be retried with
  exponential backoff: 1s, 2s, 4s (max 3 attempts).
- Permanent failures (HTTP 401, 403, 404, 422) MUST NOT be retried.
- All retry attempts MUST be logged at `DEBUG` level with attempt number
  and delay.
- The `idempotency_key` (SHA-256 of content + platform + timestamp-bucket)
  MUST be checked before each retry to prevent duplicate posts.

---

### 4.6 Credential Store (`gw/auth/`)

**Purpose:** Secure storage and retrieval of platform API tokens.

**Storage priority:**

```
1. OS Keychain (macOS Keychain, Linux Secret Service, Windows DPAPI)
   via `keyring` library
   ↓ (if keyring unavailable)
2. Encrypted file at ~/.config/ghostwriter/credentials.enc
   (AES-256-GCM, key derived from user passphrase via PBKDF2)
   ↓ (never)
3. Plaintext ← MUST NEVER HAPPEN
```

**Hard Rules:**
- Credentials MUST NEVER be written to disk in plaintext.
- Credentials MUST NEVER appear in log output (see §10).
- Credentials MUST NEVER be included in error messages or stack traces.
- If OS keychain is unavailable and encrypted file does not exist, CLI
  MUST prompt for passphrase before first-time credential storage and
  MUST warn the user about the fallback.

---

### 4.7 Config Manager (`gw/config/`)

**Purpose:** Manage user profiles (voice profiles + preferences + platform
targets) with schema versioning and migration.

**Config file:** `~/.config/ghostwriter/config.toml`

**Schema version field:**

```toml
[meta]
schema_version = "1.0"

[profile.default]
ollama_model = "llama3"
voice_profile_path = "~/.config/ghostwriter/profiles/default.json"
default_platforms = ["mastodon"]
```

**Migration contract:**
- Every schema version bump MUST include a migration function in
  `gw/config/migrations/`.
- On startup, the config manager MUST check `schema_version` and apply
  any pending migrations automatically.
- Migration MUST create a `.backup` copy of the old config before
  transforming.
- If migration fails, the CLI MUST exit with code `78` (EX_CONFIG) and
  print a recovery message.

---

### 4.8 Eraser (`gw/eraser/`)

**Purpose:** Securely overwrite and delete session-ephemeral files.

**Target files:**
- Staged draft temp files
- Intermediate prompt files (if written to disk)
- Any voice analysis intermediaries not needed for the profile

**Overwrite strategy:**
- MUST perform at least one overwrite pass with random bytes before
  unlinking.
- MUST log a WARNING if running on a known SSD/APFS/btrfs filesystem,
  advising the user that overwrite guarantees are reduced and
  recommending full-disk encryption.
- MUST NOT be skipped or made optional — it MUST always run at end of
  session, even on error paths (use `finally` blocks).

---

## 5. CLI Contract

> This section is the normative definition of the GhostWriter CLI
> user-facing interface. All flags, exit codes, and stdout/stderr
> conventions defined here are binding. Changes require a version bump
> and ADR.

### 5.1 Command Grammar

```
ghostwriter <command> [subcommand] [options] [arguments]
```

### 5.2 Command Reference

| Command                               | Description                                         |
|---------------------------------------|-----------------------------------------------------|
| `ghostwriter train [--corpus <path>]` | Analyze corpus and build voice profile              |
| `ghostwriter write [--prompt <text>]` | Generate a draft in your voice; opens TUI           |
| `ghostwriter publish [--platform <p>]`| Publish an approved draft (requires prior `write`)  |
| `ghostwriter profile list`            | List saved profiles                                 |
| `ghostwriter profile switch <name>`   | Switch active profile                               |
| `ghostwriter profile delete <name>`   | Delete a profile (prompts for confirmation)         |
| `ghostwriter auth set <platform>`     | Store credentials for a platform                   |
| `ghostwriter auth revoke <platform>`  | Delete credentials for a platform                  |
| `ghostwriter auth test <platform>`    | Validate stored credentials                        |
| `ghostwriter config show`             | Print current config (NEVER prints credentials)     |
| `ghostwriter config reset`            | Reset config to defaults (prompts for confirmation) |
| `ghostwriter version`                 | Print version and build metadata                    |
| `ghostwriter doctor`                  | Check runtime dependencies (Ollama, keyring, etc.) |

### 5.3 Global Flags

| Flag                  | Type    | Description                                     |
|-----------------------|---------|-------------------------------------------------|
| `--profile <name>`    | string  | Override active profile for this invocation     |
| `--log-level <level>` | string  | `debug`, `info`, `warn`, `error` (default: info)|
| `--log-file <path>`   | path    | Write logs to file (default: stderr only)       |
| `--no-color`          | bool    | Disable ANSI color output                       |
| `--dry-run`           | bool    | Execute all steps except actual publish calls   |
| `--yes`               | bool    | Auto-confirm non-destructive prompts only       |
| `--help`              | bool    | Show help                                       |
| `--version`           | bool    | Print version                                   |

### 5.4 Exit Codes

| Code | Constant    | Meaning                                          |
|------|-------------|--------------------------------------------------|
| 0    | `EX_OK`     | Success                                          |
| 1    | `EX_ERR`    | General unhandled error                          |
| 2    | `EX_USAGE`  | Bad arguments or missing required flag           |
| 64   | `EX_USAGE`  | Command line usage error (BSD convention)        |
| 65   | `EX_DATA`   | Corpus format error                              |
| 69   | `EX_UNAVAIL`| Ollama not running or model not available        |
| 73   | `EX_CANTCREATE` | Cannot write profile/config to disk          |
| 74   | `EX_IOERR`  | IO error reading corpus or config                |
| 77   | `EX_NOPERM` | Credential access denied                         |
| 78   | `EX_CONFIG` | Config schema error or migration failure         |
| 130  | —           | Interrupted by user (SIGINT/Ctrl-C)              |

### 5.5 stdout / stderr Convention

- **stdout**: machine-readable output only (draft content, JSON output with `--json`)
- **stderr**: all user-facing messages, warnings, progress, errors
- Logs (§10): always to stderr by default; optionally to file

This ensures `ghostwriter write --json > draft.txt` works correctly in
shell pipelines.

---

## 6. Data Architecture & Lifecycle

### 6.1 Data Classification

| Data Type                 | Classification    | Location                                    | Persists? |
|---------------------------|-------------------|---------------------------------------------|-----------|
| Corpus text               | Private / Sensitive| User-specified paths (not copied anywhere)  | Yes (user-owned) |
| Voice profile (metrics)   | Private           | `~/.config/ghostwriter/profiles/`           | Yes       |
| Config / preferences      | User              | `~/.config/ghostwriter/config.toml`         | Yes       |
| Platform credentials      | Secret            | OS keychain / encrypted file                | Yes       |
| Generated drafts (staged) | User              | `~/.config/ghostwriter/drafts/` (or temp)   | Optional  |
| Session temp files        | Ephemeral         | OS temp dir (`/tmp/gw-session-XXXX/`)       | No        |
| Log files                 | Operational       | User-specified path only                    | Optional  |

### 6.2 Data Lifecycle Rules

**Corpus:**
- GhostWriter MUST read corpus files in-place; it MUST NOT copy them.
- Corpus paths are stored in the profile only for reference; contents
  MUST NOT be serialized anywhere.

**Voice profiles:**
- Persisted after `train` command.
- Deleted only on explicit `ghostwriter profile delete`.
- MUST include `schema_version` for future migration.

**Session temp files:**
- Created with restrictive permissions: `0600` (owner read/write only).
- MUST be erased by the Eraser module at session end (see §4.8).
- MUST be stored in a uniquely named subdirectory:
  `/tmp/gw-session-<uuid4>/`.

**Approved drafts (optional persistence):**
- If the user opts to save a draft, it is written to
  `~/.config/ghostwriter/drafts/<timestamp>-<slug>.md`.
- Drafts MUST NOT contain the voice profile data used to generate them.
- The user is responsible for managing draft retention.

### 6.3 Config Schema Versioning

Config schema follows `MAJOR.MINOR` semantics:
- `MINOR` bump: additive fields only; backward-compatible.
- `MAJOR` bump: requires migration function and ADR.

---

## 7. Security Architecture

### 7.1 Threat Model

| Threat                          | Asset at Risk          | Attack Surface           | Mitigation                                          |
|----------------------------------|------------------------|--------------------------|-----------------------------------------------------|
| Credential theft (filesystem)    | API tokens             | Config dir               | OS keychain; if file: AES-256-GCM + PBKDF2          |
| Credential leak (logs)           | API tokens             | Log output               | Explicit deny-list in log filter (see §10.3)        |
| Prompt injection                 | LLM output quality     | User-provided prompt     | Sanitization layer in Prompt Builder (see §7.3)     |
| Corpus exfiltration              | Private writing        | Network                  | Ollama bound to 127.0.0.1; no cloud API calls for corpus |
| Malicious corpus files           | Local filesystem       | File parsing             | Path validation; no shell expansion of corpus paths |
| Dependency supply chain attack   | Runtime integrity      | `pip install`            | Pinned deps; hash verification in CI (see §12.3)    |
| Platform API credential replay   | User's social accounts | Network + credential store| HTTPS enforced; credentials per-platform, revocable |
| Temp file exposure               | Draft content          | `/tmp`                   | `0600` permissions; UUID subdirectory; eraser       |

### 7.2 Hard Security Rules

These are non-negotiable. Any PR that violates them MUST be blocked:

1. **No plaintext credentials on disk.** Ever.
2. **No corpus content in network payloads.** Voice profile metrics only.
3. **No outbound connections except to approved platform APIs during
   publish.** (Ollama is localhost.)
4. **No telemetry.** No analytics. No crash reporting. No beacons.
5. **No auto-publish.** Human confirmation is always required.
6. **Credentials MUST NOT appear in logs, error messages, or stack traces.**
7. **Ollama MUST bind to 127.0.0.1 by default** (enforced in OllamaClient;
   any remote override requires explicit flag + warning).

### 7.3 Prompt Injection Mitigation

The Prompt Builder MUST apply the following sanitization to user-provided
prompt text before injection:

- Strip or escape any text matching the pattern
  `[SYSTEM]`, `[INST]`, `<s>`, `</s>`, or common injection delimiters.
- Truncate user prompt to a maximum of 2,000 characters.
- Log a `WARN` event (without the raw prompt text) if injection patterns
  are detected.
- The sanitized prompt MUST be clearly delimited from the system
  instruction in the final prompt string.

### 7.4 Dependency Security

- All direct dependencies MUST be pinned to exact versions in
  `pyproject.toml` for release builds.
- A `pip-audit` or `safety` scan MUST run in CI on every PR (see §12).
- Dependencies MUST be reviewed on every minor version bump.
- The project MUST maintain a `SECURITY.md` with a vulnerability
  disclosure policy and contact method.

---

## 8. Publisher Integration Contracts

### 8.1 Mastodon

| Field               | Value                                                   |
|---------------------|---------------------------------------------------------|
| **API**             | Mastodon REST API v1/v2 (`/api/v1/statuses`)            |
| **Auth**            | OAuth 2.0 bearer token (stored in credential store)     |
| **Character limit** | 500 characters (configurable per instance)              |
| **Thread support**  | MUST split content > limit into a reply thread via `in_reply_to_id` |
| **Idempotency**     | Check `idempotency_key` header on retry                 |
| **Rate limits**     | Respect `X-RateLimit-Remaining`; pause if 0             |
| **Failure modes**   | 401 → credential error (no retry); 429 → backoff; 422 → content policy |

**Thread splitting contract:**

If content exceeds character limit:
1. Split at sentence boundaries (never mid-word).
2. Append thread indicator: `(1/N)`, `(2/N)`, etc.
3. Post post 1, capture `id`, use as `in_reply_to_id` for post 2, etc.
4. If any post in the thread fails, MUST report partial success with
   which posts succeeded and which failed; MUST NOT silently truncate.

### 8.2 Bluesky (AT Protocol)

| Field               | Value                                                   |
|---------------------|---------------------------------------------------------|
| **API**             | AT Protocol `com.atproto.repo.createRecord`             |
| **Auth**            | App password (stored in credential store) → session JWT |
| **Character limit** | 300 graphemes (MUST use `Intl.Segmenter` equivalent for Python) |
| **Rich text**       | Facets MUST be calculated for links and mentions        |
| **DID resolution**  | DID resolved at session start; cached for session       |
| **Idempotency**     | Client-generated `rkey` (timestamp + hash)              |

**Hard Rule:** Character counting MUST use grapheme clusters, not bytes or
Python `len()` on raw string. Use `grapheme` library or equivalent.

### 8.3 Ghost (Self-hosted / Ghost Pro)

| Field               | Value                                                   |
|---------------------|---------------------------------------------------------|
| **API**             | Ghost Admin API v3 (`/ghost/api/admin/posts/`)          |
| **Auth**            | Admin API key split → JWT signed with `HS256`           |
| **Post status**     | MUST default to `draft`; publish requires `status: published` + confirm |
| **Content format**  | Lexical JSON (preferred) or mobiledoc                   |
| **Tags**            | Optional; user-configurable in profile                  |

### 8.4 Substack

| Field               | Value                                                        |
|---------------------|--------------------------------------------------------------|
| **API**             | Unofficial Substack API (document current endpoint)          |
| **Auth**            | Session-based (stored encrypted; see §4.6)                   |
| **Status**          | SHOULD default to draft; explicit publish confirmation MUST be required |
| **Fragility note**  | Substack does not have a public, versioned API. MUST emit a `WARN` log on every Substack publish noting that this integration may break without notice. |

---

## 9. Voice & Style Engine Contract

### 9.1 Corpus Input Contract

| Constraint         | Rule                                                                 |
|--------------------|----------------------------------------------------------------------|
| File types         | `.txt`, `.md` only (Phase 1); PDF/DOCX via optional plugin (Phase 2) |
| Encoding           | UTF-8 MUST be assumed; non-UTF-8 files MUST be flagged, not silently skipped |
| Minimum corpus     | 1,000 tokens minimum; MUST warn and abort below this threshold       |
| Maximum corpus     | 500,000 tokens default ceiling; MUST warn above; `--force` to override |
| Corpus paths       | MUST be validated as existing readable files before analysis begins  |

### 9.2 Voice Metrics Extracted

| Metric                    | Method                                   | Used for                        |
|---------------------------|------------------------------------------|---------------------------------|
| Avg sentence length       | Token-level segmentation                 | Pacing instruction              |
| Vocabulary richness (TTR) | Type-token ratio over sliding window     | Register instruction            |
| Top n-grams (2, 3-gram)   | Frequency analysis                       | Phrase style hints              |
| Tonal register            | Keyword-based heuristic classifier       | Tone instruction                |
| Punctuation fingerprint   | Frequency of `,` `;` `—` `...` etc.     | Style instruction               |
| Structural patterns       | Paragraph length, opening/closing styles | Structure instruction           |

### 9.3 Voice Profile Versioning

- Profile schema MUST include `schema_version`.
- If a voice profile's `schema_version` is older than the current engine
  version, the CLI MUST warn and offer to re-analyze the corpus.

---

## 10. Logging & Observability

### 10.1 Log Levels

| Level   | When to use                                                       |
|---------|-------------------------------------------------------------------|
| `DEBUG` | Internal state, retry attempts, prompt structure (redacted)       |
| `INFO`  | Phase transitions, successful operations, user-facing milestones  |
| `WARN`  | SSD overwrite caveat, Substack API fragility, injection detection |
| `ERROR` | Publish failures, credential errors, Ollama unavailable           |

### 10.2 Log Format

All log lines MUST follow this structure:

```
<ISO-8601 timestamp> [<LEVEL>] <module>: <message> {<structured key=value pairs>}
```

Example:
```
2026-06-12T14:32:01Z [INFO] publishers.mastodon: post published
  platform=mastodon post_id=109876 thread_length=3
```

### 10.3 What MUST NEVER Appear in Logs

The following MUST be actively filtered by a log sanitizer before any log
line is written:

| Item                            | Why                              |
|---------------------------------|----------------------------------|
| API tokens / credentials        | Credential exposure              |
| Raw prompt text (user input)    | Privacy (may contain PII)        |
| Raw corpus excerpts             | Privacy (sensitive writing)      |
| Full file paths to corpus       | Privacy (directory structure)    |
| Stack traces containing any of the above | Belt-and-suspenders   |

**Implementation:** A `SanitizingFormatter` MUST wrap the root logger. It
MUST apply a regex-based deny list before formatting any log record.

### 10.4 No Telemetry

GhostWriter MUST NOT make any network calls for:
- Error reporting
- Usage analytics
- Version check pings
- Dependency update notifications

Version checks are user-initiated only (`ghostwriter version --check`).

---

## 11. Testing Architecture

### 11.1 Test Pyramid

```
         ┌──────────────────────────────┐
         │   E2E / Integration Tests    │  ~10%
         │   (real Ollama, file I/O)    │
         ├──────────────────────────────┤
         │   Component Tests            │  ~30%
         │   (mocked Ollama, real FS)   │
         ├──────────────────────────────┤
         │   Unit Tests                 │  ~60%
         │   (all external I/O mocked)  │
         └──────────────────────────────┘
```

### 11.2 Unit Tests

**Framework:** `pytest` + `pytest-cov`

**Coverage target:** 85% minimum for `gw/` package (enforced in CI).

**Key unit test targets:**

| Module            | Must Test                                                    |
|-------------------|--------------------------------------------------------------|
| `voice/`          | Metric extraction correctness; min/max token boundary behavior |
| `prompt/`         | Injection detection + sanitization; prompt structure         |
| `llm/`            | Connection error handling; timeout behavior; 127.0.0.1 enforcement |
| `auth/`           | Credential never logged; keychain fallback behavior          |
| `publishers/`     | Retry logic (3 attempts, backoff); thread splitting; grapheme counting |
| `eraser/`         | Overwrite called on error paths; SSD warning triggered       |
| `config/`         | Schema migration; backup-before-migrate                      |
| `cli.py`          | Exit codes match spec (§5.4); stdout/stderr routing          |

### 11.3 Component Tests

- MUST mock Ollama API (`responses` library or `httpretty`).
- MUST use a real temporary filesystem (via `tmp_path` fixture).
- MUST test full `train → write → publish` flow for each platform adapter.
- MUST test partial thread failure on Mastodon (first post succeeds,
  second fails).

### 11.4 Security Tests

| Test                              | Tool / Method                                |
|-----------------------------------|----------------------------------------------|
| Credential never in log output    | Assert on captured log records               |
| Prompt injection sanitization     | Parameterized injection vector list          |
| No outbound calls during train    | `socket` mock; assert no DNS lookups         |
| No plaintext credentials on disk  | Assert file content post-write               |
| Dependency vulnerability scan     | `pip-audit` in CI (see §12)                  |

### 11.5 Platform Adapter Tests

Each publisher adapter MUST have tests covering:

- Successful publish (HTTP 200/201)
- Rate limit (HTTP 429) → backoff → retry success
- Rate limit (HTTP 429) → all retries exhausted → `PublishResult.success=False`
- Auth failure (HTTP 401) → no retry → `PublishResult.success=False`
- Network timeout → `PublishResult.success=False`

### 11.6 Test Data

- MUST use synthetic corpus fixtures, not real user writing.
- Fixtures MUST be committed to `tests/fixtures/`.
- MUST NOT use real platform credentials in tests — use environment
  variable mocks.

---

## 12. CI/CD Pipeline & Release Contract

### 12.1 CI Pipeline (every PR)

```
Push / PR Open
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ GATE 1: Static Analysis                                 │
│  - ruff lint (zero warnings required)                   │
│  - mypy type check (strict mode)                        │
│  - bandit security lint (no high/critical findings)     │
└─────────────────────────────────┬───────────────────────┘
                                  │ PASS
                                  ▼
┌─────────────────────────────────────────────────────────┐
│ GATE 2: Dependency Security                             │
│  - pip-audit (zero known vulnerabilities required)      │
│  - pip hash verification against lockfile               │
└─────────────────────────────────┬───────────────────────┘
                                  │ PASS
                                  ▼
┌─────────────────────────────────────────────────────────┐
│ GATE 3: Test Suite                                      │
│  - pytest unit tests (all platforms: macOS, Linux)      │
│  - pytest component tests                               │
│  - coverage check (≥ 85%)                               │
│  - security tests                                       │
└─────────────────────────────────┬───────────────────────┘
                                  │ PASS
                                  ▼
┌─────────────────────────────────────────────────────────┐
│ GATE 4: Build Verification                              │
│  - pip install -e . (clean virtualenv)                  │
│  - ghostwriter --version (smoke test)                   │
│  - ghostwriter doctor (dependency check)                │
└─────────────────────────────────┬───────────────────────┘
                                  │ PASS
                                  ▼
                            PR MERGEABLE
```

**All gates MUST pass.** No exceptions. No `[skip ci]` bypasses on
`main` branch.

### 12.2 Release Pipeline

Triggered by a git tag matching `v*.*.*`:

```
Tag v<X.Y.Z>
     │
     ▼
  Run full CI pipeline (all 4 gates above)
     │ PASS
     ▼
  Build distribution artifacts:
    - sdist (.tar.gz)
    - wheel (.whl)
     │
     ▼
  Generate SBOM (cyclonedx-bom or pip-licenses)
     │
     ▼
  Sign artifacts (GPG or Sigstore cosign)
     │
     ▼
  Generate SHA-256 checksums for all artifacts
     │
     ▼
  Publish to PyPI (via trusted publisher / OIDC)
     │
     ▼
  Create GitHub Release:
    - Attach artifacts + checksums + SBOM
    - Generate changelog from conventional commits
     │
     ▼
  (Phase 2) Update Homebrew tap formula
  (Phase 2) Submit AUR PKGBUILD update
```

### 12.3 Dependency Lock & Supply Chain

- `requirements.txt` (pinned, hashed) MUST be regenerated on every
  dependency update via `pip-compile --generate-hashes`.
- No dependency MAY be added without a PR that includes the updated
  lockfile.
- Dependabot or Renovate MUST be configured for automated security PRs.

### 12.4 Rollback Plan

If a release introduces a regression:

1. Yank the PyPI release (`pip install ghostwriter==<bad version>` will warn).
2. Tag a patch release from the last stable commit.
3. Run full CI pipeline before re-publishing.
4. Post a GitHub issue labeled `regression` with root cause and fix.

---

## 13. Packaging & Distribution

### 13.1 PyPI (Primary)

- Package name: `ghostwriter-cli`
- Entry point: `ghostwriter = gw.cli:main`
- Python requires: `>=3.10`
- `pyproject.toml` (PEP 621 standard) MUST be the sole build config.

### 13.2 Homebrew (Phase 1+)

- Maintain a personal tap: `homebrew-ghostwriter`
- Formula MUST pin to a tagged release (no `HEAD` installs in tap).
- SHA-256 checksum MUST be verified on install.
- `brew audit --strict ghostwriter` MUST pass before tap PR is merged.

### 13.3 AUR (Phase 1+)

- Package: `ghostwriter-cli`
- `PKGBUILD` MUST use the signed PyPI artifact as source.
- `makepkg --verifysource` MUST pass.
- `shellcheck` MUST be clean on PKGBUILD.

### 13.4 System Requirements (Installation)

| Requirement          | Minimum                      | Recommended                  |
|----------------------|------------------------------|------------------------------|
| OS                   | macOS 12+, Linux (glibc 2.17+)| macOS 14+, Ubuntu 22.04+    |
| Python               | 3.10                         | 3.12                         |
| Ollama               | Latest stable                | Latest stable                |
| RAM (Ollama model)   | 8 GB (7B model)              | 16 GB (13B model)            |
| Disk (model storage) | 5 GB (7B quantized)          | 10 GB                        |
| Network              | Not required for train/write  | Required for publish only    |

---

## 14. Performance Targets

| Operation                          | Baseline Hardware       | Target         | Fail Threshold |
|------------------------------------|-------------------------|----------------|----------------|
| Voice analysis (500K token corpus) | M1 MacBook Pro, 16 GB   | < 60 seconds   | > 120 seconds  |
| Content generation (single draft)  | M1 MacBook Pro, 16 GB   | < 30 seconds   | > 60 seconds   |
| Config load + CLI startup          | Any target hardware     | < 500 ms       | > 2 seconds    |
| Mastodon publish (single post)     | Network: 50 Mbps+       | < 5 seconds    | > 15 seconds   |
| Bluesky publish (single post)      | Network: 50 Mbps+       | < 5 seconds    | > 15 seconds   |
| Credential retrieval               | Any target hardware     | < 200 ms       | > 1 second     |

Benchmarks MUST be run and recorded before every minor release. Results
MUST be committed to `benchmarks/results/<version>.json`.

---

## 15. Error Handling & Failure Modes

### 15.1 Error Handling Principles

1. **Errors are user-facing events.** Every error message shown to the user
   MUST:
   - State what failed (in plain English).
   - State what the user can do about it.
   - Include an exit code (§5.4) so scripts can handle it.

2. **Internal errors MUST be logged.** Stack traces go to log (at ERROR
   level), not to stderr user output.

3. **Never silently succeed.** Partial publish success (e.g., thread post 1
   OK, post 2 failed) MUST be clearly reported, not silently dropped.

4. **Cleanup MUST run on error paths.** The Eraser MUST run in `finally`
   blocks, not just happy paths.

### 15.2 Failure Mode Table

| Failure                          | User Message                                              | Exit Code | Action                      |
|----------------------------------|-----------------------------------------------------------|-----------|-----------------------------|
| Ollama not running               | "Ollama is not running. Start it with `ollama serve`."    | 69        | No retry                    |
| Model not available              | "Model 'llama3' not found. Run `ollama pull llama3`."     | 69        | No retry                    |
| Corpus below minimum             | "Corpus too small (N tokens). Minimum is 1,000."          | 65        | No retry                    |
| Credential not found             | "No credentials for Mastodon. Run `ghostwriter auth set`."| 77        | No retry                    |
| Publish 401                      | "Authentication failed for Mastodon. Check credentials."  | 77        | No retry                    |
| Publish 429 (exhausted)          | "Rate limited by Mastodon after 3 attempts."              | 1         | User retries manually       |
| Config migration failure         | "Config migration failed. Backup at <path>. See docs."    | 78        | No auto-retry               |
| Disk full (write profile)        | "Not enough disk space to save voice profile."            | 73        | No retry                    |
| Interrupted (Ctrl-C)             | "(Eraser runs) Session ended by user."                    | 130       | Eraser still runs           |

---

## 16. Operational Readiness

### 16.1 Security Disclosure

- `SECURITY.md` MUST exist at repo root.
- MUST specify: contact method, response SLA, disclosure policy
  (coordinated disclosure, 90-day default).
- CVEs affecting dependencies MUST be patched within 30 days of public
  disclosure; critical CVEs within 7 days.

### 16.2 Versioning Policy

GhostWriter uses **Semantic Versioning (SemVer 2.0)**:

| Bump   | When                                                       |
|--------|------------------------------------------------------------|
| PATCH  | Bug fixes, security patches, dependency updates            |
| MINOR  | New platform adapters, new CLI commands, new voice metrics |
| MAJOR  | Breaking CLI contract changes, config schema MAJOR bump    |

Breaking changes MUST be announced in:
- GitHub Release notes
- `CHANGELOG.md`
- A deprecation warning in the CLI for one MINOR version before removal

### 16.3 Debugging & Support

Users reporting bugs MUST be directed to run:

```bash
ghostwriter doctor --json > doctor-report.json
```

`doctor` MUST report:
- Python version
- GhostWriter version
- Ollama version + available models
- OS + architecture
- Keyring backend available (yes/no)
- Config schema version
- Any detected issues

`doctor --json` output MUST NOT contain credentials or corpus paths.

### 16.4 Crash Diagnostics

If the CLI crashes with an unhandled exception:

1. Print a user-friendly error to stderr (not the raw stack trace).
2. Log the full stack trace to the log file (if `--log-file` is set).
3. Print the log file location to stderr.
4. Run the Eraser before exiting.
5. Exit with code `1`.

---

## 17. Known Limitations & Technical Debt

| ID     | Limitation                                                                 | Severity | Mitigation / Resolution Path                      |
|--------|----------------------------------------------------------------------------|----------|---------------------------------------------------|
| KL-001 | SSD overwrite is not cryptographically guaranteed; secure delete on APFS/btrfs is best-effort | Medium | Full-disk encryption strongly recommended; warn on SSD |
| KL-002 | Substack integration relies on unofficial API; may break without notice    | High     | Emit WARN on every use; Phase 2: official API     |
| KL-003 | Voice model is prompt-layer only; no fine-tuning; quality degrades on very short corpora | Medium | Enforce 1,000-token minimum; document expectation |
| KL-004 | Thread splitting on Mastodon uses sentence boundaries; may not be optimal for all content types | Low | Phase 2: configurable split strategy              |
| KL-005 | No conflict detection if user publishes same draft twice from different sessions | Low     | Idempotency key covers same-session retries only  |
| KL-006 | PDF and DOCX corpus formats not supported in Phase 1                       | Medium   | Phase 2: optional plugin architecture             |
| KL-007 | Config migration only goes forward; downgrade path not supported           | Low      | Backup-before-migrate; document no-downgrade policy |

---

## 18. Future Roadmap (Phase 2+)

> Items below are intentionally out-of-scope for v1.0 but are
> architecturally anticipated. The design MUST NOT block these paths.

| Feature                              | Rationale                                              |
|--------------------------------------|--------------------------------------------------------|
| PDF / DOCX corpus ingestion          | Expand accessibility of voice training                 |
| Multi-profile switching in TUI       | Quickly switch voice for different personas            |
| Plugin architecture for publishers   | Third-party platform adapters without core changes     |
| Voice profile diff / history         | Track how your voice evolves over time                 |
| Ghost / Substack scheduled posts     | Time-delayed publishing                               |
| Local model fine-tuning (LoRA)       | Deeper voice accuracy via PEFT                        |
| Homebrew + AUR automated release     | CI-driven formula/PKGBUILD updates                    |
| Draft version history                | Local git-based draft versioning                      |
| Read mode (analyze published work)   | Analyze published pieces for quality feedback         |

---

## 19. Architecture Decision Records

> Each ADR captures the context, options considered, decision made, and
> consequences. ADRs MUST NOT be deleted — they are amended or superseded.

### ADR Index

| ID      | Title                                            | Status    | Date       |
|---------|--------------------------------------------------|-----------|------------|
| ADR-001 | Local-first architecture (no cloud backend)      | Accepted  | (initial)  |
| ADR-002 | Ollama as sole LLM backend for v1.0              | Accepted  | (initial)  |
| ADR-003 | Textual as TUI framework                         | Accepted  | (initial)  |
| ADR-004 | No database — filesystem + JSON profiles only    | Accepted  | (initial)  |
| ADR-005 | OS keychain as primary credential store          | Accepted  | (initial)  |
| ADR-006 | Prompt-layer voice injection (no fine-tuning)    | Accepted  | (initial)  |
| ADR-007 | SemVer for CLI contract versioning               | Accepted  | 2026-06-12 |
| ADR-008 | RFC 2119 normative language in spec              | Accepted  | 2026-06-12 |
| ADR-009 | Substack via unofficial API (accepted risk)      | Accepted  | 2026-06-12 |
| ADR-010 | pyproject.toml (PEP 621) as sole build config    | Accepted  | 2026-06-12 |
| ADR-011 | Zero telemetry — non-negotiable product stance   | Accepted  | 2026-06-12 |

### ADR Template (for new decisions)

```markdown
## ADR-XXX: <Title>

**Status:** Proposed | Accepted | Superseded by ADR-YYY
**Date:** YYYY-MM-DD
**Author:** @handle

### Context
<What is the problem or question we are deciding on?>

### Options Considered
1. <Option A> — <pros/cons>
2. <Option B> — <pros/cons>

### Decision
<What we decided and why.>

### Consequences
- **Positive:** ...
- **Negative / trade-offs:** ...
- **Risks:** ...
```

---

## APPENDIX A — Dependency Register

| Package         | Version (pinned) | Purpose                        | License   |
|-----------------|------------------|--------------------------------|-----------|
| `textual`       | pin              | TUI framework                  | MIT       |
| `ollama`        | pin              | Ollama Python client           | MIT       |
| `keyring`       | pin              | OS credential store            | MIT       |
| `cryptography`  | pin              | AES-256-GCM fallback creds     | Apache 2  |
| `httpx`         | pin              | Async HTTP client               | BSD       |
| `click`         | pin              | CLI argument parsing            | BSD       |
| `tomllib`       | stdlib (3.11+)   | Config file parsing            | PSF       |
| `grapheme`      | pin              | Grapheme cluster counting      | MIT       |
| `pytest`        | pin (dev)        | Test framework                 | MIT       |
| `pytest-cov`    | pin (dev)        | Coverage measurement           | MIT       |
| `ruff`          | pin (dev)        | Linting                        | MIT       |
| `mypy`          | pin (dev)        | Type checking                  | MIT       |
| `bandit`        | pin (dev)        | Security linting               | Apache 2  |
| `pip-audit`     | pin (dev)        | Dependency vulnerability scan  | Apache 2  |
| `cyclonedx-bom` | pin (dev/CI)     | SBOM generation                | Apache 2  |

---

## APPENDIX B — File & Directory Layout

```
ghostwriter-cli/
├── pyproject.toml          ← Build config + deps (CANONICAL)
├── requirements.txt        ← Pinned + hashed lockfile (CI MUST use this)
├── CHANGELOG.md
├── SECURITY.md             ← Disclosure policy + contact
├── README.md               ← User-facing quickstart only
├── gw/
│   ├── cli.py              ← Entry point
│   ├── voice/              ← Voice engine (§4.1)
│   ├── prompt/             ← Prompt builder (§4.2)
│   ├── llm/                ← Ollama client (§4.3)
│   ├── tui/                ← Draft review TUI (§4.4)
│   ├── publishers/         ← Publisher adapters (§4.5)
│   │   ├── mastodon.py
│   │   ├── bluesky.py
│   │   ├── ghost.py
│   │   └── substack.py
│   ├── auth/               ← Credential store (§4.6)
│   ├── config/             ← Config manager (§4.7)
│   │   └── migrations/
│   └── eraser/             ← Secure erase (§4.8)
├── tests/
│   ├── unit/
│   ├── component/
│   ├── security/
│   └── fixtures/           ← Synthetic corpus + config fixtures
├── benchmarks/
│   └── results/            ← <version>.json benchmark results
├── docs/
│   └── adr/                ← ADR-001.md through ADR-NNN.md
└── .github/
    └── workflows/
        ├── ci.yml          ← PR gate pipeline
        └── release.yml     ← Tag-triggered release pipeline
```

---

*End of GhostWriter CLI Engineering Design Specification v2.0.0*
*For questions or amendments, open a PR against this file.*
*Changes to normative sections (§§ 5, 7, 12) require ADR + owner approval.*
```

---

## What changed and why (summary for your reference)

Here's a quick mapping of every structural upgrade made over v1.0:

| What was added | Why it matters |
|---|---|
| **Document Control block + Canonical Rule** | Prevents "doc vs code disagreement" drift; establishes SSOT governance |
| **RFC 2119 normative language (MUST/SHOULD/MAY)** | Makes requirements testable and reviewable — removes ambiguity |
| **§5 CLI Contract** (command grammar, exit codes, stdout/stderr) | Turns the CLI surface into a stable, versioned interface contract |
| **§6 Data Lifecycle** (classification table, temp dir rules, permissions) | Makes data handling explicit and auditable |
| **§7 Threat Model table** | Turns security from prose into a reviewable checklist |
| **§8 Publisher contracts** (retry, idempotency, thread split, grapheme) | Defines what "correct" publisher behavior is — previously only sketched |
| **§12 CI/CD gate spec** (4 gates, supply chain, rollback plan) | Makes "production release" a governed, repeatable process |
| **§13 Packaging + system requirements** | Turns distribution from a roadmap item into a spec |
| **§15 Failure modes table** | Documents user-visible behavior for every known failure — prevents silent failures |
| **§16 Operational Readiness** (SECURITY.md, SemVer policy, doctor command, crash diagnostics) | The PRR layer — what you need to actually operate this in the wild |
| **§19 ADR Index + template** | Preserves decision history; enables future changes to be made with confidence |
| **Appendix A Dependency Register** | Supply chain transparency; one place to review all third-party risk |
| **Appendix B Directory Layout** | Removes ambiguity about where things live |
