from . import conftest

import setupmeta.scm


def test_scm():
    scm = setupmeta.scm.Scm(conftest.resouce())
    assert scm.get_branch() is None
    assert scm.get_version() is None
    assert scm.commit_files(False, None, None) is None
    assert scm.apply_tag(False, None) is None
    assert scm.get_output() is None


def test_git():
    git = conftest.MockGit(describe=None, commitid='abc123')
    assert str(git.get_version()) == 'v0.0.0-1-gabc123'

    with conftest.capture_output() as out:
        git.commit_files(False, [], '2.0')
        assert not out.to_string()

        git.commit_files(False, ['foo'], '2.0')
        assert "Would run" in out
        assert "git add foo" in out
        assert "git commit -m Version 2.0" in out


def test_strip():
    assert setupmeta.scm.strip_dash(None) is None
    assert setupmeta.scm.strip_dash('foo') == 'foo'
    assert setupmeta.scm.strip_dash('--foo-') == 'foo'
