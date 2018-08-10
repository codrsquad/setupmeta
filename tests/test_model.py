import os
import sys

from mock import patch

from setupmeta.model import Definition, DefinitionEntry, first_word, is_setup_py_path, parse_requirements, SetupMeta


def bogus_project(**attrs):
    return SetupMeta(dict(_setup_py_path='/foo/bar/shouldnotexist/setup.py', **attrs))


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
    e = DefinitionEntry('foo', 'bar', 'inlined')
    assert str(e) == 'foo=bar from inlined'

    alpha1 = Definition('alpha')
    alpha2 = Definition('alpha')
    alpha2.add('foo', 'inlined')
    assert str(alpha1) == 'alpha=None from 0 sources'
    assert str(alpha2) == 'alpha=foo from inlined'

    beta = Definition('beta')
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
    assert not meta.requirements.install
    assert not meta.requirements.test
    assert not meta.version
    assert not meta.versioning.enabled
    assert meta.versioning.problem == 'setupmeta versioning not enabled'
    assert not meta.versioning.scm
    assert not meta.versioning.strategy
    assert str(meta).startswith('0 definitions, ')


@patch.dict(os.environ, {'PYGRADLE_PROJECT_VERSION': '1.2.3'})
def test_pygradle_version():
    meta = bogus_project(name='pygradle_project')
    assert len(meta.definitions) == 2
    assert meta.value('name') == 'pygradle_project'
    assert meta.value('version') == '1.2.3'

    name = meta.definitions['name']
    version = meta.definitions['version']

    assert name.is_explicit
    assert not version.is_explicit


def test_meta():
    assert not is_setup_py_path(None)
    assert not is_setup_py_path('')
    assert not is_setup_py_path('foo.py')

    assert is_setup_py_path('/foo/setup.py')
    assert is_setup_py_path('/foo/setup.pyc')


@patch('setupmeta.model.get_pip', return_value=(None, None))
def test_no_pip(*_):
    assert parse_requirements(None) == (None, None)
