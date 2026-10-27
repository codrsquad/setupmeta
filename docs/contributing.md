# Contributing

Runtime code must stay stdlib-only (plus setuptools), and keep working on the oldest Python we
support (`python_requires` in [setup.py](../setup.py)). Since projects pull setupmeta in at build
time, a bug breaks other people's builds: test coverage is kept at 100%.

`tox -e venv` creates `.venv/`. The tox envs (tests, `coverage`, `docs`, `style`, `reformat`,
`refreshscenarios`) are defined in [tox.ini](../tox.ini). The default envlist tests only the
oldest and newest Python, and `coverage` combines both runs: that's the cheap way to get full
coverage locally, CI covers the versions in between.

`tox -e docs` runs `check-manifest`, and the README render check PyPI relies on. Files added to
the repo must be covered by [MANIFEST.in](../MANIFEST.in) or ignored in `tox.ini`.

## Scenario snapshots

`tests/test_scenarios.py` replays every folder with a `setup.py` under `tests/scenarios/`
(edge cases) and `examples/` (vanilla projects), and compares the output to its `expected.txt`.
Replay mechanics are in `tests/scenarios.py`:

- every scenario runs the commands in `SCENARIO_COMMANDS`;
- without a `.commands` file, it runs in place with a fake `SCM_DESCRIBE` version;
- with one, it runs in a fresh clone of a temp bare origin, tagged `v1.2.3`, and runs the extra
  commands listed there too; lines starting with `:` are preparation commands, run before the
  initial commit.

After an intentional behavior change, `tox -e refreshscenarios` regenerates the snapshots:
review the `expected.txt` diffs, they are the user-visible output. Snapshot churn you didn't
intend is a bug to fix, not a snapshot to accept.

## Releasing

Record user-visible changes in the top section of [CHANGELOG.md](../CHANGELOG.md) as you go.
Pushing a `v*` tag triggers `.github/workflows/release.yml`, which runs the tests and publishes
to PyPI. setupmeta versions itself, so the tag normally comes from
`python setup.py version --bump <part> --commit --push`.
