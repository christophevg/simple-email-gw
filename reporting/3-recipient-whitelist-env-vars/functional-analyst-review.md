# Functional Review — Issue #3: Recipient Whitelist Env Var Names

**Reviewer:** functional-analyst
**Stage:** a (Functional Review, BLOCKING)
**Branch:** feature/3-recipient-whitelist-env-vars
**Scope:** docs
**Date:** 2026-07-27

## Issue Summary

The README and docs advertised env var names `EMAIL_RECIPIENT_DOMAINS` and
`EMAIL_RECIPIENT_ADDRESSES` for the recipient whitelist. The code in
`src/simple_email_gw/config.py` (`ServerConfig`, `env_prefix="EMAIL_"`, fields
`recipient_whitelist_domains` / `recipient_whitelist_addresses`, no
`validation_alias`) only reads `EMAIL_RECIPIENT_WHITELIST_DOMAINS` and
`EMAIL_RECIPIENT_WHITELIST_ADDRESSES`. Users following the docs would silently
leave the whitelist disabled (fail-open), allowing outbound email to any
recipient.

## Verification Performed

### 1. Canonical env var names confirmed against code

`src/simple_email_gw/config.py`:
- `ServerConfig` uses `env_prefix="EMAIL_"` (line 111).
- Fields: `recipient_whitelist_json` (138), `recipient_whitelist_domains` (139),
  `recipient_whitelist_addresses` (142).
- No `validation_alias` on any field (grep confirmed no alias usage).
- Therefore canonical env var names are exactly:
  - `EMAIL_RECIPIENT_WHITELIST_DOMAINS`
  - `EMAIL_RECIPIENT_WHITELIST_ADDRESSES`
  - `EMAIL_RECIPIENT_WHITELIST_JSON`

### 2. All occurrences of wrong names corrected

Repo-wide grep for `EMAIL_RECIPIENT_DOMAINS` / `EMAIL_RECIPIENT_ADDRESSES`
excluding the `WHITELIST` variants returned **zero hits** (excluding `.git/`).
No stale references remain in docs, README, .env.example, code, or tests.

### 3. Correct names present in all modified files

| File | Line(s) | Status |
|------|---------|--------|
| `.env.example` | 18-19 | Correct |
| `README.md` | 212-213 | Correct |
| `docs/cli.md` | 280-281 | Correct |
| `docs/configuration.md` | 102, 108, 143 | Correct |
| `docs/security.md` | 111-112 | Correct |

The `EMAIL_RECIPIENT_WHITELIST_JSON` variant (also a real code-read name) was
already correctly named in `docs/configuration.md:116` and required no change.

### 4. Diff review

`git diff HEAD~1` confirms exactly 6 line replacements across the 5 files,
each a clean rename of the two wrong names to the two correct names. No
incidental edits, no scope creep, no whitespace noise.

### 5. Acceptance criteria

> "the docs now match the code's actual env var names"

**Met.** Every documented env var name for the recipient whitelist now matches
the name the `ServerConfig` pydantic-settings model actually reads. A user
copy-pasting from any of the modified files will get a working whitelist.

## Standards Consultation Check

The plan called for consulting `c3:readme` and `c3:documentation` skills. The
bug-fixer did not explicitly invoke either skill.

**Assessment: non-blocking for this scoped fix.**

Reasoning:
- This is a targeted, mechanical correction of two incorrect env var names to
  match the canonical names read by the code. It is not authoring new
  documentation, restructuring the README, or creating new doc sections.
- The correctness criterion is purely factual (does the documented name match
  the code-read name?), verifiable by grep against `config.py` — exactly the
  verification performed above.
- The `c3:readme` and `c3:documentation` skills govern structure, voice, and
  maintenance patterns for new/overhauled docs. A two-token rename per line
  does not engage those concerns.
- Applying the skills here would not have changed the outcome; the fix is
  already minimal, accurate, and complete.

**Recommendation for future docs-touching tasks:** when a docs change is more
than a targeted factual correction (e.g., adding sections, reorganizing,
rewriting), the skills should be consulted explicitly. For this issue, the gap
is noted but does not block approval.

## Edge Cases Considered

- **JSON env var:** `EMAIL_RECIPIENT_WHITELIST_JSON` was already correctly
  documented; no change needed. Confirmed.
- **Code/tests:** No code or test files reference the wrong names, so no code
  change was required. Scope correctly limited to docs.
- **Fail-open security implication:** The root cause (silent fail-open when
  docs are followed) is resolved by making the docs accurate. A deeper
  hardening (e.g., warning when an unrecognized `EMAIL_RECIPIENT_*` env var is
  set) is out of scope for this docs bug and would be a separate enhancement.

## Verdict

**approved**

The corrections are accurate, complete, and match the code's actual env var
names. No stale references remain. Acceptance criteria met. The standards-
consultation gap is non-blocking for a targeted factual correction of this
size.