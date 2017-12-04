import os
import pytest

from setupmeta.content import abort, MetaDefs, meta_command_init, short, to_str


def test_shortening():
    assert short(None) is None
    assert short("") == ""

    assert short("hello there", c=11) == "hello there"
    assert short("hello there", c=8) == "11 chars"

    long_message = "hello there wonderful wild world"
    assert short(long_message, c=19) == "32 chars [hello...]"

    path = os.path.expanduser('~/foo/bar')
    assert short(path) == '~/foo/bar'

    message = "found in %s" % path
    assert short(message) == 'found in ~/foo/bar'


def test_edge_cases():
    with pytest.raises(Exception):
        abort("testing")

    with pytest.raises(Exception):
        obj = MetaDefs()
        meta_command_init(obj, obj)


def test_stringify():
    assert to_str(None) == 'None'
    assert to_str('') == ''
    assert to_str(b'') == ''
    assert to_str('hello') == 'hello'
    assert to_str(b'hello') == 'hello'

    assert to_str([]) == "[]"
    assert to_str([None]) == "[None]"
    assert to_str([None, None]) == "[None, None]"
    assert to_str(['foo', 'bar']) == "['foo', 'bar']"

    assert to_str(tuple()) == "()"
    assert to_str((None,)) == "(None,)"
    assert to_str((None, None)) == "(None, None)"
    assert to_str(('foo', 'bar')) == "('foo', 'bar')"

    assert to_str(dict(bar='foo')) == "{'bar': 'foo'}"
    assert to_str(dict(bar=[u'foo'])) == "{'bar': ['foo']}"
