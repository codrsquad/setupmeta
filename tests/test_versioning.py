import os
import sys

import pep440
import pytest
from mock import patch

import setupmeta
import setupmeta.versioning
from setupmeta.model import SetupMeta
from setupmeta.scm import Version

from . import conftest


def new_meta(versioning, name="just-testing", scm=None, setup_py=None, **kwargs):
    setup_py = setup_py or conftest.resouce("setup.py")
    upstream = dict(versioning=versioning, scm=scm, _setup_py_path=setup_py)
    if name:
        # Allow to test "missing name" case
        upstream["name"] = name

    upstream.update(kwargs)
    return SetupMeta().finalize(upstream=upstream)


def test_deprecated_strategy_notation():
    """Custom separators, and the `!` marker will be removed in the future"""
    with conftest.capture_output() as logged:
        meta = new_meta("post !", scm=conftest.MockGit(True))
        versioning = meta.versioning
        assert str(versioning.strategy) == "branch(main,master):{major}.{minor}.{patch}{post}"
        check_render(versioning, "1.0.0")
        assert "PEP-440 allows only '+' as local" in logged
        assert "'!' character in 'versioning' is now deprecated" in logged

    with conftest.capture_output() as logged:
        meta = new_meta("distance+!foo", scm=conftest.MockGit(True))
        versioning = meta.versioning
        assert str(versioning.strategy) == "branch(main,master):{major}.{minor}.{distance}+foo"
        check_render(versioning, "1.0.0+foo")
        check_render(versioning, "1.0.2+foo", distance=2)
        assert "PEP-440 allows" not in logged
        assert "'!' character in 'versioning' is now deprecated" in logged


def test_disabled():
    with conftest.capture_output():
        meta = new_meta(False)
        versioning = meta.versioning
        assert not versioning.enabled
        assert versioning.problem == "setupmeta versioning not enabled"
        with pytest.raises(Exception):
            versioning.bump("major", commit=False)


def test_project_scm(sample_project):
    assert setupmeta.versioning.find_scm_root(None, ".git") is None
    assert setupmeta.versioning.find_scm_root("", ".git") is None
    assert setupmeta.versioning.find_scm_root("/", ".git") is None

    assert setupmeta.versioning.find_scm_root(".", ".git") == "."
    assert setupmeta.versioning.find_scm_root("./subfolder", ".git") == "."

    assert setupmeta.versioning.find_scm_root(sample_project, ".git") == sample_project
    assert setupmeta.versioning.find_scm_root(os.path.join(sample_project, "subfolder", "foo"), ".git") == sample_project


def test_snapshot_with_version_file():
    with setupmeta.temp_resource() as temp:
        with conftest.capture_output() as logged:
            with open(os.path.join(temp, setupmeta.VERSION_FILE), "w") as fh:
                fh.write("v1.2.3-4-g1234567")

            setup_py = os.path.join(temp, "setup.py")
            meta = SetupMeta().finalize(dict(_setup_py_path=setup_py, name="just-testing", versioning="post", setup_requires="setupmeta"))

            versioning = meta.versioning
            assert meta.version == "1.2.3.post4"
            assert not versioning.generate_version_file
            assert versioning.scm.program is None
            assert str(versioning.scm).startswith("snapshot ")
            assert not versioning.scm.is_dirty()
            assert versioning.scm.get_branch() == "HEAD"

            # Trigger artificial rewriting of version file
            versioning.generate_version_file = True
            versioning.auto_fill_version()
            assert "WARNING: No 'packages' or 'py_modules' defined" in logged


@patch.dict(os.environ, {setupmeta.SCM_DESCRIBE: "1"})
def test_find_scm_in_parent():
    with conftest.capture_output():
        meta = new_meta("post")
        versioning = meta.versioning
        assert versioning.enabled
        assert not versioning.problem
        assert setupmeta.project_path() == conftest.TESTS
        assert versioning.scm.root == conftest.TESTS


def check_render(v, expected, main="1.0", distance=None, cid=None, dirty=False):
    version = Version(main=main, distance=distance, commitid=cid, dirty=dirty)
    assert v.strategy.rendered(version) == expected


@patch("setupmeta.model.project_scm", return_value=None)
def test_no_scm(_, monkeypatch):
    with conftest.capture_output() as logged:
        fmt = "branch(a,b):{major}.{minor}.{patch}{post}+{.$*FOO*}.{$BAR1*:}{$*BAR2:}{$BAZ:z}{dirty}"
        meta = new_meta(fmt)
        versioning = meta.versioning

        assert "project not under a supported SCM" in logged

        assert versioning.enabled
        assert versioning.problem == "project not under a supported SCM"
        assert meta.version == "0.0.0"
        assert versioning.strategy
        assert versioning.strategy.branches == ["a", "b"]
        assert not versioning.strategy.problem

        assert str(versioning.strategy) == fmt
        assert "BAZ:z" in str(versioning.strategy.extra_bits)

        check_render(versioning, "1.0.0+z")
        check_render(versioning, "1.0.0.post2+z", distance=2)
        check_render(versioning, "1.0.0.post2+z.dirty", distance=2, dirty=True)

        monkeypatch.setenv("TEST_FOO1", "bar")
        monkeypatch.setenv("TEST_FOO2", "baz")
        check_render(versioning, "1.0.0.post2+bar.z.dirty", distance=2, dirty=True)

        with pytest.raises(setupmeta.UsageError):
            versioning.bump("patch")


@patch.dict(os.environ, {setupmeta.SCM_DESCRIBE: "v1.2.3-4-g1234567-dirty"})
@patch("setupmeta.versioning.find_scm_root", return_value=None)
def test_version_from_env_var(*_):
    with conftest.capture_output():
        meta = new_meta("post")
        versioning = meta.versioning
        assert meta.version == "1.2.3.post4+dirty"
        assert versioning.enabled
        assert not versioning.generate_version_file
        assert not versioning.problem
        assert versioning.scm.is_dirty()


def quick_check(versioning, expected, dirty=True, describe="v0.1.2-5-g123", compliant=True):
    meta = new_meta(versioning, scm=conftest.MockGit(dirty, describe=describe))
    assert meta.version == expected
    if compliant:
        main_part, _, _ = meta.version.partition("+")
        assert pep440.is_canonical(main_part)

    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.generate_version_file
    assert not versioning.problem
    assert versioning.scm.is_dirty() == dirty


@patch.dict(os.environ, {"BUILD_ID": "543"})
def test_versioning_variants(*_):
    with conftest.capture_output() as logged:
        quick_check("{major}.{minor}", "0.1+dirty")
        quick_check("{major}.{minor}+", "0.1")
        quick_check("{major}.{minor}{dirty}", "0.1+dirty")
        quick_check("{major}.{minor}{dirty}+", "0.1+dirty")
        quick_check("{major}.{minor}", "0.1", dirty=False)
        quick_check("{major}.{minor}+", "0.1", dirty=False)
        quick_check("{major}.{minor}+", "0.1", dirty=True)

        quick_check("distance", "0.1.5+dirty")
        quick_check("post", "0.1.2.post5+dirty")
        quick_check("dev", "0.1.3.dev5+dirty")
        quick_check("devcommit", "0.1.3.dev5+g123.dirty")

        # Old allowed notations, should remove eventually
        quick_check("dev+build-id", "0.1.3.dev5+h543.g123.dirty")
        quick_check("post+build-id", "0.1.2.post5+h543.g123.dirty")

        # Aliases
        quick_check("changes", "0.1.5+dirty")
        quick_check("default", "0.1.2.post5+dirty")
        quick_check("tag", "0.1.2.post5+dirty")

        # Edge cases
        quick_check("1.2.3", "1.2.3+dirty")
        quick_check("foo", "foo+dirty", compliant=False)

        quick_check("dev+{commitid}{dirty}", "0.1.3.dev5+g123.dirty")
        quick_check("dev+{commitid}{dirty}", "0.1.3.dev0+g123.dirty", describe="v0.1.2-0-g123")
        quick_check("dev+{commitid}{dirty}", "0.1.2+g123", describe="v0.1.2-0-g123", dirty=False)

        quick_check("dev+devcommit", "0.1.3.dev5+g123.dirty")
        quick_check("dev+devcommit", "0.1.3.dev0+g123.dirty", describe="v0.1.2-0-g123")
        quick_check("dev+devcommit", "0.1.2", describe="v0.1.2-0-g123", dirty=False)

        quick_check("post+devcommit", "0.1.2.post5+g123.dirty")
        quick_check("post+devcommit", "0.1.2+g123.dirty", describe="v0.1.2-0-g123")
        quick_check("post+devcommit", "0.1.2", describe="v0.1.2-0-g123", dirty=False)

        quick_check("dev", "0.1.9rc1", dirty=False, describe="v0.1.9-rc.1-0-gebe2789")
        quick_check("devcommit", "0.1.9rc1", dirty=False, describe="v0.1.9-rc.1-0-gebe2789")
        quick_check("post", "0.1.9rc1+dirty", dirty=True, describe="v0.1.9-rc.1-0-gebe2789")

        quick_check("dev", "0.1.9rc1.dev1", dirty=False, describe="v0.1.9-rc.1-1-gebe2789")
        quick_check("devcommit", "0.1.9rc1.dev1+gebe2789", dirty=False, describe="v0.1.9-rc.1-1-gebe2789")
        quick_check("devcommit", "0.1.9rc1.dev1+gebe2789.dirty", dirty=True, describe="v0.1.9-rc.1-1-gebe2789")
        quick_check("post", "0.1.9rc1.post1", dirty=False, describe="v0.1.9-rc.1-1-gebe2789")

        quick_check("devcommit", "0.1.3.dev5+g123", dirty=False)
        quick_check("devcommit", "0.1.3.dev5+g123.dirty")
        quick_check("build-id", "0.1.5+h543.g123.dirty")

        quick_check("post", "5.0.0a1.post1", dirty=False, describe="v5.0-a.1-1-gebe2789")
        quick_check("post", "5.0.0a1.rc2.post7", dirty=False, describe="v5.a1rc2-7-gebe2789", compliant=False)
        quick_check("dev", "0.1.0a0.dev8", dirty=False, describe="v0.1.a-8-gebe2789")

        # Patch is not bumpable
        quick_check("dev", "0.1.0rc0.dev5+dirty", describe="v0.1.rc-5-g123")
        quick_check("dev", "0.1.0rc1.dev5+dirty", describe="v0.1.rc1-5-g123")
        quick_check("dev", "0.1.0rc1.dev5+dirty", describe="v0.1.rc.1-5-g123")
        quick_check("dev", "0.1.0rc1.dev5+dirty", describe="v0.1.rc-1-5-g123")

        # On tag
        quick_check("dev", "0.1.2", describe="v0.1.2-0-g123", dirty=False)
        quick_check("dev", "0.1.3.dev0+dirty", describe="v0.1.2-0-g123", dirty=True)
        quick_check("devcommit", "0.1.2", describe="v0.1.2", dirty=False)
        quick_check("devcommit", "0.1.2", describe="v0.1.2-0-g123", dirty=False)
        quick_check("devcommit", "0.1.3.dev7+g123", describe="v0.1.2-7-g123", dirty=False)
        quick_check("devcommit", "0.1.3.dev0+g123.dirty", describe="v0.1.2-0-g123", dirty=True)

        assert "patch version component should be .0" in logged


def test_bump_patch():
    with conftest.capture_output() as logged:
        meta = new_meta("post", scm=conftest.MockGit(False, describe="v0.1.2.rc-5-g123"))
        versioning = meta.versioning
        versioning.bump("patch")
        assert "Would run: git tag -a v0.1.3" in logged
        assert "Not committing" in logged
        assert "Not pushing" in logged


def test_no_extra():
    with conftest.capture_output() as logged:
        meta = new_meta("{major}.{minor}+", scm=conftest.MockGit(True))
        versioning = meta.versioning
        assert str(versioning.strategy) == "branch(main,master):{major}.{minor}"
        check_render(versioning, "1.0")
        check_render(versioning, "1.0", distance=2)
        check_render(versioning, "1.0", distance=2, dirty=True)

        meta = new_meta("{major}.{minor}.{$FOO}+", scm=conftest.MockGit(True))
        versioning = meta.versioning
        assert meta.version == "0.1+None"
        assert str(versioning.strategy) == "branch(main,master):{major}.{minor}+{$FOO}"
        check_render(versioning, "1.0+None")
        check_render(versioning, "1.0+None", distance=2)
        check_render(versioning, "1.0+None", distance=2, dirty=True)

        assert "patch version component should be .0" in logged


def extra_version(version):
    if version.dirty:
        return "extra"

    if version.distance:
        return "d%s" % version.distance

    return ""


def test_invalid_part():
    with conftest.capture_output() as logged:
        versioning = dict(foo="bar", main="{foo}.{major}.{minor}{", extra=extra_version)
        meta = new_meta(versioning, scm=conftest.MockGit())
        versioning = meta.versioning
        assert "invalid" in str(versioning.strategy.main_bits)
        assert meta.version is None
        assert versioning.problem == "invalid versioning part 'foo'"
        assert str(versioning.strategy) == "branch(main,master):{foo}.{major}.{minor}{+function 'extra_version'"
        check_render(versioning, "invalid.1.0")
        check_render(versioning, "invalid.1.0+d2", distance=2)
        check_render(versioning, "invalid.1.0+extra", distance=2, dirty=True)

        assert "Ignored fields for 'versioning': {'foo': 'bar'}" in logged

        with pytest.raises(setupmeta.UsageError):
            versioning.bump("minor")

        with pytest.raises(setupmeta.UsageError):
            versioning.get_bump("minor")


def test_invalid_main():
    with conftest.capture_output() as logged:
        meta = new_meta(dict(main=extra_version, extra=""), scm=conftest.MockGit())
        versioning = meta.versioning
        assert str(versioning.strategy) == "branch(main,master):function 'extra_version'"
        check_render(versioning, "")
        check_render(versioning, "d2", distance=2)
        check_render(versioning, "extra", distance=2, dirty=True)
        with pytest.raises(setupmeta.UsageError):
            versioning.bump("minor")

        assert "you have pending changes" in logged


def test_malformed():
    with conftest.capture_output() as logged:
        meta = new_meta(dict(main=None, extra=""), name=None, scm=conftest.MockGit())
        versioning = meta.versioning
        assert meta.version is None
        assert not versioning.enabled
        assert versioning.problem == "No versioning format specified"
        assert "WARNING: 'name' not specified in setup.py" in logged


def test_distance_marker():
    with conftest.capture_output():
        meta = new_meta("{major}.{minor}.{distance}", scm=conftest.MockGit())
        versioning = meta.versioning
        assert versioning.enabled
        assert not versioning.problem
        assert not versioning.strategy.problem
        assert meta.version == "0.1.3+dirty"
        assert str(versioning.strategy) == "branch(main,master):{major}.{minor}.{distance}+{dirty}"


def test_preconfigured_build_id():
    """Verify that short notations expand to the expected format"""
    check_preconfigured("branch(main,master):{major}.{minor}.{patch}{post}+{dirty}", "post", "default", "tag")
    check_preconfigured("branch(main,master):{major}.{minor}.{distance}+{dirty}", "distance", "changes")
    check_preconfigured("branch(main,master):{major}.{minor}.{distance}+h{$*BUILD_ID:local}.{commitid}{dirty}", "build-id")
    check_preconfigured("branch(main,master):{major}.{minor}.{patch}{dev}+h{$*BUILD_ID:local}.{commitid}{dirty}", "dev+build-id")
    check_preconfigured("branch(main,master):{major}.{minor}.{patch}{post}+h{$*BUILD_ID:local}.{commitid}{dirty}", "post+build-id")


def check_preconfigured(expected, *shorts):
    with conftest.capture_output():
        for short in shorts:
            meta = new_meta(short, scm=conftest.MockGit())
            versioning = meta.versioning
            assert versioning.enabled
            assert not versioning.problem
            assert not versioning.strategy.problem
            assert str(versioning.strategy) == expected


@patch.dict(os.environ, {"BUILD_ID": "543"})
def test_preconfigured_strategies(*_):
    with conftest.capture_output():
        check_strategy_distance(True)
        check_strategy_distance(False)
        check_strategy_build_id(True)
        check_strategy_build_id(False)


def check_strategy_distance(dirty):
    meta = new_meta("distance", scm=conftest.MockGit(dirty))
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert not versioning.strategy.problem
    assert "major" in str(versioning.strategy.main_bits)
    assert "dirty" in str(versioning.strategy.extra_bits)
    assert str(versioning.strategy) == "branch(main,master):{major}.{minor}.{distance}+{dirty}"
    if dirty:
        assert meta.version == "0.1.3+dirty"

        with pytest.raises(setupmeta.UsageError):
            # Can't effectively bump if checkout is dirty
            versioning.bump("minor", commit=True)

    else:
        assert meta.version == "0.1.3"

    with pytest.raises(setupmeta.UsageError):
        # Can't bump 'patch' with 'distance' format
        versioning.bump("patch")

    check_bump(versioning)


def check_strategy_build_id(dirty):
    meta = new_meta("build-id", scm=conftest.MockGit(dirty))
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert not versioning.strategy.problem
    assert "major" in str(versioning.strategy.main_bits)
    assert "commitid" in str(versioning.strategy.extra_bits)
    assert str(versioning.strategy) == "branch(main,master):{major}.{minor}.{distance}+h{$*BUILD_ID:local}.{commitid}{dirty}"
    if dirty:
        assert meta.version == "0.1.3+h543.g123.dirty"

        with pytest.raises(setupmeta.UsageError):
            # Can't effectively bump when checkout is dirty
            versioning.bump("minor", commit=True)

    else:
        assert meta.version == "0.1.3+h543.g123"

    check_bump(versioning)


def check_bump(versioning):
    with conftest.capture_output() as logged:
        versioning.bump("major")
        assert "Not committing bump, use --commit to commit" in logged
        assert 'git tag -a v1.0.0 -m "Version 1.0.0"' in logged

    with conftest.capture_output() as logged:
        versioning.bump("minor", push=True)
        assert "Not committing bump, use --commit to commit" in logged
        assert 'git tag -a v0.2.0 -m "Version 0.2.0"' in logged
        assert "git push --tags origin" in logged

    with pytest.raises(setupmeta.UsageError):
        versioning.bump("foo")


def check_get_bump(versioning):
    assert versioning.get_bump("major") == "1.0.0"
    assert versioning.get_bump("minor") == "0.2.0"

    with pytest.raises(setupmeta.UsageError):
        versioning.get_bump("foo")


def write_to_file(path, text):
    with open(path, "w") as fh:
        fh.write(text)
        fh.write("\n")


SAMPLE_EMPTY_PROJECT = """
from setuptools import setup
setup(
    name='testing',
    py_modules=['foo'],
    setup_requires='setupmeta',
    versioning='distance',
)
"""


def check_version_output(expected):
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture="all")
    output = conftest.cleaned_output(output)
    assert output == expected


def test_brand_new_project():
    with setupmeta.temp_resource():
        conftest.run_git("init")
        with open("setup.py", "w") as fh:
            fh.write(SAMPLE_EMPTY_PROJECT)

        # Test that we avoid warning about no tags etc on brand new empty git repos
        check_version_output("0.0.0")

        # Now stage a file
        conftest.run_git("add", "setup.py")
        check_version_output("0.0.0+dirty")

        # Unstage it
        conftest.run_git("reset", "setup.py")
        check_version_output("0.0.0")

        # Commit it, and touch a new file
        conftest.run_git("add", "setup.py")
        conftest.run_git("commit", "-m", "Initial commit")
        with open("foo", "w") as fh:
            fh.write("foo\n")

        check_version_output("0.0.1")


def test_git_versioning(sample_project):
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.0.1"

    # Bump with no initial tags shouldn't warn
    output = setupmeta.run_program(sys.executable, "setup.py", "version", "--bump", "minor", capture="all")
    assert "UserWarning" not in output
    assert "Would run: git tag -a v0.1.0" in output

    conftest.run_git("tag", "-a", "v0.1.0", "-m", "Version 2.4.2")
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.1.0"

    output = setupmeta.run_program(sys.executable, "setup.py", "explain", capture="all")
    assert "0.1.0" in output
    assert "UserWarning" not in output

    # New file does not change dirtiness
    write_to_file("foo", "print('hello')")
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.1.0"

    # Modify existing file makes checkout dirty
    write_to_file("sample.py", "print('hello')")
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.1.0+dirty"

    # git add -> version should still be dirty, as we didn't commit yet
    conftest.run_git("add", "sample.py")
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.1.0+dirty"

    # git commit -> version reflects new distance
    conftest.run_git("commit", "-m", "Testing")
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.1.1"

    # Bump minor, we should get 0.2.0
    output = setupmeta.run_program(sys.executable, "setup.py", "version", "--bump", "minor", "--commit", capture=True)
    assert "Not pushing bump, use --push to push" in output
    assert "Running: git tag -a v0.2.0" in output
    output = setupmeta.run_program(sys.executable, "setup.py", "--version", capture=True)
    assert output == "0.2.0"


def test_missing_tags():
    with conftest.capture_output() as logged:
        meta = new_meta("distance", scm=conftest.MockGit(False, local_tags="v1.0\nv1.1", remote_tags="v1.0\nv2.0"))
        versioning = meta.versioning
        assert versioning.enabled
        assert not versioning.problem
        assert not versioning.strategy.problem
        with pytest.raises(setupmeta.UsageError):
            # Can't effectively bump when remote tags are not all present locally
            versioning.bump("minor", commit=True)
        assert "patch version component should be .0" in logged
