try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import os
import sys

from setupmeta import decode
from setupmeta.scm import Git


TESTS = os.path.dirname(__file__)
PROJECT = os.path.dirname(TESTS)


def resouce(*relative_path):
    """ Full path for 'relative_path' """
    return os.path.join(TESTS, *relative_path)


class capture_output:
    """
    Context manager allowing to temporarily grab stdout/stderr output.
    Output is captured and made available only for the duration of the context.

    Sample usage:

    with capture_output() as logged:
        ... do something that generates output ...
        assert "some message" in logged
    """
    def __init__(self, stdout=True, stderr=True):
        self.old_out = sys.stdout
        self.old_err = sys.stderr
        sys.stdout = self.out_buffer = StringIO() if stdout else self.old_out
        sys.stderr = self.err_buffer = StringIO() if stderr else self.old_err

    def __repr__(self):
        return self.to_string()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        sys.stdout = self.old_out
        sys.stderr = self.old_err
        self.out_buffer = None
        self.err_buffer = None

    def __contains__(self, item):
        return item is not None and item in self.to_string()

    def __add__(self, other):
        return "%s %s" % (self, other)

    def to_string(self):
        result = ''
        if self.out_buffer:
            result += decode(self.out_buffer.getvalue())
        if self.err_buffer:
            result += decode(self.err_buffer.getvalue())
        return result


class MockGit(Git):
    def __init__(self, dirty=True, describe='v0.1.2-3-g123', branch='master', commitid='abc123'):
        self.dirty = dirty
        self.describe = describe
        self.branch = branch
        self.commitid = commitid
        Git.__init__(self, resouce())

    def get_output(self, cmd, *args, **kwargs):
        if cmd == 'diff':
            return 1 if self.dirty else 0
        if cmd == 'describe':
            return self.describe
        if cmd == 'rev-parse':
            if '--abbrev-ref' in args:
                return self.branch
            return self.commitid
        if cmd == 'rev-list':
            return self.commitid.split()
        assert kwargs.get('dryrun') is True
        return Git.get_output(self, cmd, *args, **kwargs)
