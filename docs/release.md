# Release Process

GhostWriter follows Semantic Versioning.

## Version policy

| Bump | Use for |
|---|---|
| Patch | bug fixes, docs, security patches, dependency updates |
| Minor | new commands, publishers, metrics, compatible config additions |
| Major | breaking CLI contract changes or config schema major changes |

## Pre-release checklist

1. Update version in:
   - `gw/__init__.py`
   - `pyproject.toml`
2. Update `CHANGELOG.md`.
3. Add benchmark result file under `benchmarks/results/<version>.json`.
4. Run full gates:

```bash
ruff check gw tests
mypy gw
bandit -q -r gw -c pyproject.toml
pip-audit --strict
pytest --cov=gw --cov-report=term-missing --cov-fail-under=85
```

5. Build artifacts:

```bash
python -m build
```

6. Generate checksums:

```bash
cd dist
sha256sum * > SHA256SUMS.txt
```

7. Generate SBOM:

```bash
cyclonedx-py environment -o dist/sbom.cdx.json
```

## Tag release

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The release workflow runs CI gates, builds artifacts, generates SBOM/checksums, publishes to PyPI, and creates a GitHub Release.

## Packaging updates

After PyPI artifacts exist:

1. Replace placeholder SHA in `packaging/homebrew/ghostwriter-cli.rb`.
2. Replace placeholder SHA in `packaging/aur/PKGBUILD`.
3. Validate templates:

```bash
brew audit --strict ghostwriter-cli
shellcheck packaging/aur/PKGBUILD || true
```

`PKGBUILD` is not a shell script in the usual sense; use Arch packaging tools where possible.

## Rollback

If a release regresses:

1. Yank the PyPI version.
2. Open an issue labeled `regression`.
3. Patch from the last stable commit.
4. Run full CI.
5. Publish a patch release.
6. Document the root cause in release notes.
