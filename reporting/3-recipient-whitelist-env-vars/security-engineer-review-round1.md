# Security Engineer Review (Round 1) — Issue #3 Docs PR

**Reviewer:** security-engineer
**Stage:** b (Domain Review — Security)
**Branch:** feature/3-recipient-whitelist-env-vars
**Scope:** docs (security-affecting)
**Date:** 2026-07-27

## Scope of This Round

1. Fail-open warning added to `docs/security.md` §6 (line 119) and
   `docs/configuration.md` (line 123).
2. Rate-limit env var name corrections in `.env.example` (lines 14-15) and
   `docs/cli.md` (lines 276-277).

## 1. Fail-Open Warning Accuracy vs. Code

### 1a. Individual env var path — ACCURATE

Warning text (both files, identical):

> The whitelist is enabled only when at least one domain or address is
> non-empty. If the variables are unset, empty, or misspelled, the whitelist
> is **disabled** and all recipients are allowed (fail-open).

Code (`src/simple_email_gw/config.py:169-191`):

```python
enabled = bool(domains or addresses)
return RecipientWhitelist(enabled=enabled, domains=domains, addresses=addresses)
```

and `is_allowed` (line 77-78):

```python
if not self.enabled:
    return True
```

The warning accurately describes this path. Unset / empty / whitespace-only /
misspelled vars yield `domains=[]`, `addresses=[]`, `enabled=False`, and
`is_allowed` returns `True` for every recipient. The fail-open characterization
is correct.

### 1b. JSON form path — INACCURATE (Finding F1)

Warning text (both files):

> The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) requires `"enabled": true`
> explicitly.

Code (`src/simple_email_gw/config.py:172-176`):

```python
if self.recipient_whitelist_json:
    data = json.loads(self.recipient_whitelist_json)
    whitelist = RecipientWhitelist(**data)
    whitelist.enabled = True
    return whitelist
```

The code **forces** `whitelist.enabled = True` whenever the JSON env var is
present and truthy, **regardless** of the `"enabled"` field in the JSON. The
statement "requires `"enabled": true` explicitly" is therefore false in both
directions:

- An operator may omit `"enabled"` or set `"enabled": false` — the whitelist
  is still activated.
- Conversely, the docs imply omitting `"enabled": true` would leave the
  whitelist off (fail-open); it would not.

This is a security-affecting documentation inaccuracy because the warning's
purpose is to document the fail-open boundary precisely. An operator who
trusts the warning may (a) believe they must add `"enabled": true` to get
protection (harmless, but misleading), or (b) believe setting
`"enabled": false` in JSON is a valid way to disable the whitelist at runtime
— it is not, and the silent override could trap an operator who attempts to
temporarily disable via JSON.

**Severity:** Low (CVSS ~3.5). No exploitable vulnerability; the actual code
behavior is *more* restrictive than the docs imply (JSON always enables), so
the fail-open risk is overstated, not understated, for the JSON path. But the
docs/code mismatch is real and security-relevant.

**OWASP:** A06 Insecure Design (docs/behavior contract drift on a security
control), A09 Security Logging Failures (no warning when JSON `enabled` is
silently overridden — separate from this docs PR but noted).

**Remediation (recommend, do not auto-apply):** Pick one — both are valid;
the choice is an owner decision, not a security-engineer decision.

1. **Fix the docs to match code (smaller, matches Simplicity Principle):**
   Replace the final sentence with text that accurately describes the
   override, e.g.:
   > The JSON form (`EMAIL_RECIPIENT_WHITELIST_JSON`) activates the whitelist
   > unconditionally when present — the `"enabled"` field in the JSON is
   > ignored. To disable the whitelist, unset the env var rather than
   > setting `"enabled": false`.

2. **Fix the code to honor the JSON `enabled` field:** remove line
   `whitelist.enabled = True` and rely on the JSON's `"enabled"` value. This
   makes the JSON form self-governing and matches the existing
   `docs/configuration.md` JSON example (`"enabled": true`). This is a code
   change and outside this PR's docs scope; raise as a separate hardening
   item if preferred.

Either way, the current warning text should not ship as-is.

### 1c. Conflation between the two paths

The warning is one blockquote covering both paths. The first sentence
("enabled only when at least one domain or address is non-empty") applies
*only* to the env-var path; for the JSON path the whitelist is enabled
whenever the JSON var is present, even with empty `domains`/`addresses`
lists (in which case `is_allowed` returns `False` for everyone — fail-closed,
not fail-open). The warning does not surface this distinction. Minor; the
F1 fix text above resolves it as a side effect.

## 2. Warning Clarity for Operators

Clarity is good overall:

- Uses a blockquote with a bold "**Behavior when unset**" lead-in —
  visually distinct from the surrounding config examples.
- Names the three failure modes operators actually hit: unset, empty,
  misspelled. The "misspelled" word is especially valuable — it is exactly
  the footgun this issue was opened to fix.
- Explicitly uses the term "fail-open" and states the consequence
  ("all recipients are allowed").
- Closes with actionable guidance: "Verify the whitelist is active after
  configuration."

An operator reading this will understand the fail-open risk for the env-var
path. The JSON-path sentence (F1) is the only clarity defect.

## 3. Does the Warning Close the Prior Fail-Open Documentation Gap?

The prior functional review (`functional-analyst-review.md`, lines 98-101)
identified the fail-open implication and explicitly deferred deeper hardening
out of scope. It did **not** ask for a warning; it asked only that the env var
names be corrected so that following the docs produces a working whitelist.

This round's warning goes beyond that minimum and, for the env-var path,
**adequately closes** the documentation-side fail-open gap: an operator who
reads §6 / the Recipient Whitelist section is now explicitly told the
whitelist is off-by-default and why. The gap is closed for the env-var form.

For the JSON form, the warning *introduces* a new inaccuracy (F1) and so does
not fully close the gap for that path. Net: the gap is closed for the primary
(env-var) path and partially reopened for the JSON path.

## 4. Rate-Limit Name Corrections

`.env.example` lines 14-15 and `docs/cli.md` lines 276-277 now read:

```
# EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE=60
# EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR=100
```

Cross-checked against `RateLimitConfig` fields
(`src/simple_email_gw/config.py:62-65`): `imap_requests_per_minute`,
`smtp_sends_per_hour`. With `env_prefix="EMAIL_"` and
`env_nested_delimiter="__"`, the documented names are exactly what
pydantic-settings will read. Correct.

Consistency check across all security-relevant docs:

| File | Names | Consistent |
|------|-------|-----------|
| `.env.example` (14-15) | `EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE`, `EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR` | Yes |
| `docs/cli.md` (276-277) | same | Yes |
| `docs/configuration.md` (86-87) | same | Yes |
| `docs/security.md` §4 (69-70) | prose: "60 requests per minute", "100 sends per hour" | Yes |

No security-doc inconsistency introduced by the rate-limit corrections. The
default values (60/min IMAP, 100/hour SMTP) match the code defaults and are
consistently stated everywhere they appear.

## Findings Classification

| Finding | Classification | Action |
|---------|---------------|--------|
| F1: JSON form `enabled` override undocumented / misdocumented | Related | Fix in this PR (docs) or split out as code hardening |
| F2: No runtime warning when an unrecognized `EMAIL_RECIPIENT_*` env var is set (silent misspelling) | New | Backlog — out of scope for a docs PR; noted in prior review |
| F3: JSON path silently overrides `enabled: false` (code behavior) | New | Backlog — code hardening, separate from docs PR |

## Positive Observations

- The warning is placed in both the security policy and the configuration
  guide, so operators encounter it regardless of which doc they read.
- The "misspelled" failure mode is explicitly called out — this is the exact
  root cause of issue #3 and its inclusion is good security communication.
- The warning uses the correct technical term "fail-open" and states the
  operational consequence plainly.
- Rate-limit corrections are accurate and consistent across all four files.
- The env-var-path description matches the code exactly.

## Verdict

**rejected: F1 must be resolved before merge.**

The warning accurately closes the fail-open documentation gap for the
env-var path, and the rate-limit corrections are clean. However, the final
sentence of the warning ("The JSON form requires `"enabled": true`
explicitly") is factually wrong versus the code at
`src/simple_email_gw/config.py:175`, which forces `enabled = True`
regardless of the JSON's `enabled` field. Shipping a security warning that
misstates the enablement semantics of a security control would replace one
docs/code mismatch with another.

Recommended resolution (owner's choice):

- Docs-only fix (preferred for scope): replace the JSON-form sentence with
  text stating the whitelist is activated unconditionally when the JSON env
  var is present and the `"enabled"` field is ignored; to disable, unset the
  env var. See §1b remediation text.

Once F1 is corrected, this review converts to **approved**. F2 and F3 are
backlog items, not blockers for this docs PR.