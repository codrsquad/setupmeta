import os
import re
from unittest.mock import patch

import setupmeta

from . import conftest


def run_setup_py(args, expected, folder=None):
    expected = expected.splitlines()
    output = conftest.run_setup_py(folder or os.getcwd(), *args)
    for line in expected:
        line = line.strip()
        if line:
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
        ["version", "--bump", "major", "--simulate-branch=main", "--push"],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\\d.]+ -m "Version [\\d.]+"
            Not running 'git push --tags origin' as you don't have an origin
        """,
    )

    run_setup_py(
        ["version", "--bump", "minor", "--simulate-branch=main"],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\\d.]+ -m "Version [\\d.]+"
        """,
    )

    run_setup_py(
        ["version", "-b", "patch", "--simulate-branch=main"],
        """
            Can't bump 'patch', it's out of scope of main format .+ acceptable values: major, minor
        """,
    )

    run_setup_py(["version", "--show-next", "major"], "[\\d.]+")
    run_setup_py(["version", "--show-next", "minor"], "[\\d.]+")
    run_setup_py(["version", "-a", "patch"], "out of scope of main format")

    run_setup_py(["version", "-a", "patch"], "[\\d.]+", folder=conftest.PROJECT_DIR)


@patch("sys.stdout.isatty", return_value=True)
@patch("os.popen", return_value=conftest.StringIO("60"))
@patch.dict(os.environ, {"TERM": "testing"})
def test_console(*_):
    setupmeta.Console._columns = None
    assert setupmeta.Console.columns() == 60


def touch(folder, isdir, *paths):
    for path in paths:
        full_path = os.path.join(folder, path)
        if isdir:
            os.makedirs(full_path)

        else:
            with open(full_path, "w") as fh:
                fh.write("from setuptools import setup\nsetup(setup_requires='setupmeta')\n")


def test_clean(sample_project):
    touch(sample_project, True, ".idea", "build", "foo.egg-info", "subfolder/foo/__pycache__")
    touch(sample_project, False, "subfolder/foo/__pycache__/foo.pyc", "a.pyc", ".pyo", "bar.pyc", "setup.py")
    run_setup_py(
        ["cleanall"],
        """
        deleted build
        deleted foo.egg-info
        deleted 2 .pyc files, 1 .pyo files
        """,
    )
    # Run a 2nd time: nothing to be cleaned anymore
    run_setup_py(["cleanall"], "all clean, no deletable files found")
