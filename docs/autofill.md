# Auto-fill

Every value is a `Definition` (`setupmeta/model.py`) holding its winning value plus every
source it was seen in. `explain` prints that list: the winner on top, the others under `\_`.
A key that isn't a setuptools field is shown with a `*` suffix, and never passed to setuptools.

Ranking rule, in `Definition.add()`: the first value seen wins, unless added with
`override=True`, which takes over and moves to the top. `SetupMeta.finalize()` relies on order:

- explicit `setup()` / `setup.cfg` values are added first, tagged `explicit`;
- `PKG-INFO` values next (present when building from an sdist, so the sdist's recorded version
  and metadata win over re-computing them);
- scanned modules are merged in scan order, so the first file stating a value wins;
- `auto_fill()` overrides any value, unless the key was explicit. That's how a git-derived
  version beats a `__version__` found in code, while an explicit `version=` beats both.

Module scanning (`SimpleModule`) never imports anything: it matches `__key__ = "value"` lines,
and `key: value` lines in the first paragraph of docstrings, with regexes. Expressions are
silently ignored. The first docstring line that isn't a `key: value` becomes `docstring_lead`, a
fallback for `description`.

Requirements parsing lives in `setupmeta/__init__.py` (`ReqEntry`, `RequirementsFile`), not in
`model.py`. Abstraction only ever strips simple `name==version` pins; `requirements.in` is
never abstracted, since it's meant as a `pip-compile` input.

README handling is in `setupmeta/content.py`. The `.. [[end long_description]]` and
`.. [[include ...]]` tokens only count when nothing but whitespace surrounds them on their line:
that's what lets our own README mention them inside RST literals without being cut short.
