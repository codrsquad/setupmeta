import os

import pytest
from mock import patch

import setupmeta
import setupmeta.versioning
from setupmeta.model import SetupMeta
from setupmeta.scm import Version

from . import conftest


setupmeta.versioning.warnings.warn = lambda *_, **__: None


def new_meta(versioning, scm=None, setup_py=None, **kwargs):
    setup_py = setup_py or conftest.resouce('setup.py')
    upstream = dict(versioning=versioning, scm=scm, _setup_py_path=setup_py)
    upstream.update(kwargs)
    return SetupMeta(upstream=upstream)


def test_disabled():
    meta = new_meta(False)
    versioning = meta.versioning
    assert not versioning.enabled
    assert versioning.problem == "setupmeta versioning not enabled"
    with pytest.raises(Exception):
        versioning.bump('major', commit=False)


def test_project_scm():
    assert setupmeta.versioning.find_scm_root(None, 'git') is None
    assert setupmeta.versioning.find_scm_root("", 'git') is None
    assert setupmeta.versioning.find_scm_root("/", 'git') is None
    assert setupmeta.versioning.find_scm_root(conftest.TESTS, 'git') == conftest.PROJECT_DIR
    assert setupmeta.versioning.find_scm_root(conftest.resouce('scenarios', 'complex', 'src', 'complex'), 'git') == conftest.PROJECT_DIR


def test_snapshot():
    with setupmeta.temp_resource() as temp:
        with open(os.path.join(temp, setupmeta.VERSION_FILE), 'w') as fh:
            fh.write('v1.2.3-4-g1234567')

        setup_py = os.path.join(temp, 'setup.py')
        meta = SetupMeta(dict(_setup_py_path=setup_py, versioning='post', setup_requires='setupmeta'))
        versioning = meta.versioning
        assert meta.version == '1.2.3.post4'
        assert not versioning.generate_version_file

        assert versioning.scm.program is None
        assert str(versioning.scm).startswith('snapshot ')
        assert not versioning.scm.is_dirty()
        assert versioning.scm.get_branch() == 'HEAD'

        # Trigger artificial rewriting of version file
        versioning.generate_version_file = True
        versioning.auto_fill_version()


@patch.dict(os.environ, {setupmeta.SCM_DESCRIBE: '1'})
def test_find_scm_in_parent():
    meta = new_meta('post')
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert setupmeta.project_path() == conftest.TESTS
    assert versioning.scm.root == conftest.PROJECT_DIR


def check_render(v, expected, main='1.0', distance=None, cid=None, dirty=False):
    version = Version(main=main, distance=distance, commitid=cid, dirty=dirty)
    assert v.strategy.rendered(version) == expected


@patch('setupmeta.versioning.project_scm', return_value=None)
def test_no_scm(_):
    fmt = "branch(a,b):{major}.{minor}.{patch}{post} !{.$*FOO*}.{$BAR1*:}{$*BAR2:}{$BAZ:z}{dirty}"
    meta = new_meta(fmt)
    versioning = meta.versioning

    assert versioning.enabled
    assert versioning.problem == "project not under a supported SCM"
    assert meta.version == '0.0.0'
    assert versioning.strategy
    assert versioning.strategy.branches == ['a', 'b']
    assert not versioning.strategy.problem

    assert str(versioning.strategy) == fmt
    assert 'BAZ:z' in str(versioning.strategy.extra_bits)

    check_render(versioning, '1.0.0.z')
    check_render(versioning, '1.0.0.post2.z', distance=2)
    check_render(versioning, '1.0.0.post2.z.dirty', distance=2, dirty=True)

    os.environ['TEST_FOO1'] = 'bar'
    os.environ['TEST_FOO2'] = 'baz'
    check_render(versioning, '1.0.0.post2.bar.z.dirty', distance=2, dirty=True)
    del os.environ['TEST_FOO1']
    del os.environ['TEST_FOO2']

    with pytest.raises(setupmeta.UsageError):
        versioning.bump('patch')


@patch.dict(os.environ, {setupmeta.SCM_DESCRIBE: 'v1.2.3-4-g1234567-dirty'})
@patch('setupmeta.versioning.find_scm_root', return_value=None)
def test_version_from_env_var(*_):
    meta = new_meta('post')
    versioning = meta.versioning
    assert meta.version == '1.2.3.post4+g1234567'
    assert versioning.enabled
    assert not versioning.generate_version_file
    assert not versioning.problem
    assert versioning.scm.is_dirty()


def quick_check(versioning, expected, dirty=True, describe='v0.1.2-5-g123'):
    meta = new_meta(versioning, scm=conftest.MockGit(dirty, describe=describe))
    assert meta.version == expected
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.generate_version_file
    assert not versioning.problem
    assert versioning.scm.is_dirty() == dirty


def test_versioning_variants():
    quick_check("{major}.{minor}", "0.1+g123")
    quick_check("{major}.{minor}+", "0.1")
    quick_check("{major}.{minor}{dirty}", "0.1.dirty+g123")
    quick_check("{major}.{minor}{dirty}+", "0.1.dirty")
    quick_check("{major}.{minor}", "0.1", dirty=False)

    quick_check("distance", "0.1.5+g123")
    quick_check("post", "0.1.2.post5+g123")
    quick_check("dev", "0.1.3.dev5+g123")
    quick_check("tag+dev", "0.1.3.dev5+g123")
    quick_check("build-id", "0.1.5+hlocal.g123.dirty")
    quick_check("dev+build-id", "0.1.3.dev5+hlocal.g123.dirty")

    # Patch is not bumpable
    quick_check("dev", "0.1.rc.dev5+g123", describe='v0.1.rc-5-g123')

    # On tag
    quick_check("dev", "0.1.2", describe='v0.1.2-0-g123', dirty=False)
    quick_check("dev", "0.1.3.dev0+g123", describe='v0.1.2-0-g123', dirty=True)


def test_no_extra():
    meta = new_meta('{major}.{minor}.{$FOO}+', scm=conftest.MockGit(True))
    versioning = meta.versioning
    assert meta.version == '0.1.None'
    assert str(versioning.strategy) == "branch(master):{major}.{minor}.{$FOO}+"
    check_render(versioning, '1.0.None')
    check_render(versioning, '1.0.None', distance=2)
    check_render(versioning, '1.0.None', distance=2, dirty=True)


def extra_version(version):
    if version.dirty:
        return 'extra'
    if version.distance:
        return 'd%s' % version.distance
    return ''


def test_invalid_part():
    versioning = dict(foo='bar', main='{foo}.{major}.{minor}{', extra=extra_version, separator='-',)
    meta = new_meta(versioning, scm=conftest.MockGit())
    versioning = meta.versioning
    assert 'invalid' in str(versioning.strategy.main_bits)
    assert meta.version is None
    assert versioning.problem == "invalid versioning part 'foo'"
    assert str(versioning.strategy) == "branch(master):{foo}.{major}.{minor}{-function 'extra_version'"
    check_render(versioning, 'invalid.1.0')
    check_render(versioning, 'invalid.1.0-d2', distance=2)
    check_render(versioning, 'invalid.1.0-extra', distance=2, dirty=True)

    with pytest.raises(setupmeta.UsageError):
        versioning.bump('minor')


def test_invalid_main():
    meta = new_meta(dict(main=extra_version, extra='', separator=' '), scm=conftest.MockGit())
    versioning = meta.versioning
    assert str(versioning.strategy) == "branch(master):function 'extra_version' "
    check_render(versioning, '')
    check_render(versioning, 'd2', distance=2)
    check_render(versioning, 'extra', distance=2, dirty=True)
    with pytest.raises(setupmeta.UsageError):
        versioning.bump('minor')


def test_malformed():
    meta = new_meta(dict(main=None, extra=''), scm=conftest.MockGit())
    versioning = meta.versioning
    assert meta.version is None
    assert not versioning.enabled
    assert versioning.problem == "No versioning format specified"


def test_distance_marker():
    meta = new_meta('{major}.{minor}.{distance}', scm=conftest.MockGit())
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert not versioning.strategy.problem
    assert meta.version == '0.1.3+g123'
    assert str(versioning.strategy) == "branch(master):{major}.{minor}.{distance}+{commitid}"


def test_preconfigured_build_id():
    """Verify that short notations expand to the expected format"""
    check_preconfigured(
        "branch(master):{major}.{minor}.{patch}{post}+{commitid}",
        "post",
        "default",
    )

    check_preconfigured(
        "branch(master):{major}.{minor}.{distance}+{commitid}",
        "distance",
    )

    check_preconfigured(
        "branch(master):{major}.{minor}.{distance}+!h{$*BUILD_ID:local}.{commitid}{dirty}",
        "build-id",
        "distance+build-id",
    )

    check_preconfigured(
        "branch(master):{major}.{minor}.{patch}{post}+!h{$*BUILD_ID:local}.{commitid}{dirty}",
        "+build-id",
        "default+build-id",
        "post+build-id",
    )


def check_preconfigured(expected, *shorts):
    for short in shorts:
        meta = new_meta(short, scm=conftest.MockGit())
        versioning = meta.versioning
        assert versioning.enabled
        assert not versioning.problem
        assert not versioning.strategy.problem
        assert str(versioning.strategy) == expected


@patch.dict(os.environ, {'BUILD_ID': '543'})
def test_preconfigured_strategies():
    check_strategy_distance(True)
    check_strategy_distance(False)
    check_strategy_build_id(True)
    check_strategy_build_id(False)


def check_strategy_distance(dirty):
    meta = new_meta('distance', scm=conftest.MockGit(dirty))
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert not versioning.strategy.problem
    assert 'major' in str(versioning.strategy.main_bits)
    assert 'commitid' in str(versioning.strategy.extra_bits)
    assert str(versioning.strategy) == "branch(master):{major}.{minor}.{distance}+{commitid}"
    if dirty:
        assert meta.version == '0.1.3+g123'

        with pytest.raises(setupmeta.UsageError):
            # Can't effectively bump if checkout is dirty
            versioning.bump('minor', commit=True)

    else:
        assert meta.version == '0.1.3'

    with pytest.raises(setupmeta.UsageError):
        # Can't bump 'patch' with 'distance' format
        versioning.bump('patch')

    check_bump(versioning)


def check_strategy_build_id(dirty):
    meta = new_meta('build-id', scm=conftest.MockGit(dirty))
    versioning = meta.versioning
    assert versioning.enabled
    assert not versioning.problem
    assert not versioning.strategy.problem
    assert 'major' in str(versioning.strategy.main_bits)
    assert 'commitid' in str(versioning.strategy.extra_bits)
    assert str(versioning.strategy) == "branch(master):{major}.{minor}.{distance}+!h{$*BUILD_ID:local}.{commitid}{dirty}"
    if dirty:
        assert meta.version == '0.1.3+h543.g123.dirty'

        with pytest.raises(setupmeta.UsageError):
            # Can't effectively bump when checkout is dirty
            versioning.bump('minor', commit=True)

    else:
        assert meta.version == '0.1.3+h543.g123'

    check_bump(versioning)


def check_bump(versioning):
    with conftest.capture_output() as out:
        versioning.bump('major')
        assert "Not committing bump, use --commit to commit" in out
        assert 'git tag -a v1.0.0 -m "Version 1.0.0"' in out
        assert "git push --tags origin" in out

    with conftest.capture_output() as out:
        versioning.bump('minor')
        assert "Not committing bump, use --commit to commit" in out
        assert 'git tag -a v0.2.0 -m "Version 0.2.0"' in out
        assert "git push --tags origin" in out

    with pytest.raises(setupmeta.UsageError):
        versioning.bump('foo')
