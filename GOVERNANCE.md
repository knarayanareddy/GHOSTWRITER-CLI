# Governance

GhostWriter CLI is governed by the design specification and ADR process.

## Source of truth

The canonical engineering source of truth is:

```text
GHOSTWRITER-CLIdesigndoc.md
```

If code and spec disagree, update the spec through review before shipping code that intentionally changes the design.

## Maintainer responsibilities

Maintainers are responsible for:

- enforcing security/privacy invariants
- reviewing dependency changes
- requiring tests and docs for behavior changes
- maintaining release artifacts
- triaging vulnerabilities according to `SECURITY.md`

## Decision process

Use ADRs for:

- architecture changes
- new publisher classes
- storage model changes
- security policy changes
- CLI contract breaking changes
- dependency additions with meaningful risk

ADRs live under `docs/adr/` and are never deleted.
