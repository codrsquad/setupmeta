import pytest

import setupmeta.scm

from . import conftest


def test_scm():
    scm = setupmeta.scm.Scm(conftest.TESTS)
    assert scm.get_branch() is None
    assert scm.get_version() is None
    assert scm.commit_files(False, False, None, "") is None
    assert scm.apply_tag(False, False, "", "master") is None
    assert scm.get_output() is None


def test_git():
    git = conftest.MockGit(describe=None, commitid="abc123")
    assert str(git.get_version()) == "v0.0.0-1-gabc123"

    with conftest.capture_output() as out:
        git.commit_files(False, False, [], "2.0")
        assert not str(out)

        git.commit_files(False, True, ["foo"], "2.0")
        git.apply_tag(False, True, "2.0", "master")
        assert "Would run: git add foo" in out
        assert 'Would run: git commit -m "Version 2.0"' in out
        assert "Would run: git push origin" in out
        assert 'Would run: git tag -a v2.0 -m "Version 2.0"' in out
        assert "Would run: git push --tags origin" in out

    git._has_origin = ""
    with conftest.capture_output() as out:
        git.commit_files(False, False, [], "2.0")
        assert not str(out)

        git.commit_files(False, True, ["foo"], "2.0")
        git.apply_tag(False, True, "2.0", "master")
        assert "Would run: git add foo" in out
        assert 'Would run: git commit -m "Version 2.0"' in out
        assert 'Would run: git tag -a v2.0 -m "Version 2.0"' in out
        assert "Not running 'git push --tags origin' as you don't have an origin" in out

        assert "Would run: git push origin" not in out
        assert "Would run: git push --tags origin" not in out

    git._has_origin = True
    git.status_message = "## master...origin/master [behind 1]"
    with pytest.raises(setupmeta.UsageError):
        git.apply_tag(False, True, "2.0", "master")


def test_ignore_git_failures():
    assert setupmeta._should_ignore_run_fail("git", ["rev-list", "HEAD"], "ambiguous argument 'HEAD': unknown revision or path")
    assert setupmeta._should_ignore_run_fail("git", ["describe"], "fatal: no names found, cannot describe anything.")
