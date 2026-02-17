"""
Tests based on running legacy setup.py
"""

import sys
from pathlib import Path

import setupmeta

from . import conftest

SAMPLE_EMPTY_PROJECT = """
from setuptools import setup
setup(
    name='testing',
    py_modules=['foo'],
    setup_requires='setupmeta',
    versioning='distance',
)
"""


def write_to_file(path, text):
    with open(path, "w") as fh:
        fh.write(text)
        fh.write("\n")


def setup_py_output(*args):
    result = setupmeta.run_program(sys.executable, "setup.py", *args)
    return conftest.cleaned_output(result)


def test_brand_new_project():
    with setupmeta.temp_resource():
        conftest.run_git("init")
        with open("setup.py", "w") as fh:
            fh.write(SAMPLE_EMPTY_PROJECT)

        # Test that we avoid warning about no tags etc. on brand-new empty git repos
        assert setup_py_output("--version") == "0.0.0"

        # Now stage a file
        conftest.run_git("add", "setup.py")
        assert setup_py_output("--version") == "0.0.0+dirty"

        # Un-stage it
        conftest.run_git("reset", "setup.py")
        assert setup_py_output("--version") == "0.0.0"

        # Commit it, and touch a new file
        conftest.run_git("add", "setup.py")
        conftest.run_git("commit", "-m", "Initial commit")
        with open("foo", "w") as fh:
            fh.write("foo\n")

        assert setup_py_output("--version") == "0.0.1"


def test_git_versioning(sample_project):  # noqa: ARG001, fixture
    output = setup_py_output("--version")
    assert output == "0.0.1"

    # Bump with no initial tags shouldn't warn
    output = setup_py_output("version", "--bump", "minor")
    assert "UserWarning" not in output
    assert "Would run: git tag -a v0.1.0" in output

    conftest.run_git("tag", "-a", "v0.1.0", "-m", "Version 2.4.2")
    output = setup_py_output("--version")
    assert output == "0.1.0"

    output = setup_py_output("explain")
    assert "0.1.0" in output
    assert "UserWarning" not in output

    # New file does not change dirtiness
    write_to_file("foo", "print('hello')")
    output = setup_py_output("--version")
    assert output == "0.1.0"

    # Modify existing file makes checkout dirty
    write_to_file("sample.py", "__version__ = '0.1.0'\nprint('hello')")
    output = setup_py_output("--version")
    assert output == "0.1.0+dirty"

    # git add -> version should still be dirty, as we didn't commit yet
    conftest.run_git("add", "sample.py")
    output = setup_py_output("--version")
    assert output == "0.1.0+dirty"

    # git commit -> version reflects new distance
    conftest.run_git("commit", "-m", "Testing")
    output = setup_py_output("--version")
    assert output == "0.1.1"

    # Bump minor, we should get 0.2.0
    output = setup_py_output("version", "--bump", "minor", "--commit")
    assert "Not pushing bump, use --push to push" in output
    assert "Running: git add sample.py" in output
    assert "Running: git tag -a v0.2.0" in output
    output = setup_py_output("--version")
    assert output == "0.2.0"
    content = Path("sample.py").read_text()
    assert content.startswith("__version__ = '0.2.0'\n")
