# Privacy and Security

GhostWriter's security model is local-first, explicit-network, and no-telemetry.

## Data classification

| Data | Classification | Location | Persists |
|---|---|---|---|
| Corpus text | Private/sensitive | User-selected paths | User-managed |
| Voice profile | Private metrics | `~/.config/ghostwriter/profiles/` | Yes |
| Config | User preferences | `~/.config/ghostwriter/config.toml` | Yes |
| Credentials | Secret | OS keychain or `credentials.enc` | Yes |
| Session temp files | Ephemeral | `/tmp/gw-session-*` | No |
| Staged draft | Private/user content | `drafts/staged.json` | Until successful publish |
| Logs | Operational | stderr or user-selected file | Optional |

## Corpus privacy

During `train`:

- GhostWriter reads `.txt` and `.md` files in place.
- It does not copy corpus files.
- It does not send corpus text over the network.
- It does not write raw corpus excerpts to the profile.

Voice profiles contain metrics and hashed n-grams only.

## Ollama boundary

Default generation endpoint:

```text
http://127.0.0.1:11434
```

Remote hosts are blocked unless `--allow-remote-ollama` is passed. If enabled, prompts and style instructions may leave the machine; use only with trusted infrastructure.

## Credential storage

Primary:

- OS keychain through `keyring`

Fallback:

- encrypted file at `~/.config/ghostwriter/credentials.enc`
- AES-256-GCM
- PBKDF2-HMAC-SHA256
- 390,000 iterations
- passphrase prompted locally

GhostWriter warns before first-time fallback creation when OS keychain is unavailable.

## Logging protections

The root logger uses a sanitizing formatter that redacts:

- bearer tokens
- API keys
- passwords
- secrets
- cookies
- authorization headers
- sensitive filesystem paths

Do not intentionally log raw prompts, corpus text, or credentials.

## Network policy

Expected network calls:

| Command | Network behavior |
|---|---|
| `train` | none |
| `write` | local Ollama only by default |
| `auth set/test/revoke` | no platform validation network in current implementation |
| `publish` | selected platform APIs only |
| `doctor` | local Ollama tags endpoint |
| `version` | no network |

No automatic telemetry, analytics, crash reporting, update checking, or beaconing is implemented.

## Secure deletion caveat

The eraser overwrites files with random bytes and calls `fsync` before unlinking. This is best effort.

On SSDs and copy-on-write filesystems such as APFS, btrfs, ZFS, or overlay filesystems, physical block overwrite is not guaranteed. Use full-disk encryption for stronger protection.

## Human publish gate

Publishing requires:

1. approved draft state from review UI
2. per-platform final confirmation prompt
3. credentials for the platform

`--yes` does not auto-confirm publishing.

## Security reporting

See [`../SECURITY.md`](../SECURITY.md).
