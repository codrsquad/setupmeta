"""
Test edge cases
"""

import os

import setupmeta
from conftest import resouce


def bogus_project():
    return setupmeta.Attributes(dict(_setup_py=resouce('foo/bar')))


def test_shortening():
    assert setupmeta.short(None) is None
    assert setupmeta.short("") == ""

    assert setupmeta.short("hello there", max_chars=11) == "hello there"
    assert setupmeta.short("hello there", max_chars=8) == "11 chars"

    long_message = "hello there wonderful wild world"
    assert setupmeta.short(long_message, max_chars=19) == "32 chars [hello...]"

    path = os.path.expanduser('~/foo/bar')
    assert setupmeta.short(path) == '~/foo/bar'

    message = "found in %s" % path
    assert setupmeta.short(message) == 'found in ~/foo/bar'


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


def test_empty_attrs():
    attrs = bogus_project()
    assert not attrs.attrs
    assert not attrs.classifiers
    assert not attrs.definitions
    assert not attrs.name
    assert not attrs.packages
    assert os.path.basename(attrs.project_dir) == 'foo'
    assert not attrs.repo
    assert not attrs.version
    assert str(attrs).startswith('0 definitions, ')


def test_pygradle_version():
    os.environ['PYGRADLE_PROJECT_VERSION'] = '1.2.3'
    attrs = bogus_project()
    assert len(attrs.definitions) == 1
    assert attrs.value('version') == '1.2.3'
    del os.environ['PYGRADLE_PROJECT_VERSION']
