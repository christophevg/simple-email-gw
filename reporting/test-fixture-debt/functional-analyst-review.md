# Functional Review: test-fixture-debt

**Stage:** a (Functional Review, BLOCKING)
**Branch:** feature/test-fixture-debt
**Scope:** backend (test fixtures only)
**Date:** 2026-07-27
**Reviewer:** functional-analyst

## Summary

The change adds a single autouse fixture `_isolate_email_env` to `tests/conftest.py`
that clears every `EMAIL_*` environment variable before each test via
`monkeypatch.delenv`. This isolates the test suite from the developer's local
`../.env` (symlinked into the repo), which was leaking
`EMAIL_RECIPIENT_WHITELIST_DOMAINS=christophe.vg` at import time and causing 16
pre-existing failures (14 `WhitelistError` send-path + 2 `CLI TestWriteCommand`).

## Acceptance Criteria Check

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `make check` passes (format + lint + typecheck + tests) | PASS | 592 passed, 2 unrelated RuntimeWarnings; full check green |
| Tests hermetic (no `.env` leakage) | PASS | autouse delenv of all `EMAIL_*` keys per test |
| No production code changed | PASS | `git diff master -- src/` is empty; only `tests/conftest.py` (+21 lines) |
| No tests weakened/skipped | PASS | no `pytest.skip`/`xfail`/`importorskip` markers in tests/; no assertions removed |

## Implementation Review

`tests/conftest.py:14-31`:

```python
@pytest.fixture(autouse=True)
def _isolate_email_env(monkeypatch):
  for key in list(os.environ.keys()):
    if key.startswith("EMAIL_"):
      monkeypatch.delenv(key, raising=False)
  yield
```

Correctness:

- **autouse + monkeypatch**: correct combination. `monkeypatch` is function-scoped
  and automatically restored at teardown, so the delenv does not leak across
  tests and does not mutate the developer's real environment permanently.
- **`list(os.environ.keys())`**: snapshot is taken before iteration — avoids
  `RuntimeError: dictionary changed size during iteration`. Correct.
- **`raising=False`**: appropriate; a key may be absent on some platforms.
- **`yield` only**: no teardown needed because `monkeypatch` owns the restoration.
  Correct and minimal.
- **Underscore-prefixed name** (`_isolate_email_env`): signals "internal,
  autouse-only" — good hygiene; cannot be requested explicitly by mistake.

Docstring accurately explains the root cause (config.py loads `../.env` at import
time) and documents the composition contract with `monkeypatch.setenv` in test
bodies.

## Composition with `monkeypatch.setenv`

The fixture is autouse, so it runs before the test body. Tests that need
specific env vars set them inside the test via `monkeypatch.setenv`, which runs
*after* the delenv and overrides it. Verified consumers:

- `tests/test_config.py:69-72` — sets `EMAIL_IMAP_HOST`, `EMAIL_SMTP_HOST`,
  `EMAIL_USERNAME`, `EMAIL_PASSWORD`. PASSES.
- `tests/test_config.py:101` — sets `EMAIL_ACCOUNTS_JSON`. PASSES.
- `tests/test_sanitize.py:374,379` — sets `EMAIL_APPEND_MAX_SIZE`. PASSES.
- `tests/test_mcp.py:449` — sets `EMAIL_APPEND_MAX_SIZE`. PASSES.
- `tests/test_imap_client.py:570` — sets `EMAIL_APPEND_MAX_SIZE`. PASSES.

Redundancy note: `tests/test_config.py:110-115` (`test_empty_config`) still
contains its own `delenv` loop, now redundant with the autouse fixture. This is
harmless (idempotent) and not a weakening — the test still asserts the same
behavior. Leaving it avoids scope creep into a test-fixture-only fix.

## Test Hermeticity

Before the fix, 16 tests failed on developer machines with a populated `../.env`:
- 14 send-path tests hit `WhitelistError` because `recipient@example.com` was
  not on the developer's `EMAIL_RECIPIENT_WHITELIST_DOMAINS=christophe.vg`.
- 2 `CLI TestWriteCommand` tests drifted because `display.get_recipient_whitelist()`
  saw a live whitelist.

After the fix, the full suite (592 tests) passes on the same machine. The
isolation is performed per-test, so import-time state from `config.py` cannot
leak between tests either.

## Production Code

`git diff master -- src/` returns empty. Confirmed: no production code modified.

## Test Strength

- No `pytest.skip`, `pytest.mark.skip`, `@pytest.mark.xfail`, or
  `pytest.importorskip` markers added anywhere in `tests/`.
- No assertions removed or relaxed.
- No tests deleted.
- 592 tests pass (matches the pre-fix total count; the 16 previously-failing
  tests now pass without modification to their assertions).

## `make check` Result

```
======================= 592 passed, 2 warnings in 6.70s ========================
```

The 2 warnings are pre-existing `RuntimeWarning: coroutine ... was never
awaited` from `AsyncMock` usage in `test_sync_smtp_client.py` — unrelated to
this change and present on `master`.

Format, lint, and typecheck stages all green (check completed without aborting
before tests).

## Verdict

**approved**

The fix is minimal, correct, well-documented, and addresses the root cause
(import-time `.env` leakage) rather than papering over symptoms. It composes
correctly with the documented `monkeypatch.setenv` pattern, weakens no tests,
touches no production code, and `make check` is green.