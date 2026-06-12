# Packaging

GhostWriter is packaged primarily as a Python project.

## PyPI

Canonical package metadata is in `pyproject.toml`.

Build locally:

```bash
python -m pip install build
python -m build
```

Expected artifacts:

```text
dist/ghostwriter_cli-<version>.tar.gz
dist/ghostwriter_cli-<version>-py3-none-any.whl
```

## Locked dependencies

`requirements.txt` is generated with hashes and is used by CI for supply-chain verification.

Regenerate after dependency changes:

```bash
pip-compile --generate-hashes --output-file=requirements.txt requirements.in
```

If using direct pyproject input, ensure the generated file includes all runtime dependencies and hashes.

## Homebrew

Template:

```text
packaging/homebrew/ghostwriter-cli.rb
```

Before publishing:

1. Update version URL.
2. Replace `REPLACE_WITH_RELEASE_SDIST_SHA256`.
3. Run Homebrew audit.
4. Submit to the project tap.

## AUR

Template:

```text
packaging/aur/PKGBUILD
```

Before publishing:

1. Update `pkgver`.
2. Replace `sha256sums`.
3. Validate with Arch tooling:

```bash
makepkg --verifysource
makepkg -si
```

## Signing and checksums

Release artifacts should include:

- SHA-256 checksums
- SBOM
- optional GPG/Sigstore signatures

See [Release Process](release.md).
