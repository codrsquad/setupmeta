# setupmeta — repo context

setupmeta is a setuptools plugin: git-tag-based versioning and version bumps, plus auto-filled
`setup.py` metadata. It's self-hosted: our own `setup.py` uses it.

## Docs — read the relevant set before diving into the code

- **[`docs/`](./docs/index.md)** — how the repo works inside (internal, not published).
- **[`README.rst`](./README.rst)** — the user guide, also published on PyPI as `long_description`.

## Working notes

- Quick tests: `.venv/bin/pytest -q`; before finishing, `tox -e style,docs` and the oldest +
  newest Python with coverage (see [contributing](./docs/contributing.md)).
- Runtime code is stdlib-only, and must run on the oldest Python `python_requires` allows.
- Preserve backward compatibility for legacy `setup.py` users.
- Behavior changes ship with tests, README updates, and reviewed snapshot diffs in the same change.
- Keep the upcoming version's section at the top of [CHANGELOG.md](./CHANGELOG.md) current with
  user-visible changes.
- Ask the maintainer before changing bootstrap or version bump internals (`setup.py`,
  `setupmeta/hook.py`, `setupmeta/versioning.py`, `setupmeta/scm.py`), or when a change could
  break backward compatibility or produce broad snapshot churn.
