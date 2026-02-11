import os

import setupmeta


def test_shortening():
    assert setupmeta.short(None) == "None"
    assert setupmeta.short("") == ""

    assert setupmeta.short("hello  there", c=13) == "hello there"
    assert setupmeta.short("hello  there", c=12) == "hello there"
    assert setupmeta.short("hello  there", c=11) == "hello there"
    assert setupmeta.short("hello  there", c=10) == "hello t..."
    assert setupmeta.short("hello  there", c=-10) == "hello ther..."
    assert setupmeta.short("hello there wild wonderful world", c=19) == "hello there wild..."
    assert setupmeta.short("hello there wild wonderful world", c=-19) == "hello there wild wo..."

    assert setupmeta.short(["hello", "there", "wild", "wonderful  world"], c=34) == '4 items: ["hello", "there", "wi...'

    path = os.path.expanduser("~/foo/bar")
    assert setupmeta.short(path) == "~/foo/bar"

    assert setupmeta.short("found in %s" % path) == "found in ~/foo/bar"

    assert setupmeta.short({"foo": "bar"}, c=8) == "1 keys"


def test_strip():
    assert setupmeta.strip_dash(None) is None
    assert setupmeta.strip_dash("foo") == "foo"
    assert setupmeta.strip_dash("--foo-") == "foo"


def test_listify():
    assert setupmeta.listify("a, b") == ["a,", "b"]
    assert setupmeta.listify("a,  b") == ["a,", "b"]
    assert setupmeta.listify("a, b", separator=",") == ["a", "b"]
    assert setupmeta.listify("a,, b", separator=",") == ["a", "b"]
    assert setupmeta.listify("a,\n b", separator=",") == ["a", "b"]
    assert setupmeta.listify("a\n b", separator=",") == ["a", "b"]
    assert setupmeta.listify(("a", "b")) == ["a", "b"]


def test_parsing():
    assert setupmeta.to_int(None) is None
    assert setupmeta.to_int(None, default=2) == 2
    assert setupmeta.to_int("") is None
    assert setupmeta.to_int("foo") is None
    assert setupmeta.to_int(["foo"]) is None
    assert setupmeta.to_int([1]) is None
    assert setupmeta.to_int(1, default=2) == 1
    assert setupmeta.to_int(0, default=2) == 0


def test_stringify():
    assert setupmeta.stringify((1, 2)) == '("1", "2")'
    assert setupmeta.stringify(["1", "2"]) == '["1", "2"]'
    assert setupmeta.stringify(("a b", "c d")) == '("a b", "c d")'

    assert setupmeta.stringify("""quoted ("double"+'single')""", quote=True) == """'quoted ("double"+'single')'"""
    assert setupmeta.stringify("""quoted 'single only'""", quote=True) == '''"quoted 'single only'"'''
    assert setupmeta.stringify("no 'foo'") == "no 'foo'"
    assert setupmeta.stringify("no 'foo'", quote=True) == '''"no 'foo'"'''

    assert setupmeta.stringify({"bar": "no 'foo'"}) == """{bar: no 'foo'}"""
    assert setupmeta.stringify({"bar": 'no "foo"'}) == """{bar: no "foo"}"""

    assert setupmeta.listify("a b") == ["a", "b"]
    assert sorted(setupmeta.listify(set("ab"))) == ["a", "b"]
    assert setupmeta.listify(("a", "b")) == ["a", "b"]
