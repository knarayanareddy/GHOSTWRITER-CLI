# Configuration

GhostWriter stores user configuration in TOML and voice profiles in JSON.

## Config directory

Default:

```text
~/.config/ghostwriter/
```

Override:

```bash
export GHOSTWRITER_CONFIG_DIR=/path/to/config
```

This is useful for tests, demos, or isolated projects.

## Config file

Default path:

```text
~/.config/ghostwriter/config.toml
```

Example:

```toml
[meta]
schema_version = "1.0"
active_profile = "default"

[profile.default]
ollama_model = "llama3"
voice_profile_path = "~/.config/ghostwriter/profiles/default.json"
default_platforms = ["mastodon"]
mastodon_character_limit = 500
ghost_default_status = "draft"
```

## Profiles

A profile combines:

- Ollama model name
- voice profile path
- default publish platforms
- platform preferences

Use:

```bash
ghostwriter profile list
ghostwriter profile switch <name>
ghostwriter profile delete <name>
```

The current code creates a default profile automatically. Additional profile creation can be performed by editing `config.toml` and then training to the matching `voice_profile_path`.

## Voice profiles

Default directory:

```text
~/.config/ghostwriter/profiles/
```

Schema:

```json
{
  "schema_version": "1.0",
  "created_at": "<ISO-8601>",
  "corpus_hash": "<sha256 of sorted file paths + sizes>",
  "metrics": {
    "token_count": 12345,
    "avg_sentence_length": 18.4,
    "vocabulary_richness": 0.72,
    "top_n_grams": [
      {"n": 2, "hash": "...", "count": 10}
    ],
    "tonal_register": "conversational",
    "punctuation_fingerprint": {},
    "structural_patterns": []
  }
}
```

Privacy notes:

- `corpus_hash` is based on file paths and sizes, not contents.
- `top_n_grams` stores hashes, not phrases.
- No source sentence or paragraph is serialized.

## Drafts

```text
~/.config/ghostwriter/drafts/staged.json
```

`staged.json` is the approved draft waiting for publish. It is erased after all attempted publish targets succeed.

Optional saved drafts created with `--save` are kept as markdown files and are user-managed.

## Credentials

Primary backend:

- OS keychain via `keyring`

Fallback:

```text
~/.config/ghostwriter/credentials.enc
```

Fallback encryption:

- AES-256-GCM
- PBKDF2-HMAC-SHA256
- 390,000 iterations
- passphrase prompted locally

The CLI warns when OS keychain is unavailable and a first-time encrypted fallback file will be created.

## Logging

Default: sanitized logs to stderr.

Optional file:

```bash
ghostwriter --log-level debug --log-file ~/ghostwriter.log doctor
```

Logs are sanitized for:

- bearer tokens
- API keys
- passwords/secrets/cookies
- raw prompt text patterns
- sensitive filesystem paths

## Schema migrations

The config manager checks `schema_version` on startup. Migration rules:

- backup old config before migration
- fail with exit code `78` on migration failure
- preserve user data when possible

Migration modules live under:

```text
gw/config/migrations/
```
