"""
Test edge cases
"""

import os
import pytest

import setupmeta


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


def test_toml():
    assert setupmeta.toml_key_value(None) == (None, None)
    assert setupmeta.toml_key_value('=') == (None, None)
    assert setupmeta.toml_key_value('a=b') == ('a', 'b')
    assert setupmeta.toml_key_value('"a=b') == (None, '"a=b')
    assert setupmeta.toml_key_value('"a b"=c') == ('a b', 'c')

    assert setupmeta.is_toml_section('[a]')
    assert setupmeta.is_toml_section('[[a]]')

    assert setupmeta.normalized_toml('a=[\n1]'.split()) == ['a=[ 1]']

    assert setupmeta.parsed_toml(dict(a=1)) == dict(a=1)
    assert setupmeta.parsed_toml('a=[\n1]') == dict(a=[1])
    assert setupmeta.parsed_toml('=\n[foo]\na=1') == dict(foo=dict(a=1))

    assert setupmeta.toml_value(None) is None
    assert setupmeta.toml_value("true") is True
    assert setupmeta.toml_value("false") is False
    assert setupmeta.toml_value('{a=1,b=2}') == dict(a=1, b=2)
    assert setupmeta.toml_value("a") == 'a'


def test_edge_cases():
    with pytest.raises(Exception):
        setupmeta.abort("testing")

    with pytest.raises(Exception):
        obj = setupmeta.DefinitionEntry('', '', '')
        setupmeta.meta_command_init(obj, obj)


def test_stringify():
    assert setupmeta.to_str(None) == 'None'
    assert setupmeta.to_str('') == ''
    assert setupmeta.to_str(b'') == ''
    assert setupmeta.to_str('hello') == 'hello'
    assert setupmeta.to_str(b'hello') == 'hello'

    assert setupmeta.to_str([]) == "[]"
    assert setupmeta.to_str([None]) == "[None]"
    assert setupmeta.to_str([None, None]) == "[None, None]"
    assert setupmeta.to_str(['foo', 'bar']) == "['foo', 'bar']"

    assert setupmeta.to_str(tuple()) == "()"
    assert setupmeta.to_str((None,)) == "(None,)"
    assert setupmeta.to_str((None, None)) == "(None, None)"
    assert setupmeta.to_str(('foo', 'bar')) == "('foo', 'bar')"

    assert setupmeta.to_str(dict(bar='foo')) == "{'bar': 'foo'}"
    assert setupmeta.to_str(dict(bar=[u'foo'])) == "{'bar': ['foo']}"


def test_meta():
    assert not setupmeta.MetaDefs.is_setup_py_path(None)
    assert not setupmeta.MetaDefs.is_setup_py_path('')
    assert not setupmeta.MetaDefs.is_setup_py_path('foo.py')

    assert setupmeta.MetaDefs.is_setup_py_path('/foo/setup.py')
    assert setupmeta.MetaDefs.is_setup_py_path('/foo/setup.pyc')


def test_representation():
    e = setupmeta.DefinitionEntry('foo', 'bar', 'inlined')
    assert str(e) == 'foo=bar from inlined'

    alpha1 = setupmeta.Definition('alpha')
    alpha2 = setupmeta.Definition('alpha')
    alpha2.add('foo', 'inlined')
    assert str(alpha1) == 'alpha=None from 0 sources'
    assert str(alpha2) == 'alpha=foo from inlined'

    beta = setupmeta.Definition('beta')
    assert str(beta) == 'beta=None from 0 sources'
    beta.add('foo1', 'inlined1')
    assert str(beta) == 'beta=foo1 from inlined1'
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
