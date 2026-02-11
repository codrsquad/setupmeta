# AGENTS.md

## Purpose

This file defines repo-specific guidance for coding agents working on `setupmeta`.
Use it as the first source of truth for how to make changes safely and consistently.

## Project Summary

- `setupmeta` helps keep `setup.py` files minimal by auto-filling metadata and requirements.
- It provides custom setup commands: `explain`, `version`, and `check`.
- It supports git-tag-based versioning and automated version bumps.
- The project is self-hosted: `setup.py` uses `setupmeta` itself and has bootstrap behavior.

## Core Principles

- Preserve backward compatibility for users relying on legacy `setup.py` workflows.
- Keep runtime dependencies minimal; prefer stdlib for runtime code.
- Favor explicit, test-covered behavior over cleverness.
- Keep documentation aligned with actual behavior and test scenarios.

## Repository Layout

- `setupmeta/`: main library code (`commands`, `model`, `scm`, `versioning`, etc.)
- `tests/`: unit tests + scenario replay tests
- `tests/scenarios/` and `examples/`: behavior fixtures with `expected.txt` snapshots
- `docs/`: user and contributor documentation
- `setup.py`: self-bootstrapping package definition
- `tox.ini`: test/lint/docs/coverage orchestration

## Environment and Commands

Use these commands from repo root:

- Quick tests: `.venv/bin/pytest -q`
- Full test/lint/docs run: `tox`
- Single tox env: `tox -e py314`
- Fast compatibility matrix (old+new + coverage): `tox -e py39,py314,coverage`
- Style only: `tox -e style`
- Docs checks: `tox -e docs`
- Refresh scenario snapshots: `tox -e refreshscenarios`
- Manual command checks:
  - `.venv/bin/python setup.py explain`
  - `.venv/bin/python setup.py version`
  - `.venv/bin/python setup.py check -q`

Notes:

- `tox.ini` pins `UV_CACHE_DIR` to `.tox/.uv-cache`, so no command-line prefix is needed.
- `py37` exists because it is the oldest Python still supported by this library.
- If `py37` is unavailable locally (common on macOS arm64), substitute the oldest available interpreter and pair it with the newest one.
  Example: system Python `3.9` + `3.14` via `tox -e py39,py314,coverage`.
- Intent: keep local runs fast while still exercising one older runtime and one modern runtime, with `coverage combine` validating cross-env coverage data.

## Code Change Expectations

- Keep changes narrow and focused.
- Maintain Python compatibility targeted by this repo (including older supported versions).
- When changing behavior, update both tests and docs in the same change.
- Do not silently alter CLI output formats used by scenario snapshots unless intentional.
- If you touch versioning logic, verify:
  - `tests/test_versioning.py`
  - `tests/test_setup_py.py`
  - scenario outputs that include `version`/`explain`.

## Scenario Snapshot Rules

- Scenario tests compare command output against `expected.txt`.
- If behavior changes are intentional:
  1. Regenerate snapshots (`tox -e refreshscenarios`).
  2. Review diffs in `tests/scenarios/*/expected.txt` and `examples/*/expected.txt`.
  3. Ensure docs and release notes explain user-visible changes.
- If behavior changes are not intentional, fix code/tests instead of accepting snapshot churn.

## Documentation Rules

- Keep `README.rst`, `docs/*.rst`, and example READMEs consistent with current behavior.
- Avoid documenting deprecated/removed commands as active features.
- Keep versioning docs aligned with current strategy defaults and command examples.
- Record user-visible changes in `HISTORY.rst`.

## Safety and Review Checklist

Before finalizing a change, verify:

1. Tests pass for affected areas.
2. Formatting/lint checks pass.
3. Scenario snapshots are unchanged unless intentionally updated.
4. Docs are updated if behavior or commands changed.
5. No unrelated files were modified.

## When to Ask for Clarification

Ask the maintainer before proceeding if:

- A change could break backward compatibility.
- Expected output changes are broad/noisy and intent is unclear.
- A docs update conflicts with tested behavior.
- A refactor touches bootstrap or version bump internals in `setup.py`, `setupmeta/hook.py`, `setupmeta/versioning.py`, or `setupmeta/scm.py`.
