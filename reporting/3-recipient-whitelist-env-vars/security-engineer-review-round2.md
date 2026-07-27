# Security Engineer Review — Round 2

**Branch**: `feature/3-recipient-whitelist-env-vars`
**Scope**: Issue #3 docs PR — fail-open warning accuracy (re-run after round 1 rejection)
**Date**: 2026-07-27

## Round 1 Rejection (recap)

F1: The fail-open warning's JSON-form sentence was factually wrong. It claimed the JSON form requires `"enabled": true` to activate the whitelist. In reality, `config.py:175` forces `whitelist.enabled = True` unconditionally whenever the `EMAIL_RECIPIENT_WHITELIST_JSON` env var is set, ignoring the JSON payload's `enabled` field.

The danger: an operator reading the old sentence could set `"enabled": false` in the JSON believing it disables the whitelist, while the gateway silently enforces it (or vice versa, misjudging the control). Misstating a fail-open/fail-closed boundary is directionally dangerous.

## Round 2 Verification

### Source of truth — `src/simple_email_gw/config.py:169-189`

```python
def get_recipient_whitelist(self) -> RecipientWhitelist:
    """Parse and return recipient whitelist configuration."""
    # JSON configuration takes precedence
    if self.recipient_whitelist_json:
        data = json.loads(self.recipient_whitelist_json)
        whitelist = RecipientWhitelist(**data)
        whitelist.enabled = True          # line 175 — forced, JSON field ignored
        return whitelist

    # Parse from individual env vars
    ...
    enabled = bool(domains or addresses)  # line 189 — env-var form: enabled iff non-empty
```

Observed behavior:
1. **JSON form**: when `EMAIL_RECIPIENT_WHITELIST_JSON` is set, `whitelist.enabled` is overwritten to `True` on line 175. The `enabled` field in the parsed JSON has no effect. To disable: unset the env var.
2. **Env-var form**: `enabled = bool(domains or addresses)` — whitelist is active only when at least one domain or address is non-empty; unset/empty/misspelled vars → disabled → fail-open.

### Updated warning text (both files)

`docs/security.md:119` and `docs/configuration.md:123` now read:

> **Behavior when unset**: The whitelist is enabled only when at least one domain or address is non-empty. If the variables are unset, empty, or misspelled, the whitelist is **disabled** and all recipients are allowed (fail-open). Verify the whitelist is active after configuration. The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) enables the whitelist unconditionally when set — the `enabled` field is ignored. To disable the whitelist, unset the env var.

### Claim-by-claim accuracy check

| Claim in warning | Source behavior | Verdict |
|---|---|---|
| Env-var form enabled iff at least one domain/address non-empty | `config.py:189` `enabled = bool(domains or addresses)` | Accurate |
| Unset/empty/misspelled vars → disabled → fail-open | Same line; empty list → `enabled=False` | Accurate |
| JSON form enables whitelist unconditionally when set | `config.py:175` forces `enabled = True` whenever JSON env var is truthy | Accurate |
| JSON `enabled` field is ignored | Line 175 overwrites whatever `RecipientWhitelist(**data)` set | Accurate |
| To disable the JSON whitelist, unset the env var | Only path that skips the `if self.recipient_whitelist_json:` branch | Accurate |

### Directional safety check

- No claim suggests `enabled: false` in JSON disables the whitelist (the round-1 hazard).
- No claim suggests the JSON form can be disabled via the payload.
- The disable instruction (unset env var) is the only mechanism the code actually supports.
- The fail-open characterization of the env-var form is unchanged and remains correct.

No new directionally-dangerous claims introduced. The fail-open documentation gap from round 1 is correctly and safely closed.

## Positive observations

- Warning is now consistent with the actual control semantics, removing operator-misconfiguration risk.
- Identical text in both `security.md` and `configuration.md` prevents drift between the two docs.
- Disable instruction maps to a concrete, supported action (unset env var), not a no-op JSON field.

## Scope classification

| Finding | Classification | Action |
|---|---|---|
| F1 (round 1): JSON-form sentence factually wrong | Blocking | Fixed in round 2 — verified |
| No new issues introduced | — | — |

## Verdict

**approved**

The round-1 fail-open documentation gap is closed. The updated warning accurately reflects `config.py:169-189` behavior for both config forms, introduces no new directionally-dangerous claims, and gives operators a working disable instruction.