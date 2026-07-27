# Functional Review — Issue #3 (Round 1, scoped re-run: docs additions)

**Scope:** Uncommitted working-tree additions on `feature/3-recipient-whitelist-env-vars`
- Fail-open warning in `docs/security.md` and `docs/configuration.md`
- `CHANGELOG.md` new `## Unreleased` section
- Rate-limit env var name corrections in `.env.example` and `docs/cli.md`

**Date:** 2026-07-27

## Verdict

**rejected** — one factual inaccuracy in the fail-open warning must be fixed before push.

## Checks performed

### 1. Rate-limit env var names (verified against `src/simple_email_gw/config.py`)

`ServerConfig` (lines 107-135): `env_prefix="EMAIL_"`, `env_nested_delimiter="__"`,
`rate_limits: RateLimitConfig` with `imap_requests_per_minute` and `smtp_sends_per_hour`
(RateLimitConfig, lines 59-65).

Canonical names:
- `EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE`
- `EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR`

Diff uses exactly these names in `.env.example` (lines 14-15) and `docs/cli.md`
(lines 276-277). **PASS.**

### 2. Stale rate-limit name grep

`grep -rn "EMAIL_RATE_LIMIT_REQUESTS_PER_MINUTE\|EMAIL_RATE_LIMIT_SENDS_PER_HOUR"`
returns only the `CHANGELOG.md` line describing what was fixed (intentional).
No stale references in user-facing docs. **PASS.**

### 3. Whitelist env var names

All references use `EMAIL_RECIPIENT_WHITELIST_DOMAINS` / `_ADDRESSES` / `_JSON`,
matching `ServerConfig` fields (lines 138-144). **PASS.**

### 4. CHANGELOG entry

- `## Unreleased` placed above `## 0.3.0 - 2026-06-17` — correct Keep-a-Changelog form.
- "Corrected recipient whitelist env var names in README and docs" — accurate;
  prior commit `508ff0b` corrected README.md, .env.example, docs/cli.md,
  docs/configuration.md, docs/security.md.
- "Corrected rate-limit env var names in `.env.example` and `docs/cli.md`" —
  accurate per this round's diff.
- "Added fail-open warning to recipient whitelist documentation in `docs/security.md`
  and `docs/configuration.md`." — accurate per this round's diff.
- Three Fixed entries, all well-formed. **PASS.**

### 5. Fail-open warning — factual accuracy against code

`get_recipient_whitelist` (config.py lines 169-191):

```python
if self.recipient_whitelist_json:
    data = json.loads(self.recipient_whitelist_json)
    whitelist = RecipientWhitelist(**data)
    whitelist.enabled = True          # <-- forced, overrides JSON
    return whitelist
```

When `EMAIL_RECIPIENT_WHITELIST_JSON` is set, `enabled` is **forced to True
regardless of what the JSON contains**. Verified at runtime:

```
$ EMAIL_RECIPIENT_WHITELIST_JSON='{"enabled": false, "domains": ["example.com"]}' uv run python -c "..."
enabled: True
is_allowed(test@other.com): False
is_allowed(test@example.com): True
```

The warning added to `docs/security.md` (line 119) and `docs/configuration.md`
(line 123) states:

> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) requires `"enabled": true` explicitly.

This is **factually incorrect**. The JSON form does *not* require `"enabled": true`:
the code unconditionally forces `enabled=True` when the JSON env var is set, so
the `enabled` field in the JSON is ignored entirely (the user cannot disable the
whitelist via JSON).

The accurate statement is: "The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`)
enables the whitelist unconditionally when set; the `enabled` field is ignored."
Or, more conservatively for the fail-open warning, simply note that misspelling
the `EMAIL_RECIPIENT_WHITELIST_JSON` env var name leaves the whitelist disabled
(covered by the existing "unset, empty, or misspelled" clause) and drop the
misleading "requires enabled: true" clause.

**FAIL** — must correct the JSON clause in both `docs/security.md` and
`docs/configuration.md`.

### 6. `make check`

`make check` passes: 592 passed, 2 warnings (pre-existing, unrelated). **PASS.**

## Required fix before push

In **both** `docs/security.md` (line 119) and `docs/configuration.md` (line 123),
replace the clause:

> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) requires `"enabled": true` explicitly.

with a factually correct statement, e.g.:

> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) enables the whitelist
> unconditionally when set; the `enabled` field is ignored.

Rationale: the added warning's purpose is to alert users to fail-open risk.
Telling users they must set `"enabled": true` is both wrong (the field is
ignored) and directionally dangerous (a user who sets `"enabled": false`
believing it disables the whitelist will find it silently enabled — the
opposite of the warning's intent).

## Items not in scope (no action)

- README.md whitelist env var names — already correct (corrected in prior
  commit `508ff0b`); no edits this round.
- README has no rate-limit env var names — no change needed.