# Testing Engineer Review — Round 1 (Stage c, scoped re-run)

**Scope:** Issue #3 docs PR additions on `feature/3-recipient-whitelist-env-vars`.
**Round:** 1 (docs-only additions following prior review reports).
**Date:** 2026-07-27.

## What was added this round

Documentation-only changes (no code, no test files touched):

- `.env.example` — corrected rate-limit env var names to
  `EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE` /
  `EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR` (previously documented names were
  never read by the code).
- `docs/cli.md` — same rate-limit env var name corrections.
- `docs/configuration.md` — added a "Behavior when unset" fail-open warning
  block to the recipient whitelist section.
- `docs/security.md` — added the same fail-open warning block.
- `CHANGELOG.md` — new `Unreleased` section documenting the env var name
  corrections and the fail-open warning addition.
- `README.md` — recipient whitelist env var names corrected (committed earlier
  in the branch, included for context).

## Task 1 — Are tests needed for these additions?

**No.** All additions are documentation (prose, env var name strings in
example files, and a changelog entry). None of them change executable
behavior, configuration parsing, or test infrastructure. Documentation
accuracy is verified by review, not by executable tests.

Per the testing-engineer mandate, tests verify *behavior*, not prose or
file contents. Creating tests for env var name strings in `.env.example`
or for the presence of a warning paragraph would fall under the
"Testing file existence / configuration values" anti-pattern and would
be bloat.

## Task 2 — `make check` result

`make check` ran to completion. Result:

```
======================= 592 passed, 2 warnings in 6.86s =======================
```

The two warnings are pre-existing `RuntimeWarning: coroutine ...
was never awaited` from `AsyncMock` usage in
`tests/test_sync_imap_client.py` and `tests/test_sync_smtp_client.py`
(thread-safety tests). They are unrelated to this round's changes.

Coverage: 76% overall (unchanged from prior rounds; no code changed).

## Task 3 — Did the additions break any previously-passing tests?

No. All 592 tests pass. No test files were modified in this round
(`git diff master...HEAD -- tests/` shows only the earlier
`tests/conftest.py` isolation fix from a prior committed round, not part
of this round's working-tree additions).

The documentation additions cannot affect test execution because:

- They are not imported by any source module.
- They do not alter `.env` loading behavior (`.env.example` is a template;
  the test suite isolates from the developer's real `.env` via the
  conftest fixture added in a prior round).
- No assertion in the suite reads documentation files.

## Task 4 — Coverage analysis (gap check)

Since this is a docs-only round, the relevant question for a testing
engineer is whether the *underlying behavior* the docs now describe is
already covered by tests. The docs make two behavioral claims worth
confirming against the suite:

1. **Fail-open when whitelist env vars are unset/empty/misspelled.**
   Covered by `tests/test_whitelist.py::TestRecipientWhitelist::test_disabled_allows_all`
   (passes). The documented fail-open behavior is therefore backed by an
   existing behavioral test.

2. **Rate-limit env vars read under their corrected names
   (`EMAIL_RATE_LIMITS__IMAP_REQUESTS_PER_MINUTE`,
   `EMAIL_RATE_LIMITS__SMTP_SENDS_PER_HOUR`).**
   `src/simple_email_gw/safety/rate_limiter.py` is at 100% coverage, and
   `tests/test_sync_imap_client.py` / `tests/test_sync_smtp_client.py`
   exercise the rate limiter. The env var names are parsed by pydantic
   settings in `config.py` (82% covered). No new test is required for the
   docs correction itself; the parsing path is already exercised.

No coverage gaps introduced by this round. No new test stubs required.

## Verdict

**approved.**

- No tests needed for docs-only additions.
- `make check` passes (592/592, 2 pre-existing unrelated warnings).
- No previously-passing test broken.
- Behavioral claims in the new documentation are already backed by
  existing tests (`test_disabled_allows_all`, rate-limiter coverage).