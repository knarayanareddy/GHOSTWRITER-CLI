# Benchmarking

The design specification defines performance targets for voice analysis, generation, startup, publishing, and credential retrieval.

## Results location

```text
benchmarks/results/<version>.json
```

## Minimum release record

Each minor release should record:

- GhostWriter version
- date/time
- hardware
- OS
- Python version
- corpus token count
- operation timings
- notes about Ollama model

Example schema:

```json
{
  "version": "1.0.1",
  "recorded_at": "2026-06-12T00:00:00Z",
  "hardware": "M1 MacBook Pro, 16 GB",
  "python": "3.12.x",
  "ollama_model": "llama3",
  "results": [
    {"operation": "voice_analysis_500k_tokens", "seconds": 42.1},
    {"operation": "cli_startup", "seconds": 0.22}
  ]
}
```

## Manual timing examples

```bash
time ghostwriter train --corpus ~/large-corpus --force
time ghostwriter doctor --json >/tmp/doctor.json
```

For generation, model and hardware dominate results:

```bash
time ghostwriter write --prompt "Write a 300-word test post"
```

Do not commit private corpus data or generated private drafts with benchmark results.
