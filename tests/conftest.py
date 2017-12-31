import os
import sys

from six import StringIO

from setupmeta import decode
from setupmeta.scm import Git


TESTS = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(TESTS)
SCENARIOS = os.path.join(TESTS, 'scenarios')
EXAMPLES = os.path.join(PROJECT_DIR, 'examples')

SCENARIO_COMMANDS = ['explain -c161', 'entrypoints']


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


def valid_scenarios(folder):
    result = []
    for name in os.listdir(folder):
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            result.append(full_path)
    return result


def scenario_paths():
    """ Available scenario names """
    return valid_scenarios(SCENARIOS) + valid_scenarios(EXAMPLES)


def get_scenario_commands(scenario):
    result = []
    result.extend(SCENARIO_COMMANDS)
    extra_commands = os.path.join(scenario, '.commands')
    if os.path.isfile(extra_commands):
        with open(extra_commands) as fh:
            for line in fh:
                line = decode(line).strip()
                if line:
                    result.append(line)
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
