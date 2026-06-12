"""Example migration module retained for schema migration contract tests."""

from __future__ import annotations


def migrate(old_text: str) -> str:
    """Upgrade a hypothetical 0.9 config to 1.0.

    Real deployments should add concrete transforms for each schema bump.
    """
    if 'schema_version = "0.9"' in old_text:
        return old_text.replace('schema_version = "0.9"', 'schema_version = "1.0"')
    return old_text
