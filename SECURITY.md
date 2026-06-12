# Security Policy

GhostWriter CLI handles private writing, generated drafts, and publishing credentials. Security and privacy issues are treated as release blockers.

## Supported versions

| Version | Supported |
|---|---|
| `1.x` | Yes |

## Reporting a vulnerability

Please do **not** open a public GitHub issue for exploitable vulnerabilities.

Preferred reporting path:

1. Open a private GitHub Security Advisory for the repository.
2. If private advisories are unavailable, contact the repository owner privately and include `GhostWriter CLI Security` in the subject.

Include, if possible:

- affected version or commit
- operating system
- reproduction steps
- impact assessment
- whether credentials/corpus data can be exposed
- suggested mitigation or patch

Do not include real user credentials or private corpus text in reports. Use synthetic data.

## Response SLA

| Event | Target |
|---|---:|
| Initial acknowledgement | 7 days |
| Critical confirmed vulnerability patch | 7 days |
| High severity confirmed vulnerability patch | 14 days |
| Dependency CVE patch | 30 days |
| Coordinated disclosure window | 90 days default |

## Security invariants

These rules are non-negotiable:

1. No plaintext credentials on disk.
2. No corpus content in network payloads.
3. No telemetry, analytics, crash beacons, or automatic update pings.
4. No publishing without explicit human confirmation.
5. No credentials, raw prompts, corpus excerpts, or full private corpus paths in logs.
6. Remote Ollama must remain opt-in and warning-backed.
7. Publisher adapters must report partial failure rather than silently succeeding.

## Known security caveats

### Secure deletion

GhostWriter performs best-effort overwrite and unlink for ephemeral files. SSDs and copy-on-write filesystems may retain old blocks. Full-disk encryption is strongly recommended.

### Substack integration

Substack does not provide a stable public publishing API. The integration uses unofficial behavior and may break without notice. It should be treated as higher operational risk.

### Local model trust

Ollama is trusted only when bound to loopback. If you opt into remote Ollama, prompts and style instructions may leave the machine.

## Dependency security

Maintainers should run:

```bash
pip-audit --strict
bandit -q -r gw -c pyproject.toml
```

Dependency updates must include an updated hashed `requirements.txt` and full test run.
