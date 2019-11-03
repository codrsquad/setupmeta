import os

import pytest

import setupmeta

from . import conftest


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

    assert setupmeta.short(dict(foo="bar"), c=8) == "1 keys"

    assert setupmeta.merged("a", None) == "a"
    assert setupmeta.merged(None, "a") == "a"
    assert setupmeta.merged("a", "b") == "a\nb"


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


def test_decode():
    assert setupmeta.decode(None) is None
    assert setupmeta.decode("") == ""
    assert setupmeta.decode(b"") == ""


def test_parsing():
    assert setupmeta.to_int(None) is None
    assert setupmeta.to_int(None, default=2) == 2
    assert setupmeta.to_int("") is None
    assert setupmeta.to_int("foo") is None
    assert setupmeta.to_int(["foo"]) is None
    assert setupmeta.to_int([1]) is None
    assert setupmeta.to_int(1, default=2) == 1
    assert setupmeta.to_int(0, default=2) == 0


def test_which():
    assert setupmeta.which(None) is None
    assert setupmeta.which("/foo/does/not/exist") is None
    assert setupmeta.which("foo/does/not/exist") is None
    assert setupmeta.which("pip")


def test_run_program():
    setupmeta.DEBUG = True
    with conftest.capture_output() as out:
        assert setupmeta.run_program("ls", capture=True, dryrun=True) is None
        assert setupmeta.run_program("ls", capture=False, dryrun=True) == 0
        assert setupmeta.run_program("ls", "foo/does/not/exist", capture=None) != 0
        assert setupmeta.run_program("pip", "--version", capture=True)
        assert setupmeta.run_program("pip", "foo bar", capture=True) == ""
        assert "unknown command" in setupmeta.run_program("pip", "foo bar", capture="all")
        assert setupmeta.run_program("/foo/does/not/exist", capture=True, dryrun=True) is None
        assert setupmeta.run_program("/foo/does/not/exist", capture=False) != 0

        with pytest.raises(SystemExit):
            setupmeta.run_program("/foo/does/not/exist", fatal=True)

        with pytest.raises(SystemExit):
            assert setupmeta.run_program("ls", "foo/does/not/exist", fatal=True)

        assert "exitcode" in out

    setupmeta.DEBUG = False


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


def test_meta_command_init():
    with pytest.raises(Exception):
        obj = setupmeta.MetaDefs()
        setupmeta.meta_command_init(obj, {})
