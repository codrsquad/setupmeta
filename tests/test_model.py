import os
import sys

from mock import MagicMock, patch

import setupmeta
from setupmeta.model import Definition, DefinitionEntry, first_word, get_pip, is_setup_py_path, Requirements, RequirementsFile, SetupMeta

from . import conftest


def bogus_project(**attrs):
    return SetupMeta(dict(_setup_py_path="/foo/bar/shouldnotexist/setup.py", **attrs))


def test_first_word():
    assert first_word(None) is None
    assert first_word("") == ""
    assert first_word("FOO bar") == "foo"


def test_setup_py_determination():
    initial = sys.argv[0]
    sys.argv[0] = "foo/setup.py"
    meta = SetupMeta(dict(_setup_py_path=None))
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

    f = RequirementsFile(conftest.resouce("scenarios/disabled/requirements.txt"))
    assert len(f.lines) == 15
    assert str(f.lines[0]) == "chardet==3.0.4"
    assert f.filled_requirements == ["chardet", "requests", "runez", "some-project"]
    assert f.dependency_links == ["git+git://a.b/c/p1.git#egg=runez", "https://a.b/c/p2.git@u/pp", "file:///tmp/bar1", "file:///tmp/bar2"]
    assert f.abstracted == ["chardet  # abstracted by default"]
    assert f.ignored == ["coverage>=5.0  # 'indirect' stated on line"]
    assert f.untouched == ["requests", "runez", "some-project"]

    f = RequirementsFile("".splitlines())
    assert not f.lines
    assert not f.filled_requirements
    assert not f.dependency_links
    assert not f.abstracted

    f = RequirementsFile(None)
    assert not f.lines
    assert not f.filled_requirements
    assert not f.dependency_links
    assert not f.abstracted


def test_empty():
    meta = bogus_project()
    assert not meta.attrs
    assert not meta.definitions
    assert not meta.name
    assert isinstance(meta.requirements, Requirements)
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
    meta = bogus_project(name="pygradle_project")
    assert len(meta.definitions) == 2
    assert meta.value("name") == "pygradle_project"
    assert meta.value("version") == "1.2.3"

    name = meta.definitions["name"]
    version = meta.definitions["version"]

    assert name.is_explicit
    assert not version.is_explicit


def test_meta():
    assert not is_setup_py_path(None)
    assert not is_setup_py_path("")
    assert not is_setup_py_path("foo.py")

    assert is_setup_py_path("/foo/setup.py")
    assert is_setup_py_path("/foo/setup.pyc")


def test_no_pip():
    with conftest.capture_output() as logged:
        # Simulate pip > 20.0
        with patch.dict(
            "sys.modules", {"pip._internal.req": MagicMock(), "pip._internal.download": None, "pip._internal.network.session": MagicMock()}
        ):
            assert len(get_pip()) == 2

        # Simulate 10.0 < pip < 20.0
        with patch.dict(
            "sys.modules", {"pip._internal.req": MagicMock(), "pip._internal.download": MagicMock(), "pip._internal.network.session": None}
        ):
            assert len(get_pip()) == 2

        # Simulate pip < 10.0
        with patch.dict("sys.modules", {"pip._internal": None, "pip.req": MagicMock(), "pip.download": MagicMock()}):
            assert len(get_pip()) == 2

        # Simulate pip not installed at all
        with patch.dict("sys.modules", {"pip": None, "pip._internal.req": None, "pip.req": None}):
            assert get_pip() == (None, None)

        assert "Can't find PipSession" in logged
