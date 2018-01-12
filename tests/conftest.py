import imp
import os
import sys

from six import StringIO

import setupmeta
from setupmeta import decode
from setupmeta.scm import Git


TESTS = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(TESTS)
IGNORED_OUTPUT = set("debugger UserWarning warnings.warn".split())


os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True


def resouce(*relative_path):
    """ Full path for 'relative_path' """
    return os.path.join(TESTS, *relative_path)


def relative_path(full_path):
    return full_path[len(PROJECT_DIR) + 1:]


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


def cleaned_output(text, folder=None):
    text = decode(text)
    if not text:
        return text
    result = []
    for line in text.splitlines():
        line = line.rstrip()
        if line and all(m not in line for m in IGNORED_OUTPUT):
            if folder:
                line = line.replace(folder, '<target>')
            result.append(line)
    return '\n'.join(result).strip()


def run_setup_py(folder, *args):
    if folder == setupmeta.project_path() or not os.path.isabs(folder):
        return cleaned_output(setupmeta.run_program(sys.executable, os.path.join(folder, 'setup.py'), *args, capture='all', fatal=True))

    return run_internal_setup_py(folder, *args)


def run_internal_setup_py(folder, *args):
    """Run setup.py without an external process, to record coverage properly"""
    old_cd = os.getcwd()
    old_argv = sys.argv
    old_pd = setupmeta.MetaDefs.project_dir
    setupmeta.DEBUG = False
    fp = None
    try:
        os.chdir(folder)
        setup_py = os.path.join(folder, 'setup.py')
        with capture_output() as logged:
            sys.argv = [setup_py] + list(args)
            run_output = ''
            try:
                basename = 'setup'
                fp, pathname, description = imp.find_module(basename, [folder])
                imp.load_module(basename, fp, pathname, description)

            except SystemExit as e:
                run_output += "'setup.py %s' exited with code 1:\n" % ' '.join(args)
                run_output += "%s\n" % e

            run_output = "%s\n%s" % (logged.to_string().strip(), run_output.strip())
            return cleaned_output(run_output, folder)

    finally:
        if fp:
            fp.close()
        setupmeta.MetaDefs.project_dir = old_pd
        sys.argv = old_argv
        os.chdir(old_cd)


class MockGit(Git):
    def __init__(self, dirty=True, describe='v0.1.2-3-g123', branch='master', commitid='abc123'):
        self.dirty = dirty
        self.describe = describe
        self.branch = branch
        self.commitid = commitid
        Git.__init__(self, TESTS)

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
        if cmd == 'config':
            return args[1]
        assert kwargs.get('dryrun') is True
        return Git.get_output(self, cmd, *args, **kwargs)
