import os
import sys

from mock import patch

import setupmeta
from setupmeta.model import Definition, DefinitionEntry, is_setup_py_path

from . import conftest


def test_first_word():
    assert setupmeta.relative_path(None) is None
    assert setupmeta.relative_path("") == ""
    assert setupmeta.relative_path("foo") == "foo"

    assert setupmeta.first_word(None) is None
    assert setupmeta.first_word("") is None
    assert setupmeta.first_word("  \n \t ") is None
    assert setupmeta.first_word("  \n \t foo[bar]") == "foo"
    assert setupmeta.first_word("FOO bar") == "foo"
    assert setupmeta.first_word(" FOO, bar") == "foo"
    assert setupmeta.first_word("123") == "123"


def test_setup_py_determination():
    with conftest.capture_output():
        initial = sys.argv[0]
        sys.argv[0] = "foo/setup.py"
        with conftest.TestMeta() as meta:
            assert not meta.definitions
            assert not meta.version
            sys.argv[0] = initial


def test_representation():
    e = DefinitionEntry("foo", "bar", "inlined")
    assert str(e) == "foo=bar from inlined"

    alpha1 = Definition("alpha")
    alpha2 = Definition("alpha")
    alpha2.add("foo", "inlined")
    assert str(alpha1) == "alpha=None from 0 sources"
    assert str(alpha2) == "alpha=foo from inlined"

    beta = Definition("beta")
    assert str(beta) == "beta=None from 0 sources"
    beta.add("foo1", "inlined1")
    assert str(beta) == "beta=foo1 from inlined1"
    beta.add("foo2", "inlined2")
    assert str(beta) == "beta=foo1 from 2 sources"
    beta.add("foo3", "inlined3", override=True)
    assert str(beta) == "beta=foo3 from 3 sources"

    assert alpha1 == alpha2
    assert alpha1 != beta
    assert not alpha1 < alpha2
    assert alpha1 < beta
    assert not alpha1 > beta


def test_requirements():
    assert setupmeta.pkg_req(None) is None
    assert setupmeta.pkg_req("#foo") is None

    assert setupmeta.requirements_from_file("/dev/null/foo") is None

    sample = conftest.resouce("scenarios/disabled/requirements.txt")
    f = setupmeta.RequirementsFile.from_file(sample)
    assert len(f.reqs) == 6
    assert str(f.reqs[0]) == "wheel from tests/scenarios/disabled/requirements.txt:2, abstracted by default"
    assert str(f.reqs[4]) == "-e git://example.com/p1.git#egg=flake8 from tests/scenarios/disabled/requirements.txt:12"
    assert f.filled_requirements == [
        "wheel",
        "click; python_version >= '3.6'",
        "setuptools",
        "git://example.com/p1.git#egg=flake8",
        "pytest-cov @ https://example.com/a.git@u/pp",
    ]

    assert len(f.abstracted) == 2
    assert len(f.ignored) == 1
    assert len(f.untouched) == 3

    sample = conftest.resouce("scenarios/complex-reqs/requirements.in")
    f = setupmeta.RequirementsFile.from_file(sample)
    assert len(f.reqs) == 5

    fr = setupmeta.requirements_from_file(sample)
    assert fr == f.filled_requirements

    sample = "a==1.0\nb; python_version >= '3.6'"
    f = setupmeta.RequirementsFile()
    f.scan(sample.splitlines())
    f.finalize()
    assert len(f.reqs) == 2
    assert f.filled_requirements == ["a", "b; python_version >= '3.6'"]
    assert len(f.abstracted) == 1
    assert len(f.ignored) == 0
    assert len(f.untouched) == 1

    fr = setupmeta.requirements_from_text(sample)
    assert fr == f.filled_requirements

    f = setupmeta.RequirementsFile()
    f.scan([])
    f.finalize()
    assert f.reqs == []
    assert f.filled_requirements == []
    assert f.abstracted == []


def test_empty():
    with conftest.capture_output():
        with conftest.TestMeta(setup="/dev/null/shouldnotexist/setup.py") as meta:
            assert not meta.attrs
            assert not meta.definitions
            assert not meta.name
            assert isinstance(meta.requirements, setupmeta.Requirements)
            assert not meta.requirements.install_requires
            assert not meta.requirements.tests_require
            assert not meta.version
            assert not meta.versioning.enabled
            assert meta.versioning.problem == "setupmeta versioning not enabled"
            assert not meta.versioning.scm
            assert not meta.versioning.strategy
            assert str(meta).startswith("0 definitions, ")


@patch.dict(os.environ, {"PYGRADLE_PROJECT_VERSION": "1.2.3"})
def test_pygradle_version():
    with conftest.capture_output() as logged:
        with conftest.TestMeta(setup="/dev/null/shouldnotexist/setup.py", name="pygradle_project") as meta:
            assert len(meta.definitions) == 2
            assert meta.value("name") == "pygradle_project"
            assert meta.value("version") == "1.2.3"

            name = meta.definitions["name"]
            version = meta.definitions["version"]

            assert name.is_explicit
            assert not version.is_explicit
            assert "WARNING: No 'packages' or 'py_modules' defined" in logged


def test_meta():
    assert not is_setup_py_path(None)
    assert not is_setup_py_path("")
    assert not is_setup_py_path("foo.py")

    assert is_setup_py_path("/foo/setup.py")
    assert is_setup_py_path("/foo/setup.pyc")


def test_standard_req():
    assert setupmeta.standard_req("foo-bar") == "foo-bar"
    assert setupmeta.standard_req("foo==1.0") == "foo==1.0"

    assert setupmeta.standard_req("file://foo") is None
    assert setupmeta.standard_req("/dev/null") is None
    assert setupmeta.standard_req("42-foo") is None
    assert setupmeta.standard_req(".foo") is None
    assert setupmeta.standard_req(".") is None
    assert setupmeta.standard_req("") is None
