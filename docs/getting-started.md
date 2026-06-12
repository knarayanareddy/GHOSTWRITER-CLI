# Getting Started

This guide takes you from a clean machine to a successful local GhostWriter run.

## 1. Install prerequisites

### Python

GhostWriter requires Python 3.10 or newer.

```bash
python --version
```

### Ollama

Install Ollama from the official distribution for your operating system, then start it and pull a model:

```bash
ollama serve
ollama pull llama3
```

Verify Ollama is reachable locally:

```bash
curl http://127.0.0.1:11434/api/tags
```

## 2. Install GhostWriter

From the repository root:

```bash
python -m pip install .
ghostwriter --version
```

For development:

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pip install -e ".[dev]"
```

## 3. Run diagnostics

```bash
ghostwriter doctor
```

Machine-readable version:

```bash
ghostwriter doctor --json > doctor-report.json
```

The doctor report does not include credentials or corpus paths.

## 4. Train with the synthetic fixture

This is a safe smoke test that does not use private writing:

```bash
export GHOSTWRITER_CONFIG_DIR="$(mktemp -d)"
ghostwriter train --corpus tests/fixtures/synthetic_corpus.md --min-tokens 10
```

Expected output includes a JSON object with `profile_path`, `schema_version`, and `token_count`.

## 5. Train with your own corpus

```bash
ghostwriter train --corpus ~/writing-samples
```

Use only UTF-8 `.txt` and `.md` files. GhostWriter reads files in place and does not copy the corpus.

## 6. Generate a draft

```bash
ghostwriter write --prompt "Write a reflective post about maintaining creative focus"
```

GhostWriter will call local Ollama, show a review UI, and stage the draft only if you approve it.

## 7. Configure a publisher

Example for Mastodon:

```bash
ghostwriter auth set mastodon
```

Then publish:

```bash
ghostwriter publish --platform mastodon
```

Publishing always prompts for final confirmation. Default is `No`.

## Next steps

- Read the full [Usage Guide](usage.md).
- Configure your profile in [Configuration](configuration.md).
- Set up platforms in [Publisher Setup](publisher-setup.md).
