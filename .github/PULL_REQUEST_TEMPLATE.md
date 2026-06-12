## Summary

What changed and why?

## Type of change

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Security/privacy hardening
- [ ] Refactor
- [ ] Release/packaging

## Security/privacy checklist

- [ ] No plaintext credentials are written.
- [ ] No corpus content is sent over the network.
- [ ] No telemetry or automatic network call was added.
- [ ] No raw prompts/corpus/credentials are logged.
- [ ] Publish still requires explicit human confirmation.

## Tests

- [ ] `ruff check gw tests`
- [ ] `mypy gw`
- [ ] `bandit -q -r gw -c pyproject.toml`
- [ ] `pytest --cov=gw --cov-report=term-missing --cov-fail-under=85`

## Docs

- [ ] README/docs updated if user-facing behavior changed.
- [ ] ADR added/updated if architecture changed.
