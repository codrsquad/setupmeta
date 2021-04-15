import os
import shutil
import sys
import warnings

import pytest
from six import StringIO

import setupmeta
from setupmeta import decode
from setupmeta.model import SetupMeta
from setupmeta.scm import Git


TESTS = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(TESTS)

setupmeta.MetaDefs.project_dir = PROJECT_DIR
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


def run_program(program, *args, **kwargs):
    capture = kwargs.pop("capture", True)
    fatal = kwargs.pop("fatal", True)
    represented = "%s %s" % (program, setupmeta.represented_args(args))
    print("Running: %s" % represented)
    if not setupmeta.WINDOWS and "PYCHARM_HOSTED" in os.environ and "python" in program and args and args[0].startswith("-m"):
        # Temporary workaround for https://youtrack.jetbrains.com/issue/PY-40692
        wrapper = os.path.join(os.path.dirname(__file__), "pydev-wrapper.sh")
        args = [wrapper, program] + list(args)
        program = "/bin/sh"

    output = setupmeta.run_program(program, *args, capture=capture, fatal=fatal, **kwargs)
    if output and capture:
        print("output:")
        print(output)

    return output


def run_git(*args, **kwargs):
    # git requires a user.email configured, which is usually done in ~/.gitconfig, however under tox, we don't have $HOME defined
    kwargs.setdefault("capture", True)
    kwargs.setdefault("fatal", True)
    output = setupmeta.run_program("git", "-c", "user.name=Tester", "-c", "user.email=test@example.com", *args, **kwargs)
    return output


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
            run_git("init", cwd=dest)
            run_git("add", *files, cwd=dest)
            run_git("commit", "-m", "Initial commit", cwd=dest)
            os.chdir(dest)
            yield dest

    finally:
        os.chdir(old_cd)


class TestMeta:
    def __init__(self, setup=None, **upstream):
        upstream.setdefault("_setup_py_path", setup)
        self.upstream = upstream
        self.old_pd = None

    def __enter__(self):
        self.old_pd = setupmeta.MetaDefs.project_dir
        return SetupMeta().finalize(self.upstream)

    def __exit__(self, *args):
        setupmeta.MetaDefs.project_dir = self.old_pd


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

        return result.rstrip()

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
        return item in str(self)

    def __len__(self):
        return len(str(self))

    def __add__(self, other):
        return "%s %s" % (self, other)


def should_ignore_output(line):
    if not line:
        return True

    if line.startswith("pydev debugger:"):
        return True

    if "Module setupmeta was already imported" in line:
        # Edge case when pinning setupmeta itself to a certain version
        return True

    if "pkg_resources.working_set.add" in line:
        return True


def simplified_temp_path(line, *paths):
    if line:
        for path in paths:
            if path:
                p = os.path.realpath(path)
                if p in line:
                    return line.replace(p, "<target>")

                if path in line:
                    return line.replace(path, "<target>")

    return line


def cleaned_output(text, folder=None):
    text = decode(text)
    if not text:
        return text

    result = []
    cwd = os.getcwd()
    for line in text.splitlines():
        line = line.rstrip()
        if should_ignore_output(line):
            continue

        if setupmeta.WINDOWS:
            if " \\_: " not in line:
                line = line.replace("\\", "/")

        line = simplified_temp_path(line, folder, cwd)
        # Ignore minor change in how missing meta-data warning is phrased...
        line = line.replace(" must be supplied", " should be supplied")
        result.append(line)

    return "\n".join(result).rstrip()


def run_setup_py(folder, *args):
    if folder == setupmeta.project_path() or not os.path.isabs(folder):
        output = run_program(sys.executable, os.path.join(folder, "setup.py"), "-q", *args, capture="all")
        return cleaned_output(output)

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
            sys.argv = [setup_py, "-q"] + list(args)
            run_output = ""
            try:
                basename = "setup"
                if sys.version_info[0] > 2:
                    import importlib.util

                    spec = importlib.util.spec_from_file_location(basename, setup_py)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                else:
                    # With python2, we have to use deprecated imp module
                    import imp

                    fp, pathname, description = imp.find_module(basename, [folder])
                    imp.load_module(basename, fp, pathname, description)

            except SystemExit as e:
                run_output += "'setup.py %s' exited with code 1:\n" % " ".join(args)
                run_output += "%s\n" % e

            run_output = "%s\n%s" % (logged, run_output.rstrip())
            return cleaned_output(run_output, folder=folder)

    finally:
        if fp:
            fp.close()

        setupmeta.MetaDefs.project_dir = old_pd
        sys.argv = old_argv
        os.chdir(old_cd)


class MockGit(Git):
    def __init__(
        self,
        dirty=True,
        describe="v0.1.2-3-g123",
        branch="master",
        commitid="abc123",
        local_tags="",
        remote_tags="",
    ):
        self.dirty = dirty
        self.describe = describe
        self.branch = branch
        self.commitid = commitid
        self.status_message = "## master...origin/master"
        self._local_tags = local_tags
        self._remote_tags = remote_tags
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

        if cmd == "show-ref":
            return self._local_tags

        if cmd == "ls-remote":
            return self._remote_tags

        if cmd.startswith("fetch"):
            return None

        if cmd.startswith("status"):
            return self.status_message

        assert kwargs.get("dryrun") is True
        return Git.get_output(self, cmd, *args, **kwargs)
