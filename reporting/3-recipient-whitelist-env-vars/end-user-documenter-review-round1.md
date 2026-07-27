# End-User Documenter Review — Round 1 (docs additions)

**Branch:** `feature/3-recipient-whitelist-env-vars`
**Scope:** docs additions in the current uncommitted round
**Reviewer:** end-user-documenter
**Date:** 2026-07-27

## Scope of this review

Round-1 additions reviewed:
1. Fail-open warning blockquote in `docs/security.md` §6 and `docs/configuration.md` (Recipient Whitelist section).
2. `CHANGELOG.md` — new `## Unreleased` section with three `### Fixed` entries.
3. Rate-limit env var name corrections in `.env.example` and `docs/cli.md`.

## 1. Fail-open warning — clarity, consistency, tone

**Location:** `docs/security.md:119`, `docs/configuration.md:123`

**Verdict: mostly good, with one factual inaccuracy.**

Strengths:
- Identical text in both files — consistent.
- Clear heading ("Behavior when unset") and advisory tone.
- The term "fail-open" is introduced and immediately explained ("all recipients are allowed") — accessible to non-technical readers.
- Actionable guidance ("Verify the whitelist is active after configuration").
- The env-var-form claim is accurate: when `EMAIL_RECIPIENT_WHITELIST_DOMAINS` / `EMAIL_RECIPIENT_WHITELIST_ADDRESSES` are unset, empty, or misspelled, `enabled = bool(domains or addresses)` is `False` and `is_allowed()` returns `True` for all recipients (config.py:189, is_allowed at config.py:77-78). Fail-open confirmed.

Issue found — **factual inaccuracy in the JSON-form claim**:

The warning states:
> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) requires `"enabled": true` explicitly.

This is misleading. `config.py:172-176` shows that when `recipient_whitelist_json` is present, the code constructs the whitelist from the JSON and then **unconditionally forces `whitelist.enabled = True` on line 175**, overriding whatever the JSON contained. Consequences:

- The JSON form does **not** require `"enabled": true` — it works without that field, and even with `"enabled": false` the whitelist is still enabled.
- The statement implies omitting `enabled: true` would leave the whitelist disabled (fail-open), which is the opposite of the actual behavior.

Recommendation: correct the final sentence to reflect that the JSON form always enables the whitelist when present, e.g.:

> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) always enables the whitelist when set; the `enabled` field in the JSON is ignored.

This also surfaces a latent code-vs-docs mismatch worth noting to the development agents: a user who sets `"enabled": false` in the JSON believing it disables the whitelist will still have it enabled. That is a code behavior question, not a docs one, but the docs must not paper over it.

## 2. CHANGELOG entry — form, accuracy, Keep-a-Changelog conventions

**Location:** `CHANGELOG.md:8-14`

**Verdict: well-formed and accurate.**

- `## Unreleased` is placed immediately above the most recent release (`## 0.3.0 - 2026-06-17`), matching Keep-a-Changelog conventions.
- Three entries, all under `### Fixed`, all accurately describing the three changes in this round.
- Entry 1 (recipient whitelist env var names) describes commit `508ff0b` on this branch — correctly captured as unreleased.
- Entry 2 (rate-limit env var names) accurately names both the corrected and the previously documented variables.
- Entry 3 (fail-open warning) accurately references the two docs files touched.
- The "silently leaving the whitelist disabled (fail-open)" phrasing in entry 1 correctly communicates the user-visible impact.

Minor observation (non-blocking): entries 1 and 2 both end with "were never read by the code." — repetitive phrasing across two consecutive bullets. Could be tightened for flow, but not a correctness issue.

## 3. Rate-limit name corrections — consistency across all docs

**Verdict: consistent, no stale names remain.**

Corrected names match the code exactly:
- `config.py:110-116` sets `env_prefix="EMAIL_"` and `env_nested_delimiter="__"`.
- `config.py:135` `rate_limits: RateLimitConfig` with fields `imap_requests_per_minute` (line 62) and `smtp_sends_per_hour` (line 65).
- Resolved env var names: `EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE` / `EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR` — exactly what `.env.example:14-15` and `docs/cli.md:276-277` now show.

Grep across all non-reporting files for the stale names (`EMAIL_RATE_LIMIT_REQUESTS_PER_MINUTE`, `EMAIL_RATE_LIMIT_SENDS_PER_HOUR`, `EMAIL_RECIPIENT_DOMAINS`, `EMAIL_RECIPIENT_ADDRESSES`) returns hits only in `CHANGELOG.md:12-13`, where they are intentionally referenced as "the previously documented" names. No stale occurrences in user-facing config docs.

`docs/configuration.md` does not enumerate the rate-limit env vars by name (it documents rate limits elsewhere), so no correction was needed there — confirmed no stale names present.

## 4. `.env.example` — examples match corrected names and read naturally

**Location:** `.env.example:13-15`

```bash
# Rate Limiting (optional)
# EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE=60
# EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR=100
```

- Both names match the corrected code names.
- Default values (60 / 100) match `config.py:62-65` defaults.
- Reads naturally; the double-underscore nested delimiter is unusual for a `.env` file but is correct for pydantic-settings with `env_nested_delimiter="__"`. A brief inline comment noting the `__` maps to nested config could help users unfamiliar with the convention, but this is a nice-to-have, not a blocker.
- The recipient whitelist examples (`.env.example:17-19`) use the correct names and read naturally.

## Summary

| Check | Result |
|-------|--------|
| Fail-open warning — env-var form | Accurate, clear, consistent |
| Fail-open warning — JSON form claim | **Inaccurate** (code forces `enabled=True`, does not require it) |
| CHANGELOG form and placement | Correct |
| CHANGELOG accuracy | Accurate |
| Rate-limit name consistency | Consistent, no stale names |
| `.env.example` correctness | Correct and natural |

## Recommendation

**rejected** — one factual inaccuracy in the fail-open warning must be fixed before merge: the JSON-form sentence claims `"enabled": true` is required, but `config.py:175` forces `enabled = True` regardless of the JSON content. The sentence should be corrected to state the JSON form always enables the whitelist when present.

All other aspects (CHANGELOG, rate-limit name corrections, `.env.example`, env-var-form warning) are approved.