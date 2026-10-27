# Known gaps

- **`setup.py` is on its way out.** `setup_requires` is deprecated by setuptools, and
  `pyproject.toml` is declarative, so it leaves nothing to auto-fill. The plan is to keep
  git-tag versioning and bumps as the core, and to phase out the custom commands and metadata
  auto-fill. Until then, legacy `setup.py` users must keep working.
- **Only git is supported.** Another SCM would be a new `Scm` subclass in `setupmeta/scm.py`,
  picked up by `project_scm()` in `setupmeta/versioning.py`.
- **`versioning` isn't validated** when registered (TODO in `register_keyword()`), only once the
  version gets computed.
- **`pinned.txt`** is still read for `install_requires`, as a legacy fallback to phase out.
- **`setupmeta.model.get_pip()`** is dead code kept for external callers that import it.
