# Testing-Engineer Review — test-fixture-debt

**Scope:** `tests/conftest.py` only (autouse fixture `_isolate_email_env`).
**Branch:** `feature/test-fixture-debt` (uncommitted working-tree change).
**Verdict:** **approved**.

---

## 1. Fixture correctness

The fixture iterates `list(os.environ.keys())`, deletes every key starting
with `EMAIL_` via `monkeypatch.delenv(..., raising=False)`, then yields.
`monkeypatch` auto-restores each var at teardown, so leakage between tests is
impossible. Snapshotting `list(...)` before iteration avoids
"dict changed during iteration". The pattern is idiomatic and correct.

Ordering: autouse fixtures run before test-bound `monkeypatch.setenv`, so tests
that need a specific `EMAIL_*` value (e.g. `tests/test_config.py` sets
`EMAIL_IMAP_HOST`/`EMAIL_SMTP_HOST`/`EMAIL_USERNAME`/`EMAIL_PASSWORD`;
`tests/test_sanitize.py`, `tests/test_imap_client.py`, `tests/test_mcp.py` set
`EMAIL_APPEND_MAX_SIZE`) override the cleared slate. Verified empirically:
`make check` = 592 passed, including those env-dependent tests. Composition is
sound.

## 2. Hermetic isolation coverage

Audit of env reads in `src/simple_email_gw`:

| Read site | Var | Covered? |
|-----------|-----|----------|
| `config.py` (pydantic-settings, `env_prefix="EMAIL_"`) | all `EMAIL_*` | yes — prefix sweep |
| `imap/client.py:38` `DEFAULT_WORKSPACE = Path(os.environ.get("EMAIL_WORKSPACE", ...))` | `EMAIL_WORKSPACE` | yes (caveat §5) |
| `safety/sanitize.py:286` `os.environ.get("EMAIL_APPEND_MAX_SIZE")` | `EMAIL_APPEND_MAX_SIZE` | yes |

All env vars read by this project carry the `EMAIL_` prefix. The fixture's
prefix sweep covers the complete set. No `os.getenv` / `os.environ` read of a
non-`EMAIL_` var exists in `src/`, so non-`EMAIL_` leakage (e.g.
`OBSIDIAN_API_KEY`, `OLLAMA_API_KEY`, `GEMINI_API_KEY` present in `../.env`)
is not a concern for this codebase.

## 3. Right reason, not weakened assertions

The 14 send-path failures were `WhitelistError` raised from
`smtp/client.py:226` / `:339` because `get_recipient_whitelist()` read the
leaked `EMAIL_RECIPIENT_WHITELIST_DOMAINS=christophe.vg` and blocked
`recipient@example.com`. The 2 CLI `TestWriteCommand` failures were the
unpatched-`get_recipient_whitelist` paths drifting on the same leak.

Verified the previously-failing tests still assert meaningful behavior:
`tests/test_smtp_client.py` asserts `result["status"] == "sent"`, Message-ID
presence/format, `appended is True`, `append_folder`, audit-log kwargs, and
imap call args — not weakened to `assert True` or try/except pass-throughs.
The CLI tests at `tests/cli/test_app.py:1462+` patch `get_recipient_whitelist`
explicitly and assert whitelist-violation aborts (line 1495), so they are
hermetic regardless of env and were failing only on the unpatched paths.

With the fixture, whitelist defaults to `enabled=False` → recipient accepted →
the real send/append code path executes and is asserted. The tests pass
because the code under test runs correctly under a clean env, not because
assertions were relaxed.

## 4. Over-isolation risk — balance is right

The fixture clears *all* `EMAIL_*` vars, which could theoretically mask a bug
where production reads an env var that no test sets. In practice the opposite
holds: tests that depend on an env var now *must* declare it via
`monkeypatch.setenv`, making the dependency explicit rather than implicit on
the developer's machine state. This raises signal, not lowers it. The scope
(prefix `EMAIL_`) is tight — it does not clear unrelated env (PATH, HOME,
term vars), avoiding collateral damage.

Recommended (non-blocking) guardrail: if a future test silently depends on an
`EMAIL_*` var that the fixture clears, it will fail loudly rather than pass
mysteriously — which is the desired failure mode.

## 5. Observation (separate, not required for this fix)

`config.py:34` calls `_load_dotenv()` at **import time**, and `../.env` is a
symlink to the developer's real `.env` containing live credentials
(`EMAIL_PASSWORD`, `OAUTH2_TOKEN`, etc.) and
`EMAIL_WORKSPACE=/tmp/email_workspace`. Two concerns worth noting for a
follow-up:

1. **Import-time module-level capture.** `imap/client.py:38` captures
   `DEFAULT_WORKSPACE` at import. The per-test fixture clears `EMAIL_WORKSPACE`
   in `os.environ` but cannot undo the already-captured module constant. Today
   this is benign because the `.env` value equals the hardcoded default
   (`/tmp/email_workspace`), but if the `.env` value ever diverged, the
   fixture could not restore it. Tests depending on `DEFAULT_WORKSPACE` would
   silently use the developer's value.

2. **`_load_dotenv()` unguarded in test mode.** Production code loading a
   sibling `.env` at import is reasonable, but in test mode it poisons the
   process env before any fixture can run. The autouse fixture mitigates this
   for `EMAIL_*`, but the cleaner fix would be to guard `_load_dotenv()` (e.g.
   skip when `PYTEST_CURRENT_TEST` is set, or behind an explicit opt-in flag),
   or to point the env-file lookup at a test fixture path. This is a
   production-code change and out of scope for this test-only fix; flagged for
   the owner.

## 6. Independent `make check`

```
592 passed, 2 warnings in 7.15s
TOTAL coverage 76%
```

Warnings are pre-existing `ResourceWarning` / `RuntimeWarning` on
`AsyncMock` coroutines in `test_sync_smtp_client.py` — unrelated to this
change.

## 7. Summary

| Check | Result |
|-------|--------|
| Fixture mechanically correct | yes |
| Covers all `EMAIL_*` env reads | yes (complete) |
| Non-`EMAIL_` leak risk | none for this codebase |
| 16 failures fixed for right reason | yes — assertions intact, real code path exercised |
| Over-isolation risk | low — explicit env deps, tight prefix scope |
| `make check` green | yes, 592 passed |
| Assertions weakened | no |

**Approved.** Recommend the owner consider §5 (guard `_load_dotenv()` in test
mode) as a separate, optional follow-up to eliminate the import-time env
poisoning class of bugs at the source.