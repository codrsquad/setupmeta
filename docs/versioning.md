# Versioning

Three layers, all driven by `Versioning` (`setupmeta/versioning.py`):

- `Strategy` parses the user's `versioning=` value (`_parsed_versioning()`): a preconfigured
  name from `PRECONFIGURED` (aliases `default` and `tag` mean `post`), a format string, or a
  dict. Each `{...}` becomes a `VersionBit`. Bits not in `MAIN_BITS` get moved from the main to
  the local part, to stay PEP-440 compliant.
- `Version` (`setupmeta/scm.py`) is the parsed `git describe` output: tag components, distance,
  commit id, dirty flag. Its `post` / `dev` / `devcommit` properties render those bits.
- `Scm` subclasses talk to the source of truth, picked by `project_scm()`:
  `Snapshot` when the `SCM_DESCRIBE` env var is set, else `Git` for the nearest `.git` found
  walking *up* from the project dir, else `Snapshot` reading `.setupmeta.version`.

Surprises worth knowing:

- The nearest parent `.git` wins, even an unrelated one: a test project created inside our
  checkout (eg: under `_tmp/`) reports setupmeta's own version (verified).
- `dev` and `devcommit` render a bumped patch (`Strategy.rendered()` auto-bumps the bit before a
  trailing `{dev}`), so a dirty checkout exactly on `v0.1.0` gives `0.1.1.dev0+dirty`.
- With `distance` and `build-id`, a tag like `v0.1.3` yields `0.1.0` plus a warning: the
  patch component is the distance, so it can't be bumped either.
- A repo with no tag, or no commit yet, yields `0.0.0` rather than an error; `Git.get_version()`
  then counts commits itself.
- Only tags matching `v*.*` count by default: a repo tagged `1.2.0` reports `0.0.0`.

Bumping is `Versioning.bump()`: it checks branch, pending changes and remote tags, rewrites any
`__version__`-style line it found in `.py` sources (`update_sources()`, by recorded file:line),
commits that with `--no-verify`, then `Git.apply_tag()` refuses if the branch is behind its
remote, and creates an annotated `v<version>` tag. Every git call goes through `Git.run_git()`,
which prints instead of running when `--commit` isn't given.

`.setupmeta.version` is written whenever the git root isn't the project dir, so that a copy of
the project without `.git` (pip builds in a temp dir) still knows its version.

Tests: `tests/test_versioning.py` mocks git via `conftest.MockGit`; scenario snapshots cover the
end-to-end output, see [contributing](./contributing.md).
