# Troubleshooting

## Start with doctor

```bash
ghostwriter doctor --json > doctor-report.json
```

Review `issues` in the report.

## Ollama is not running

Error:

```text
Ollama is not running. Start it with `ollama serve`.
```

Fix:

```bash
ollama serve
ollama pull llama3
```

## Model not found

Error:

```text
Model 'llama3' not found. Run `ollama pull llama3`.
```

Fix:

```bash
ollama pull llama3
```

Or update `ollama_model` in `config.toml`.

## Corpus too small

Error:

```text
Corpus too small (N tokens). Minimum is 1,000.
```

Fix:

- Add more `.txt` / `.md` files.
- Make sure files are UTF-8.
- For experiments only, lower `--min-tokens`.

## Unsupported corpus file type

Phase 1 supports only:

- `.txt`
- `.md`

Convert PDFs/DOCX externally before training.

## Keyring unavailable

GhostWriter will warn and fall back to encrypted file storage if keyring is unavailable.

Fix options:

- Configure your OS keychain/secret service.
- Install platform keyring dependencies.
- Continue with encrypted fallback and a strong passphrase.

## Forgot credential fallback passphrase

GhostWriter cannot recover encrypted credentials without the passphrase.

Fix:

1. Delete `~/.config/ghostwriter/credentials.enc`.
2. Recreate credentials with `ghostwriter auth set <platform>`.
3. Rotate/revoke old platform tokens where applicable.

## Publish failed with 401

Meaning: platform authentication failed.

Fix:

```bash
ghostwriter auth revoke <platform>
ghostwriter auth set <platform>
ghostwriter auth test <platform>
```

Also verify the token/app password in the platform dashboard.

## Publish rate limited

Meaning: platform returned `429`.

GhostWriter retries transient failures with backoff. If exhausted, retry manually later.

## Bluesky links are not clickable

GhostWriter generates facets for `http://` and `https://` URLs. If links are still plain text:

- confirm the text includes a full URL
- check platform API response
- run with `--log-level debug --log-file <path>` and inspect sanitized logs

## Textual UI does not appear

The rich Textual app appears only in an interactive terminal with Textual importable. In non-interactive shells or minimal environments, GhostWriter uses the prompt fallback.

Fix:

```bash
python -m pip install textual==8.2.7
```

Run in a real terminal, not a detached pipeline.

## Staged draft disappeared after publish

This is expected after successful non-dry-run publish to all attempted targets. The staged draft is securely erased. If you want a persistent copy, use:

```bash
ghostwriter write --prompt "..." --save
```
