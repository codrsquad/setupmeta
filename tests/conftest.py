import contextlib
import io
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import os
import sys

TESTS = os.path.dirname(__file__)
PROJECT = os.path.dirname(TESTS)


def resouce(*relative_path):
    """ Full path for 'relative_path' """
    return os.path.join(TESTS, *relative_path)


def file_contents(*relative_path):
    full_path = resouce(*relative_path)
    with io.open(full_path, encoding='utf-8') as fh:
        return ''.join(fh.readlines()).strip()


@contextlib.contextmanager
def capture_output():
    old_out, old_err = sys.stdout, sys.stderr
    out_buffer, err_buffer = StringIO(), StringIO()
    try:
        sys.stdout, sys.stderr = out_buffer, err_buffer
        yield out_buffer, err_buffer
    finally:
        sys.stdout, sys.stderr = old_out, old_err
