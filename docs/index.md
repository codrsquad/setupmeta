# setupmeta internals

setupmeta is a setuptools plugin with no runtime dependencies besides setuptools. A project
activates it with `setup_requires="setupmeta"`; setuptools then calls our hooks, which compute a
version from git tags and fill in whatever `setup()` metadata wasn't given explicitly.
Users see the result through three `setup.py` commands: `explain`, `version` and `check`.
What users can do is documented in the [README](../README.rst); these pages cover the inside.

Where to start reading:

- `setupmeta/hook.py`: the entry points setuptools calls, short and the root of every flow.
- `SetupMeta.finalize()` in `setupmeta/model.py`: the auto-fill pipeline, in order.
- `Versioning` in `setupmeta/versioning.py`: computing and bumping versions.

Pages:

- [setuptools integration](./setuptools-integration.md): how and when setuptools hands us control.
- [Auto-fill](./autofill.md): how values are found, ranked, and reported by `explain`.
- [Versioning](./versioning.md): strategies, SCM backends, and the bump flow.
- [Bootstrap](./bootstrap.md): why our own `setup.py` looks the way it does.
- [Contributing](./contributing.md): tests, scenario snapshots, coverage, releasing.
- [Known gaps](./known-gaps.md): open TODOs and planned removals.

Release notes live in [CHANGELOG.md](../CHANGELOG.md).
