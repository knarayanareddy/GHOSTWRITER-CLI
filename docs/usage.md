# Usage Guide

This guide explains day-to-day GhostWriter CLI workflows.

## Global command form

```bash
ghostwriter [GLOBAL OPTIONS] <command> [COMMAND OPTIONS]
```

Global options:

| Option | Meaning |
|---|---|
| `--profile <name>` | Use a profile only for this invocation. |
| `--log-level <level>` | `debug`, `info`, `warn`, `warning`, or `error`. |
| `--log-file <path>` | Write sanitized logs to a file. |
| `--no-color` | Disable ANSI color. |
| `--dry-run` | Execute flow without actual publish calls. |
| `--yes` | Auto-confirm non-destructive prompts only. Never auto-publishes. |
| `--version` | Print CLI version. |

## Train

```bash
ghostwriter train --corpus ~/writing-samples
```

Multiple paths:

```bash
ghostwriter train --corpus ~/essays --corpus ~/posts --corpus ~/notes/style.md
```

Options:

| Option | Default | Meaning |
|---|---:|---|
| `--corpus <path>` | required | File or directory. Repeatable. |
| `--output <path>` | active profile path | Custom profile output path. |
| `--min-tokens <n>` | `1000` | Minimum token threshold. |
| `--max-tokens <n>` | `500000` | Maximum token threshold without `--force`. |
| `--force` | false | Analyze above max token ceiling. |

Failure examples:

- too few tokens → exit code `65`
- unsupported file type → exit code `65`
- unreadable file → exit code `65` or `74`

## Write

```bash
ghostwriter write --prompt "Write an essay about patient practice"
```

Options:

| Option | Default | Meaning |
|---|---:|---|
| `--prompt <text>` | required | Topic/instruction. Sanitized and truncated to 2,000 characters. |
| `--timeout <seconds>` | `60` | Ollama generation timeout. |
| `--ollama-base-url <url>` | `http://127.0.0.1:11434` | Ollama endpoint. |
| `--allow-remote-ollama` | false | Permit non-local endpoint after explicit risk acceptance. |
| `--json` | false | Emit machine-readable output. |
| `--save` | false | Save approved draft as markdown in `drafts/`. |

### What happens during write?

1. Load active config/profile.
2. Load voice profile JSON.
3. Convert profile metrics to natural-language instructions.
4. Sanitize user prompt.
5. Call Ollama.
6. Open Textual review UI when available.
7. Stage an approved draft at `~/.config/ghostwriter/drafts/staged.json`.
8. Securely erase temporary prompt/draft session files.

## Publish

```bash
ghostwriter publish --platform mastodon
```

Multiple targets:

```bash
ghostwriter publish --platform mastodon --platform bluesky
```

If `--platform` is omitted, GhostWriter uses the platforms stored on the staged draft or active profile.

Publishing rules:

- The draft must have been approved by the write review flow.
- Every target prompts for final confirmation.
- `--yes` does not bypass publish confirmation.
- After all attempted targets succeed in non-dry-run mode, `staged.json` is securely erased.
- If any target fails or is skipped, `staged.json` remains for retry.

## Auth

```bash
ghostwriter auth set mastodon
ghostwriter auth test mastodon
ghostwriter auth revoke mastodon
```

Credentials are never displayed.

## Profile management

```bash
ghostwriter profile list
ghostwriter profile switch default
ghostwriter profile delete old-profile
```

The default profile cannot be deleted.

## Config

```bash
ghostwriter config show
ghostwriter config reset
```

`config show` does not print credentials.

## Doctor

```bash
ghostwriter doctor
ghostwriter doctor --json
```

Reports:

- Python version
- GhostWriter version
- OS and architecture
- Ollama availability and local models
- keyring availability
- config schema version
- detected issues

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Success |
| `1` | General handled/unhandled error |
| `64` | Usage error |
| `65` | Corpus/data error |
| `69` | Ollama unavailable/model unavailable |
| `73` | Cannot create/write file |
| `74` | I/O error |
| `77` | Credential/permission error |
| `78` | Config error |
| `130` | Interrupted by user |
