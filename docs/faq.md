# FAQ

## Does GhostWriter send my corpus to an AI service?

No. Training reads local files only. Writing uses Ollama on `127.0.0.1` by default.

## Does the voice profile contain my writing?

It should not contain verbatim corpus text. It stores metrics and hashed n-grams.

## Can I use a remote Ollama server?

Yes, only with `--allow-remote-ollama`. This weakens the local-only privacy boundary because prompt/style data may leave your machine.

## Does GhostWriter fine-tune models?

No. It uses prompt-layer voice injection only.

## Can I use PDFs or DOCX files?

Not directly in Phase 1. Convert them to UTF-8 `.txt` or `.md` first.

## Is secure deletion perfect?

No. It is best effort. SSD and copy-on-write filesystems can retain old blocks. Use full-disk encryption for stronger protection.

## Does GhostWriter publish automatically?

No. Publishing requires an approved staged draft and a final confirmation prompt per platform.

## Does `--yes` auto-publish?

No. `--yes` is for non-destructive prompts only and does not bypass publish confirmation.

## Where are credentials stored?

OS keychain if available. Otherwise, `~/.config/ghostwriter/credentials.enc` encrypted with AES-256-GCM and a passphrase-derived key.

## Is Substack officially supported?

Substack support uses an unofficial API and may break without notice. GhostWriter warns on every Substack publish attempt.
