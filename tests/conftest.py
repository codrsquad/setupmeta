import imp
import os
import shutil
import sys
import warnings

import pytest
from six import StringIO

import setupmeta
from setupmeta import decode
from setupmeta.scm import Git


TESTS = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(TESTS)

setupmeta.TESTING = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


def resouce(*relative_path):
    """Full path for 'relative_path'"""
    return os.path.join(TESTS, *relative_path)


def relative_path(full_path):
    return full_path[len(PROJECT_DIR) + 1:]


def print_warning(message, *_, **__):
    """Print simplified warnings for capture in testing, instead of letting warnings do its funky thing"""
    print("WARNING: %s" % setupmeta.short(message, -60))


@pytest.fixture
def sample_project():
    """Yield a sample git project, seeded with files from tests/sample"""
    old_cd = os.getcwd()
    try:
        with setupmeta.temp_resource() as temp:
            source = resouce("sample")
            dest = os.path.join(temp, "sample")
            shutil.copytree(source, dest)
            files = os.listdir(dest)
            setupmeta.run_program("git", "init", cwd=dest)
            setupmeta.run_program("git", "add", *files, cwd=dest)
            setupmeta.run_program("git", "commit", "-m", "Initial commit", cwd=dest)
            setupmeta.run_program("git", "tag", "-a", "v0.1.0", "-m", "Version 2.4.2", cwd=dest)
            os.chdir(dest)
            yield dest

    finally:
        os.chdir(old_cd)


class capture_output:
    """
    Context manager allowing to temporarily grab stdout/stderr output.
    Output is captured and made available only for the duration of the context.

    Sample usage:

    with capture_output() as logged:
        ... do something that generates output ...
        assert "some message" in logged
    """

    def __init__(self, stdout=True, stderr=True, ownwarn=False):
        """
        :param bool stdout: If True, capture stdout
        :param bool stderr: If True, capture stderr
        :param bool ownwarn: If True, capture only setupmeta's warnings (drop the rest)
        """
        self.old_out = sys.stdout if stdout else None
        self.old_err = sys.stderr if stderr else None
        self.ownwarn = ownwarn
        self.old_warnings = warnings.warn
        self.old_setupmeta_warnings = setupmeta.warn
        self.out_buffer = None
        self.err_buffer = None

    def __repr__(self):
        result = ""
        if self.out_buffer:
            result += decode(self.out_buffer.getvalue())
        if self.err_buffer:
            result += decode(self.err_buffer.getvalue())
        return result.strip()

    def __enter__(self):
        if self.old_out is not None:
            sys.stdout = self.out_buffer = StringIO()
        if self.old_err is not None:
            sys.stderr = self.err_buffer = StringIO()

        if self.ownwarn:
            # Only let setupmeta's own warning through
            setupmeta.warn = print_warning
            warnings.warn = lambda *_, **__: None

        else:
            warnings.warn = print_warning

        return self

    def __exit__(self, *args):
        if self.old_out is not None:
            sys.stdout = self.old_out
        if self.old_err is not None:
            sys.stderr = self.old_err
        self.out_buffer = None
        self.err_buffer = None
        warnings.warn = self.old_warnings
        setupmeta.warn = self.old_setupmeta_warnings

    def __contains__(self, item):
        return item is not None and item in str(self)

    def __add__(self, other):
        return "%s %s" % (self, other)


def cleaned_output(text, folder=None):
    text = decode(text)
    if not text:
        return text
    result = []
    for line in text.splitlines():
        line = line.rstrip()
        if setupmeta.WINDOWS:
            if " \\_: " not in line:
                line = line.replace("\\", "/")
        if line and not line.startswith("pydev debugger:"):
            if folder:
                line = line.replace(folder, "<target>")
            result.append(line)
    return "\n".join(result).strip()


def run_setup_py(folder, *args):
    if folder == setupmeta.project_path() or not os.path.isabs(folder):
        return cleaned_output(setupmeta.run_program(sys.executable, os.path.join(folder, "setup.py"), *args, capture="all", fatal=True))

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
        setup_py = os.path.join(folder, "setup.py")
        with capture_output(ownwarn=True) as logged:
            sys.argv = [setup_py] + list(args)
            run_output = ""
            try:
                basename = "setup"
                fp, pathname, description = imp.find_module(basename, [folder])
                imp.load_module(basename, fp, pathname, description)

            except SystemExit as e:
                run_output += "'setup.py %s' exited with code 1:\n" % " ".join(args)
                run_output += "%s\n" % e

            run_output = "%s\n%s" % (logged, run_output.strip())
            return cleaned_output(run_output, folder)

    finally:
        if fp:
            fp.close()
        setupmeta.MetaDefs.project_dir = old_pd
        sys.argv = old_argv
        os.chdir(old_cd)


class MockGit(Git):
    def __init__(self, dirty=True, describe="v0.1.2-3-g123", branch="master", commitid="abc123"):
        self.dirty = dirty
        self.describe = describe
        self.branch = branch
        self.commitid = commitid
        Git.__init__(self, TESTS)

    def get_output(self, cmd, *args, **kwargs):
        if cmd.startswith("diff"):
            return 1 if self.dirty else 0
        if cmd == "describe":
            return self.describe
        if cmd == "rev-parse":
            if "--abbrev-ref" in args:
                return self.branch
            return self.commitid
        if cmd == "rev-list":
            return self.commitid.split()
        if cmd == "config":
            return args[1]
        assert kwargs.get("dryrun") is True
        return Git.get_output(self, cmd, *args, **kwargs)
