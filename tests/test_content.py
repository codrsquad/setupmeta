import os

from setupmeta import decode, listify, short, MetaDefs


def test_shortening():
    assert short(None) == "None"
    assert short("") == ""

    assert short("hello there", c=11) == "hello there"
    assert short("hello there", c=8) == "11 chars"

    long_message = "hello there wild wonderful world"
    assert short(long_message, c=19) == "32 chars: hello ..."

    long_message = ["hello", "there", "wild", "wonderful  world"]
    assert short(long_message, c=34) == "4 items: ['hello', 'there', 'wi..."

    path = os.path.expanduser('~/foo/bar')
    assert short(path) == '~/foo/bar'

    message = "found in %s" % path
    assert short(message) == 'found in ~/foo/bar'


def test_listify():
    assert listify("a, b") == ['a,', 'b']
    assert listify("a,  b") == ['a,', 'b']
    assert listify("a, b", separator=',') == ['a', 'b']
    assert listify("a,, b", separator=',') == ['a', 'b']
    assert listify("a,\n b", separator=',') == ['a', 'b']
    assert listify("a\n b", separator=',') == ['a', 'b']


def test_decode():
    assert decode(None) is None
    assert decode('') == ''
    assert decode(b'') == ''
