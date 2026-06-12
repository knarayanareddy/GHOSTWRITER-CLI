# Support

## Before asking for help

Run:

```bash
ghostwriter doctor --json > doctor-report.json
```

The report is designed to avoid credentials and corpus paths. Review it for obvious issues before sharing.

## Where to get help

- Usage questions: open a GitHub Discussion or issue.
- Bugs: open a GitHub issue using the bug template.
- Feature requests: open a feature request issue.
- Security vulnerabilities: follow [`SECURITY.md`](SECURITY.md), do not open a public issue.

## What to include in bug reports

- GhostWriter version
- Python version
- OS and architecture
- command run
- expected behavior
- actual behavior
- sanitized logs if available
- `doctor --json` output if relevant

Never include:

- API tokens
- app passwords
- session cookies
- private corpus text
- unreleased/private drafts
