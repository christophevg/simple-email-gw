# Testing Engineer Review — Issue #3 (Recipient Whitelist Env Var Names in Docs)

**Stage:** c (Quality Review — Testing) of `c3:project-review`
**Branch:** `feature/3-recipient-whitelist-env-vars`
**Scope:** documentation-only
**Reviewer:** testing-engineer
**Verdict:** approved

---

## 1. Are tests needed for this change?

No. This is a documentation-only correction of environment-variable names in
`README.md`, `.env.example`, and three files under `docs/`. No production code,
no test code, and no configuration consumed by the test suite was modified.

TDD test stubs do not apply: there is no behavior to specify. A test that
asserts "the README contains the string `EMAIL_RECIPIENT_WHITELIST_DOMAINS`"
would be a low-value string-existence check (anti-pattern: "Testing exact
output strings" / "Tests that never fail usefully"). It would also couple the
test suite to prose, which breaks on harmless rewording.

The correct guard against this class of bug is a docs/config drift check
(out of scope for this issue), not a behavioral test.

## 2. Did the fix break any previously-passing test?

No. The modified files are:

- `README.md`
- `.env.example`
- `docs/cli.md`
- `docs/configuration.md`
- `docs/security.md`

I verified via `grep` across `tests/`, `src/`, and `conftest.py` that none of
these files are read by the test suite or any Python module. They cannot
affect test execution.

Test results with the fix applied (`make test`):

- 576 passed, 16 failed, 1 warning

## 3. Pre-existing failures — independent confirmation

The bug-fixer reported 16 pre-existing failures on the base branch, verified
via `git stash`. I independently reproduced this:

1. `git stash` of the working-tree changes (the 5 docs files).
2. `make test` on the clean base branch.
3. `git stash pop` to restore the fix.

Result on the base branch **without** the fix:

- 576 passed, 16 failed — **identical** failure set and count.

The 16 failures are pre-existing and unrelated to this docs change. They fall
into two clusters, neither of which touches documentation:

- **14 `WhitelistError` failures** (`tests/test_smtp_client.py`,
  `tests/cli/test_display.py`): `Recipients not in whitelist: …`. These are
  whitelist-enforcement test-fixture failures — the fixtures do not disable
  the whitelist before exercising the send path. Root cause is in test
  setup, not in any file modified by this issue.
- **2 CLI compose failures** (`tests/cli/test_app.py`):
  `test_write_command_invalid_cc_reprompts` (`StopAsyncIteration`) and
  `test_write_command_ctrl_c_cancels_compose` (`assert False`). These are
  interactive-input harness failures, also pre-existing and unrelated to
  env-var documentation.

Because the diff is confined to Markdown and `.env.example` (no Python files,
no conftest, no pyproject), there is no mechanism by which this change could
alter test outcomes. The identical before/after failure set confirms this.

## 4. Correctness of the documented names (sanity check)

The fix aligns docs with the actual env vars derived from
`src/simple_email_gw/config.py`:

- `SettingsConfigDict(env_prefix="EMAIL_", …)`
- Fields `recipient_whitelist_domains` and `recipient_whitelist_addresses`

Pydantic-Settings therefore reads `EMAIL_RECIPIENT_WHITELIST_DOMAINS` and
`EMAIL_RECIPIENT_WHITELIST_ADDRESSES` — exactly the names now documented. The
previous `EMAIL_RECIPIENT_DOMAINS` / `EMAIL_RECIPIENT_ADDRESSES` forms were
incorrect. The fix is accurate.

## 5. Coverage note

Coverage is unchanged by this change (no source lines modified). The 74%
overall figure and the per-module numbers are identical with and without the
fix. No coverage gap is introduced or widened by this issue.

## 6. Recommendation

Approved. No tests are required for a documentation-only env-var-name
correction, the fix does not alter any code path exercised by the suite, and
the 16 failing tests are confirmed pre-existing and unrelated (independently
reproduced via `git stash`).

The 16 pre-existing failures should be tracked separately as test-fixture
debt (whitelist fixtures need to disable the whitelist for send-path tests;
the two CLI compose tests need an interactive-input harness fix). They are
**not** regressions from issue #3 and should not block this docs fix.