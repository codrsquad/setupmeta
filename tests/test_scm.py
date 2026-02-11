import pytest

import setupmeta.scm

from . import conftest


def test_scm():
    scm = setupmeta.scm.Scm(conftest.TESTS)
    assert scm.get_branch() is None
    assert scm.get_version() is None
    assert scm.commit_files(False, False, None, "") is None
    assert scm.apply_tag(False, False, "", "main") is None


def test_git():
    git = conftest.MockGit(describe="", commitid="abc123")
    assert str(git.get_version()) == "v0.0.0-1-gabc123"

    with conftest.capture_output() as out:
        git.commit_files(False, False, [], "2.0")
        assert not str(out)

        git.commit_files(False, True, ["foo"], "2.0")
        assert out.pop() == 'Would run: git add foo\nWould run: git commit -m "Version 2.0" --no-verify\nWould run: git push origin'
        git.apply_tag(False, True, "2.0", "main")
        assert out.pop() == 'Would run: git fetch --all\nWould run: git tag -a v2.0 -m "Version 2.0"\nWould run: git push --tags origin'

        with pytest.raises(SystemExit):
            git.apply_tag(True, True, "2.0", "main")

        assert out.pop() == "chatty stderr\ngit push --tags origin exited with code 1:\noops push failed"

        report = git.get_diff_report()
        assert report == "some diff stats"
        assert out.pop() == "WARNING: git diff --stat exited with code 1, stderr:\noops something happened"

    git._has_origin = ""
    with conftest.capture_output() as out:
        git.commit_files(False, False, [], "2.0")
        assert not str(out)

        git.commit_files(False, True, ["foo"], "2.0")
        assert "Won't push: no origin defined" in out.pop()
        git.apply_tag(False, True, "2.0", "main")
        assert "Would run: git push " not in out
        assert "Not running 'git push --tags origin' as you don't have an origin" in out.pop()

    git._has_origin = True
    git.status_message = "## main...origin/main [behind 1]"
    with pytest.raises(setupmeta.UsageError, match="branch 'main' is out of date"):
        git.apply_tag(False, True, "2.0", "main")


def test_git_describe_override(monkeypatch):
    monkeypatch.setenv("SETUPMETA_GIT_DESCRIBE_COMMAND", "describe foo")

    # `git describe` returned garbage, fall back to 'git rev-parse' etc.
    git = conftest.MockGit(describe="foo", commitid="abc")
    v = git.get_version()
    assert v.text == "v0.0.0-1-gabc"
    assert v.main_text == "0.0.0"
    assert v.distance == 1
    assert v.commitid == "gabc"

    # If SETUPMETA_GIT_DESCRIBE_COMMAND led to proper output, verify it does get used
    git = conftest.MockGit(describe="v1.2.3-4-gabc123-dirty")
    v = git.get_version()
    assert v.text == "v1.2.3-4-gabc123-dirty"
    assert v.main_text == "1.2.3"
    assert v.distance == 4
    assert v.commitid == "gabc123"
