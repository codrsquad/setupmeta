import os

import pytest
from . import conftest

import setupmeta
from setupmeta.model import SetupMeta
from setupmeta.scm import Git, Version
import setupmeta.versioning


setupmeta.versioning.warnings.warn = lambda *x: None


def new_meta(versioning, scm=None, setup_py=None, **kwargs):
    setup_py = setup_py or conftest.resouce('setup.py')
    upstream = dict(versioning=versioning, scm=scm, _setup_py_path=setup_py)
    upstream.update(kwargs)
    return SetupMeta(upstream=upstream)


class MockGit(Git):
    def __init__(self, dirty=True, describe='v0.1.2-3-g123', branch='master'):
        self.dirty = dirty
        self.describe = describe
        self.branch = branch
        Git.__init__(self, conftest.resouce())

    def get_output(self, cmd, *args, **kwargs):
        if cmd == 'diff':
            return 1 if self.dirty else 0
        if cmd == 'describe':
            return self.describe
        if cmd == 'rev-parse':
            return self.branch
        assert kwargs.get('dryrun') is True
        return Git.get_output(self, cmd, *args, **kwargs)


def test_disabled():
    meta = new_meta(False)
    versioning = meta.versioning
    assert not versioning.enabled
    assert versioning.problem == "setupmeta versioning not enabled"
    with pytest.raises(Exception):
        versioning.bump('major', commit=False)


def check_render(v, expected, m='1.0', c=None, cid=None, d=False):
    version = Version(main=m, changes=c, commitid=cid, dirty=d)
    assert v.strategy.rendered(version) == expected


def test_no_scm():
    s = 'tag(a,b):{major}.{minor}.{patch}{beta}+?{.$*FOO*}.{$BAR*:}{$BAZ:z}'
    meta = new_meta(s)
    versioning = meta.versioning
    assert versioning.enabled
    assert versioning.problem == "project not under a supported SCM"
    assert meta.version == '0.0.0'
    assert versioning.strategy
    assert versioning.strategy.branches == ['a', 'b']
    assert not versioning.strategy.problem
    check_rep(versioning, extra='?{.$*FOO*}.{$BAR*:}{$BAZ:z}', branches='a,b')
    check_render(versioning, '1.0.0')
    check_render(versioning, '1.0.0b2', c=2)
    check_render(versioning, '1.0.0b2+.z', c=2, d=True)
    os.environ['TEST_FOO1'] = 'bar'
    os.environ['TEST_FOO2'] = 'baz'
    check_render(versioning, '1.0.0b2+.bar.z', c=2, d=True)
    del os.environ['TEST_FOO1']
    del os.environ['TEST_FOO2']
    with pytest.raises(setupmeta.UsageError):
        versioning.bump('patch')


def test_no_extra():
    meta = new_meta('{major}.{minor}+', scm=MockGit(True))
    versioning = meta.versioning
    assert meta.version == '0.1'
    check_rep(versioning, main='{major}.{minor}', extra='')
    check_render(versioning, '1.0')
    check_render(versioning, '1.0', c=2)
    check_render(versioning, '1.0', c=2, d=True)


def check_git(dirty):
    meta = new_meta('changes', scm=MockGit(dirty))
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert not versioning.strategy.problem
    assert 'major' in str(versioning.strategy.main_bits)
    assert 'commitid' in str(versioning.strategy.extra_bits)
    check_rep(versioning, main='{major}.{minor}.{changes}')
    if dirty:
        assert meta.version == '0.1.3+g123'
    else:
        assert meta.version == '0.1.3'

    with conftest.capture_output() as out:
        versioning.bump('major')
        assert "Not committing bump, use --commit to commit" in out
        assert "git tag -a v1.0.0 -m Version 1.0.0" in out
        assert "git push --tags origin master" in out

    with conftest.capture_output() as out:
        versioning.bump('minor')
        assert "Not committing bump, use --commit to commit" in out
        assert "git tag -a v0.2.0 -m Version 0.2.0" in out
        assert "git push --tags origin master" in out

    with pytest.raises(setupmeta.UsageError):
        versioning.bump('patch')

    with pytest.raises(setupmeta.UsageError):
        versioning.bump('foo')


def test_git():
    check_git(True)
    check_git(False)


def check_rep(versioning, **kwargs):
    expected = setupmeta.versioning.Versioning.formatted(**kwargs)
    assert str(versioning.strategy) == expected


def extra_version(version):
    if version.dirty:
        return 'extra'
    if version.changes:
        return 'c%s' % version.changes
    return ''


def test_invalid_part():
    meta = new_meta(
        dict(
            foo='bar',
            main='{foo}.{major}.{minor}{',
            extra=extra_version,
            separator='-',
        ),
        scm=MockGit()
    )
    versioning = meta.versioning
    assert 'invalid' in str(versioning.strategy.main_bits)
    assert meta.version == '0.0.0'
    assert versioning.problem == "invalid versioning part 'foo'"
    check_rep(
        versioning,
        main='{foo}.{major}.{minor}{',
        extra=str(extra_version), separator='-'
    )
    check_render(versioning, 'invalid.1.0')
    check_render(versioning, 'invalid.1.0-c2', c=2)
    check_render(versioning, 'invalid.1.0-extra', c=2, d=True)

    with pytest.raises(setupmeta.UsageError):
        versioning.bump('minor')


def test_invalid_main():
    meta = new_meta(
        dict(
            main=extra_version,
            extra='',
        ),
        scm=MockGit()
    )
    versioning = meta.versioning
    check_rep(versioning, main=extra_version, extra='')
    check_render(versioning, '')
    check_render(versioning, 'c2', c=2)
    check_render(versioning, 'extra', c=2, d=True)
    with pytest.raises(setupmeta.UsageError):
        versioning.bump('minor')


def test_malformed():
    meta = new_meta(
        dict(
            main=None,
            extra='',
        ),
        scm=MockGit()
    )
    versioning = meta.versioning
    assert meta.version is None
    assert not versioning.enabled
    assert not versioning.strategy
    assert versioning.problem == "setupmeta versioning not enabled"
