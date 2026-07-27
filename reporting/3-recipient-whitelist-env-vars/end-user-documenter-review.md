# End-User Documentation Review — Issue #3

**Branch:** feature/3-recipient-whitelist-env-vars
**Scope:** docs
**Date:** 2026-07-27
**Reviewer:** end-user-documenter agent

## Summary

The fix corrects the recipient-whitelist environment variable names across all
end-user-facing documentation to match the names actually consumed by
`src/simple_email_gw/config.py`:

- `EMAIL_RECIPIENT_DOMAINS` → `EMAIL_RECIPIENT_WHITELIST_DOMAINS`
- `EMAIL_RECIPIENT_ADDRESSES` → `EMAIL_RECIPIENT_WHITELIST_ADDRESSES`

## Verification

### 1. Consistency of corrected env var names

A repo-wide grep for the old names (`EMAIL_RECIPIENT_DOMAINS` /
`EMAIL_RECIPIENT_ADDRESSES`, excluding the `WHITELIST` substring) returns **no
matches**. The stale names have been purged everywhere.

All current occurrences use the corrected names uniformly:

- `README.md` (lines 212-213) — "Recipient Whitelist" section
- `.env.example` (lines 18-19) — commented example
- `docs/cli.md` (lines 280-281) — "Environment File Example" section
- `docs/configuration.md` (lines 102, 108, 116, 143) — "Recipient Whitelist"
  section and the `.env` example
- `docs/security.md` (lines 111-112) — "Recipient Whitelist" security feature

### 2. Match against code

`src/simple_email_gw/config.py` defines the pydantic Settings model with
`env_prefix="EMAIL_"` (line 111) and fields
`recipient_whitelist_domains` (line 139) and `recipient_whitelist_addresses`
(line 142). Pydantic-settings uppercases field names, so the canonical env var
names are `EMAIL_RECIPIENT_WHITELIST_DOMAINS` and
`EMAIL_RECIPIENT_WHITELIST_ADDRESSES` — exactly what the docs now state. The
JSON variant `EMAIL_RECIPIENT_WHITELIST_JSON` (line 116 of configuration.md)
matches `recipient_whitelist_json` (config.py line 138) too.

### 3. .env.example alignment

`.env.example` uses the corrected names with the same values shown in the
README quick example, and the comment header "Recipient Whitelist (optional)"
matches the framing in README and docs.

### 4. Whitelist framing consistency

The "whitelist" terminology is consistent throughout:

- README has a "Recipient Whitelist" subsection (line 207) and a "Recipient
  Whitelist" entry under Security Features (line 230).
- `docs/configuration.md` has a "Recipient Whitelist" section with
  "Domain Whitelist" / "Address Whitelist" subsections.
- `docs/security.md` titles the feature "Recipient Whitelist" (line 104).
- `docs/cli.md` labels the block "Optional: Recipient whitelist".

The env var names now align with this framing (previously the names dropped
the "whitelist" component, which was the source of the user confusion).

### 5. Readability

The corrected examples read naturally. No surrounding prose referenced the old
names, so no sentences needed rewording — only the code-block values changed.
Cross-references to the ReadTheDocs pages remain valid.

## CHANGELOG recommendation

**Warranted.** The project follows Keep a Changelog and the latest released
version (0.3.0, 2026-06-17) shipped with the wrong env var names in
user-facing documentation. Users following the 0.3.0 docs would have set
variables that the code silently ignored (the whitelist would not be applied),
which is a behaviour-affecting docs bug, not a cosmetic typo.

Recommended entry under a new `## Unreleased` section:

```
### Fixed

- Corrected recipient-whitelist env var names in README and docs
  (`EMAIL_RECIPIENT_WHITELIST_DOMAINS` / `EMAIL_RECIPIENT_WHITELIST_ADDRESSES`)
  to match `config.py`. The previously documented `EMAIL_RECIPIENT_DOMAINS` /
  `EMAIL_RECIPIENT_ADDRESSES` were silently ignored.
```

This is outside my documentation scope (CHANGELOG.md is owned by the
release-manager), so I flag it for the release-manager rather than editing it.

## Out of scope observations

- `docs/configuration.md` documents `EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE`
  (double underscore) while `.env.example` and README use
  `EMAIL_RATE_LIMIT_REQUESTS_PER_MINUTE` (single underscore, no `S`). This is
  a separate potential inconsistency, not introduced by this change, and is
  flagged for the functional-analyst / release-manager to triage independently.

## Verdict

approved

The documentation correction is complete, consistent across all five modified
files, matches the code in `config.py`, and the whitelist framing is coherent.
A CHANGELOG entry is recommended but belongs to the release-manager.