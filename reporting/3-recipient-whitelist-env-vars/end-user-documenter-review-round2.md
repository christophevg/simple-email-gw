# End-User Documenter Review — Round 2 (docs additions)

**Branch:** `feature/3-recipient-whitelist-env-vars`
**Scope:** round-2 correction to the fail-open warning's JSON-form sentence
**Reviewer:** end-user-documenter
**Date:** 2026-07-27

## Scope of this review

Round 1 rejected the fail-open warning over one factual inaccuracy: the JSON-form sentence claimed `"enabled": true` was required, but `config.py:175` forces `whitelist.enabled = True` unconditionally when JSON is present. Round 2 replaces that sentence in both `docs/security.md:119` and `docs/configuration.md:123` with:

> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) enables the whitelist unconditionally when set — the `enabled` field is ignored. To disable the whitelist, unset the env var.

This review checks (1) the corrected sentence for clarity, tone, and consistency, (2) that it reads naturally in context, and (3) that the existing CHANGELOG entry remains accurate.

## 1. Corrected JSON-form sentence — clarity, tone, consistency

**Location:** `docs/security.md:119`, `docs/configuration.md:123`

**Verdict: approved.**

- **Factual accuracy (the round-1 blocker):** Confirmed against `config.py:172-176`. When `recipient_whitelist_json` is set, the whitelist is built from the JSON and `whitelist.enabled` is forced to `True` on line 175, regardless of the JSON's `enabled` field. The new sentence ("enables the whitelist unconditionally when set — the `enabled` field is ignored") matches this behavior exactly.
- **Actionable guidance:** "To disable the whitelist, unset the env var." gives the user a concrete, correct remediation path. This is the only way to disable the JSON-form whitelist, and it is stated plainly.
- **Tone:** Advisory and consistent with the rest of the blockquote — direct, non-alarming, user-facing.
- **Consistency across files:** The sentence is byte-identical in both `docs/security.md` and `docs/configuration.md`, preserving the cross-file consistency noted as a strength in round 1.
- **Terminology:** "unconditionally" is the right word here — it signals that no field inside the JSON can turn the whitelist off, which is precisely the behavior users need to understand to avoid the footgun where `"enabled": false` silently does nothing.

## 2. Readability in context

**Verdict: reads naturally.**

The full blockquote in both files now reads:

> **Behavior when unset**: The whitelist is enabled only when at least one domain or address is non-empty. If the variables are unset, empty, or misspelled, the whitelist is **disabled** and all recipients are allowed (fail-open). Verify the whitelist is active after configuration. The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) enables the whitelist unconditionally when set — the `enabled` field is ignored. To disable the whitelist, unset the env var.

- The heading "Behavior when unset" still fits the first clause cleanly. The JSON-form clarification extends the advisory rather than contradicting it — the em-dash and the follow-up "To disable… unset the env var" make the contrast with the env-var form explicit.
- The transition from the env-var-form description ("enabled only when at least one domain or address is non-empty") to the JSON-form description ("enables the whitelist unconditionally when set") is now a clean contrast between two distinct enablement rules, which is exactly what a user configuring the whitelist needs to hold in their head.
- One minor note (non-blocking): the heading "Behavior when unset" technically only describes the first half of the blockquote; the JSON-form clause is about behavior *when set*. This was already true in round 1 and is not introduced by the round-2 edit. The blockquote is short enough that the heading still serves as a useful label rather than a mislabel. No change required.

## 3. CHANGELOG entry — still accurate

**Location:** `CHANGELOG.md:14`

> Added fail-open warning to recipient whitelist documentation in `docs/security.md` and `docs/configuration.md`.

**Verdict: still accurate; no update needed.**

- The entry describes the addition of the warning to both files, which is what happened. A wording refinement *within* that warning does not invalidate the entry — the entry does not quote the warning's text, so it does not need to track sentence-level edits.
- The entry remains under `### Fixed` in the `## Unreleased` section, correctly placed above `## 0.3.0 - 2026-06-17`.
- The two adjacent entries (env var name corrections on lines 12–13) are unaffected by this round's change.
- The round-1 minor observation about repeated "were never read by the code" phrasing across entries 1 and 2 still stands as a non-blocking style note; no change required for merge.

## Summary

| Check | Result |
|-------|--------|
| JSON-form sentence — factual accuracy vs `config.py:175` | Accurate |
| JSON-form sentence — clarity and tone | Clear, advisory, actionable |
| Cross-file consistency (`security.md` vs `configuration.md`) | Identical, consistent |
| Readability in surrounding blockquote context | Reads naturally; clean contrast between forms |
| Heading "Behavior when unset" still fits | Acceptable (pre-existing, non-blocking) |
| CHANGELOG entry accuracy | Still accurate; wording change does not invalidate it |

## Recommendation

**approved** — the round-1 factual inaccuracy is corrected. The new JSON-form sentence is accurate against the code, reads naturally in context, is consistent across both docs files, and the CHANGELOG entry remains correct. No further docs changes are required for this PR.