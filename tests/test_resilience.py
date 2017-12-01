"""
Test edge cases
"""

import os

import setupmeta
import conftest


def bogus_project(**attrs):
    return setupmeta.SetupMeta(dict(_setup_py_path='foo/bar', **attrs))


def test_shortening():
    assert setupmeta.short(None) is None
    assert setupmeta.short("") == ""

    assert setupmeta.short("hello there", c=11) == "hello there"
    assert setupmeta.short("hello there", c=8) == "11 chars"

    long_message = "hello there wonderful wild world"
    assert setupmeta.short(long_message, c=19) == "32 chars [hello...]"

    path = os.path.expanduser('~/foo/bar')
    assert setupmeta.short(path) == '~/foo/bar'

    message = "found in %s" % path
    assert setupmeta.short(message) == 'found in ~/foo/bar'


def test_edge_cases():
    with conftest.capture_output() as logged:
        setupmeta.clean_file(None)
        assert "Could not clean up None" in logged


def test_stringify():
    assert setupmeta.to_str(None) is None
    assert setupmeta.to_str('') == ''
    assert setupmeta.to_str(b'') == ''
    assert setupmeta.to_str('hello') == 'hello'
    assert setupmeta.to_str(b'hello') == 'hello'


def test_meta():
    assert not setupmeta.Meta.is_setup_py_path(None)
    assert not setupmeta.Meta.is_setup_py_path('')
    assert not setupmeta.Meta.is_setup_py_path('foo.py')
    assert setupmeta.Meta.is_setup_py_path('/foo/setup.py')
    assert setupmeta.Meta.is_setup_py_path('/foo/setup.pyc')


def test_representation():
    e = setupmeta.DefinitionEntry('foo', 'bar', 'inlined')
    assert str(e) == 'foo=bar from inlined'

    alpha1 = setupmeta.Definition('alpha')
    alpha2 = setupmeta.Definition('alpha')
    alpha2.add('foo', 'inlined')
    assert str(alpha1) == 'alpha=None from 0 sources'
    assert str(alpha2) == 'alpha=foo from 1 sources'

    beta = setupmeta.Definition('beta')
    assert str(beta) == 'beta=None from 0 sources'
    beta.add('foo1', 'inlined1')
    assert str(beta) == 'beta=foo1 from 1 sources'
    beta.add('foo2', 'inlined2')
    assert str(beta) == 'beta=foo1 from 2 sources'
    beta.add('foo3', 'inlined3', override=True)
    assert str(beta) == 'beta=foo3 from 3 sources'

    assert alpha1 == alpha2
    assert alpha1 != beta
    assert not alpha1 < alpha2
    assert alpha1 < beta
    assert not alpha1 > beta


def test_empty():
    meta = bogus_project()
    assert not meta.attrs
    assert not meta.definitions
    assert not meta.name
    assert not meta.version
    assert str(meta).startswith('0 definitions, ')
    assert not meta.explain()


def test_pygradle_version():
    os.environ['PYGRADLE_PROJECT_VERSION'] = '1.2.3'
    meta = bogus_project(name='pygradle_project')
    assert len(meta.definitions) == 2
    assert meta.value('name') == 'pygradle_project'
    assert meta.value('version') == '1.2.3'

    name = meta.definitions['name']
    version = meta.definitions['version']

    assert name.is_explicit
    assert not version.is_explicit

    del os.environ['PYGRADLE_PROJECT_VERSION']
