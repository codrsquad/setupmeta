import os
import re

from mock import patch
from six import StringIO

import setupmeta
from setupmeta.commands import _show_dependencies, DepTree, find_venv

from . import conftest


def run_setup_py(args, expected, folder=None):
    expected = expected.splitlines()
    output = conftest.run_setup_py(folder or os.getcwd(), *args)
    for line in expected:
        line = line.strip()
        if not line:
            continue

        m = re.search(line, output)
        assert m, "'%s' not present in output of '%s': %s" % (line, " ".join(args), output)


def test_check(sample_project):
    # First sample_project is a pristine git checkout, check should pass
    output = conftest.run_setup_py(sample_project, "explain")
    assert 'install_requires: (req1.txt ) ["click>7.0"]' in output

    output = conftest.run_setup_py(sample_project, "check")
    assert not output

    # Now let's modify one of the files
    with open(os.path.join(sample_project, "sample.py"), "w") as fh:
        fh.write("print('hello')\n")

    # check should report that as a pending change
    output = conftest.run_setup_py(sample_project, "check")
    assert "Pending changes:" in output


def test_check_dependencies():
    if os.environ.get("VIRTUAL_ENV"):
        # check --deptree is only useful when ran from a venv, which is guaranteed when invoking tests via tox (but may not be otherwise)
        run_setup_py(
            ["check", "--deptree"],
            """
                mock==.+
                pytest-cov==.+
            """,
            folder=conftest.PROJECT_DIR,
        )

    with patch("setupmeta.commands.find_venv", return_value=None):
        with conftest.capture_output() as logged:
            assert _show_dependencies(None) == 1
            assert "Could not find virtual environment" in logged

    with patch("setupmeta.commands.find_subfolders", return_value=[]):
        with conftest.capture_output() as logged:
            assert _show_dependencies(None) == 1
            assert "Could not find 'site-packages' subfolder" in logged

    with patch.dict(os.environ, {"VIRTUAL_ENV": ""}):
        with patch("os.path.isdir", return_value=True):
            assert find_venv()

    with patch("setupmeta.pkg_resources", spec=str):
        with conftest.capture_output() as logged:
            assert _show_dependencies(None) == 1
            assert "pkg_resources is not available" in logged


class FakeDist:
    def __init__(self, spec, requires):
        req = setupmeta.pkg_req(spec)
        self.key = req.key
        self.version = req.specs[0][1] if req.specs else "1.0"
        self._requires = requires

    def requires(self):
        return self._requires

    @classmethod
    def from_string(self, specs):
        result = []
        for spec in specs.split():
            name, _, req = spec.partition(":")
            if req:
                req = [setupmeta.pkg_req(r) for r in req.split("+")]
            else:
                req = []
            result.append(FakeDist(name, req))
        return result


class FakeDefinition:
    def __init__(self, value):
        self.value = value


def expect_render(definitions, spec, expected):
    dists = FakeDist.from_string(spec)
    definitions = dict((k, FakeDefinition(v)) for k, v in definitions.items())
    tree = DepTree(dists, definitions)
    s = tree.rendered()
    assert s.strip() == expected.strip()
    return tree


def test_dep_tree():
    # No deps edge case
    expect_render({}, "", """
Dependency tree:
- no dependencies -
""")

    # Simple case, no conflicts, no cycles
    tree = expect_render(
        {"install_requires": ["mock"]},
        "mock==2.0:pbr>=0.11 pbr",
        """
Dependency tree:
install_requires:
----------------
  mock==2.0
    pbr [required: >=0.11, installed: 1.0]
""")

    # Some extra edge case coverage
    assert tree.packages["mock"] != tree.packages["pbr"]
    assert str(tree.packages["mock"]) == "mock"
    pbr = tree.packages["mock"].requires[0]
    assert str(pbr) == "pbr"
    assert tree.packages["mock"].requires[0] == pbr
    report = []
    seen = set()
    tree.render_section(report, seen, "some title", ["absent"])
    assert not report
    assert not seen

    # Conflict and cycles
    expect_render(
        {"install_requires": ["mock"], "extras_require": {"bonus": ["pbr"]}},
        "mock==2.0:pbr+attrs pbr:attrs attrs:six six:mock>=3.0 foo",
        """
Dependency tree:
install_requires:
----------------
  mock==2.0
    attrs [required: Any, installed: 1.0]
      six [required: Any, installed: 1.0]
        mock [required: >=3.0, installed: 2.0] CONFLICT!
          pbr [required: Any, installed: 1.0]
    pbr [required: Any, installed: 1.0]
      attrs [required: Any, installed: 1.0]
        six [required: Any, installed: 1.0]
          mock [required: >=3.0, installed: 2.0] CONFLICT!

extras_require[bonus]:
---------------------
  pbr==1.0
    attrs [required: Any, installed: 1.0]
      six [required: Any, installed: 1.0]
        mock [required: >=3.0, installed: 2.0] CONFLICT!
          pbr [required: Any, installed: 1.0]

other:
-----
  foo==1.0


1 conflicts: mock

2 cycles found:
attrs -> six -> mock -> attrs
pbr -> attrs -> six -> mock -> pbr
""")


def test_explain():
    """ Test setupmeta's own setup.py """
    run_setup_py(
        ["explain"],
        """
            author:.+ Zoran Simic
            description:.+ Simplify your setup.py
            license:.+ MIT
            url:.+ https://github.com/codrsquad/setupmeta
            version:.+ [0-9]+\\.[0-9]
        """,
        folder=conftest.PROJECT_DIR,
    )


def test_version(sample_project):
    run_setup_py(["version", "--bump", "major", "--simulate-branch=HEAD"], "Can't bump branch 'HEAD'")

    run_setup_py(
        ["version", "--bump", "major", "--simulate-branch=master", "--push"],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\\d.]+ -m "Version [\\d.]+"
            Not running 'git push --tags origin' as you don't have an origin
        """,
    )

    run_setup_py(
        ["version", "--bump", "minor", "--simulate-branch=master"],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\\d.]+ -m "Version [\\d.]+"
        """,
    )

    run_setup_py(
        ["version", "-b", "patch", "--simulate-branch=master"],
        """
            Can't bump 'patch', it's out of scope of main format .+ acceptable values: major, minor
        """,
    )

    run_setup_py(["version", "--show-next", "major"], "[\\d.]+")
    run_setup_py(["version", "--show-next", "minor"], "[\\d.]+")
    run_setup_py(["version", "-a", "patch"], "out of scope of main format")

    run_setup_py(["version", "-a", "patch"], "[\\d.]+", folder=conftest.PROJECT_DIR)


@patch("sys.stdout.isatty", return_value=True)
@patch("os.popen", return_value=StringIO("60"))
@patch.dict(os.environ, {"TERM": "testing"})
def test_console(*_):
    setupmeta.Console._columns = None
    assert setupmeta.Console.columns() == 60


def touch(folder, isdir, *paths):
    for path in paths:
        full_path = os.path.join(folder, path)
        if isdir:
            os.mkdir(full_path)
        else:
            with open(full_path, "w") as fh:
                fh.write("from setuptools import setup\nsetup(setup_requires='setupmeta')\n")


def test_clean(sample_project):
    touch(sample_project, True, ".idea", "build", "dd", "dd/__pycache__", "foo.egg-info")
    touch(sample_project, False, "foo", "a.pyc", ".pyo", "bar.pyc", "setup.py", "dd/__pycache__/a.pyc")
    run_setup_py(
        ["cleanall"],
        """
        deleted build
        deleted foo.egg-info
        deleted dd.__pycache__
        deleted 2 .pyc files, 1 .pyo files
        """,
    )
    # Run a 2nd time: nothing to be cleaned anymore
    run_setup_py(["cleanall"], "all clean, no deletable files found")
