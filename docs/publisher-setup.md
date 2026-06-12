# Publisher Setup

GhostWriter can publish approved drafts to Mastodon, Bluesky, Ghost, and Substack. Publishing always requires final confirmation.

## General workflow

```bash
ghostwriter auth set <platform>
ghostwriter auth test <platform>
ghostwriter publish --platform <platform>
```

Credentials are stored in the OS keychain when available, or in an encrypted file fallback.

## Mastodon

Command:

```bash
ghostwriter auth set mastodon
```

Prompts:

- Mastodon instance URL, e.g. `https://mastodon.social`
- OAuth access token

Behavior:

- Posts to `/api/v1/statuses`.
- Splits content above the configured character limit into reply threads.
- Uses a unique idempotency key per thread chunk.
- Retries transient errors: `429`, `502`, `503`.
- Does not retry permanent errors: `401`, `403`, `404`, `422`.

## Bluesky

Command:

```bash
ghostwriter auth set bluesky
```

Prompts:

- Bluesky handle
- Bluesky app password

Behavior:

- Creates an AT Protocol session.
- Enforces 300 grapheme limit.
- Adds rich-text facets for links.
- Resolves `@handle.example` mentions to DID when possible and adds mention facets.
- Uses a client-generated `rkey`.

Notes:

- Use an app password rather than your account password.
- Mentions that cannot be resolved are left as plain text.

## Ghost

Command:

```bash
ghostwriter auth set ghost
```

Prompts:

- Ghost Admin API base URL
- Ghost Admin API key in `id:secret` format
- status: normally `draft` or `published`

Behavior:

- Defaults are draft-oriented.
- If you choose `published`, GhostWriter asks whether stored credentials are allowed to create live published posts.
- Even with `confirmed_publish = "true"`, publish still requires the normal final confirmation prompt.

Recommended setup:

```text
status = draft
```

Then review/publish in Ghost admin manually if that is your editorial process.

## Substack

Command:

```bash
ghostwriter auth set substack
```

Prompts:

- Substack base URL
- session cookie
- status: normally `draft` or `published`

Behavior:

- Uses an unofficial API endpoint.
- Emits a warning on every publish attempt.
- If you choose `published`, GhostWriter asks whether stored credentials are allowed to create live published posts.
- Final confirmation is still required.

Caveat:

Substack does not provide a stable public publishing API. This integration may break without notice.

## Dry runs

Use global `--dry-run` to validate flow without making publish requests:

```bash
ghostwriter --dry-run publish --platform mastodon
```

Dry runs still require final confirmation prompts because they exercise the publish gate.

## Revoking credentials

```bash
ghostwriter auth revoke mastodon
```

Also revoke tokens/passwords in the platform itself when rotating credentials.
