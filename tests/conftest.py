import importlib.util
import os
import shutil
import sys
import warnings
from io import StringIO

import pytest

import setupmeta
from setupmeta.model import SetupMeta
from setupmeta.scm import Git

TESTS = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(TESTS)

setupmeta.MetaDefs.project_dir = PROJECT_DIR
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


def resource(*relative_path):
    """Full path for 'relative_path'"""
    return os.path.join(TESTS, *relative_path)


def relative_path(full_path):
    return full_path[len(PROJECT_DIR) + 1 :]


def ignore_warning(*_, **__):
    pass


def print_warning(message, *_, **__):
    """Print simplified warnings for capture in testing, instead of letting warnings do its funky thing"""
    print("WARNING: %s" % setupmeta.short(message, -60))


def run_git(*args, cwd=None):
    # git requires a user.email configured, which is usually done in ~/.gitconfig, however under tox, we don't have $HOME defined
    result = setupmeta.run_program("git", "-c", "user.name=Tester", "-c", "user.email=test@example.com", *args, cwd=cwd)
    result.require_success()
    return result


@pytest.fixture
def sample_project():
    """Yield a sample git project, seeded with files from tests/sample"""
    with setupmeta.temp_resource() as temp:
        source = resource("sample")
        dest = os.path.join(temp, "sample")
        shutil.copytree(source, dest)
        files = os.listdir(dest)
        run_git("init", cwd=dest)
        run_git("add", *files, cwd=dest)
        run_git("commit", "-m", "Initial commit", cwd=dest)
        with setupmeta.current_folder(dest):
            yield dest


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


class capture_warnings:
    """
    Context manager allowing to temporarily silence setuptools warnings, capture only setupmeta's warnings.
    """

    def __init__(self):
        self.old_setupmeta_warnings = setupmeta.warn
        self.old_warnings = warnings.warn

    def __enter__(self):
        setupmeta.warn = print_warning
        warnings.warn = ignore_warning
        return self

    def __exit__(self, *args):
        setupmeta.warn = self.old_setupmeta_warnings
        warnings.warn = self.old_warnings


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
        """
        :param bool stdout: If True, capture stdout
        :param bool stderr: If True, capture stderr
        """
        self.capture_warn = capture_warnings()
        self.old_out = sys.stdout if stdout else None
        self.old_err = sys.stderr if stderr else None
        self.out_buffer = None
        self.err_buffer = None

    def __repr__(self):
        result = ""
        if self.out_buffer:
            result += self.out_buffer.getvalue()

        if self.err_buffer:
            result += self.err_buffer.getvalue()

        return result.rstrip()

    def clear(self):
        """Clear captured content"""
        if self.out_buffer is not None:
            self.out_buffer.seek(0)
            self.out_buffer.truncate(0)
        if self.err_buffer is not None:
            self.err_buffer.seek(0)
            self.err_buffer.truncate(0)

    def pop(self):
        result = str(self)
        self.clear()
        return result

    def __enter__(self):
        if self.old_out is not None:
            sys.stdout = self.out_buffer = StringIO()

        if self.old_err is not None:
            sys.stderr = self.err_buffer = StringIO()

        self.capture_warn.__enter__()
        return self

    def __exit__(self, *args):
        if self.old_out is not None:
            sys.stdout = self.old_out

        if self.old_err is not None:
            sys.stderr = self.old_err

        self.out_buffer = None
        self.err_buffer = None
        self.capture_warn.__exit__(*args)

    def __contains__(self, item):
        return item in str(self)


def simplified_output_path(line, representation, path):
    if line and path:
        rp = os.path.realpath(path)
        if rp not in line:
            rp = path

        return line.replace(rp, representation)

    return line


def _cleaned_text(folder, cwd, text):
    result = []
    for line in text.splitlines():
        line = line.rstrip()
        if line and not line.startswith(("pydev debugger:", "Connected to: <socket")) and "Module setupmeta was" not in line:
            line = simplified_output_path(line, "<target>", folder)
            line = simplified_output_path(line, "<tests>", TESTS)
            line = simplified_output_path(line, "<setupmeta>", PROJECT_DIR)
            line = simplified_output_path(line, "<cwd>", cwd)
            result.append(line)

    return "\n".join(result).rstrip()


def cleaned_output(run_result, folder=None):
    cwd = os.getcwd()
    result = []
    output = _cleaned_text(folder, cwd, run_result.stdout)
    if output:
        result.append(output)

    if run_result.returncode:
        result.append(f"{setupmeta.represented_args(run_result.args)} exited with code {run_result.returncode}:")
        output = _cleaned_text(folder, cwd, run_result.stderr)
        if output:
            result.append(output)

    return "\n".join(result).rstrip()


def spawn_setup_py(folder, *args):
    """Invoke `setup.py` from `folder` as an external process, silence all warnings"""
    env = dict(os.environ)
    env["PYTHONWARNINGS"] = "ignore"
    result = setupmeta.run_program(sys.executable, "setup.py", "-q", *args, cwd=folder, env=env)
    return cleaned_output(result, folder=folder)


def invoke_setup_py(folder, *args):
    """Run `setup.py` from `folder` in-process if possible, to record coverage properly"""
    if folder == setupmeta.project_path():
        return spawn_setup_py(folder, *args)

    old_argv = sys.argv
    old_pd = setupmeta.MetaDefs.project_dir
    try:
        setup_py = os.path.join(folder, "setup.py")
        sys.argv = [setup_py, "-q", *args]
        result = setupmeta.RunResult(program=sys.executable, args=sys.argv)
        with capture_output() as logged:
            try:
                spec = importlib.util.spec_from_file_location("setup", setup_py)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                result.stdout = str(logged)

            except (SystemExit, setupmeta.UsageError) as e:
                result.returncode = 1
                result.stderr = str(e)

            return cleaned_output(result, folder=folder)

    finally:
        setupmeta.MetaDefs.project_dir = old_pd
        sys.argv = old_argv


class MockGit(Git):
    def __init__(self, describe="v0.1.2-3-g123-dirty", branch="main", commitid="abc123", local_tags="", remote_tags=""):
        self.describe = describe
        self.branch = branch
        self.commitid = commitid
        self.status_message = "## %s...origin/%s" % (branch, branch)
        self._local_tags = local_tags
        self._remote_tags = remote_tags
        Git.__init__(self, TESTS)

    def run_program(self, cmd, *args, announce=False, dryrun=False):
        if dryrun:
            return setupmeta.run_program("git", cmd, *args, announce=announce, dryrun=dryrun)

        result = setupmeta.RunResult(program="git", args=args)
        if cmd in ("fetch", "add", "commit"):
            return result

        if cmd == "tag":
            result.stderr = "chatty stderr"  # Simulate output on stderr is passed through
            return result

        if cmd == "push":
            result.returncode = 1
            result.stderr = "oops push failed"
            return result

        if cmd == "diff":
            if args[0] == "--quiet":
                if "-dirty" in self.describe:
                    result.returncode = 1

            elif args[0] == "--stat":
                result.returncode = 1
                result.stdout = "some diff stats"
                result.stderr = "oops something happened"

            return result

        if cmd == "describe":
            result.stdout = self.describe
            return result

        if cmd == "rev-parse":
            result.stdout = self.branch if "--abbrev-ref" in args else self.commitid.splitlines()[0]
            return result

        if cmd == "rev-list":
            result.stdout = self.commitid
            return result

        if cmd == "config":
            result.stdout = args[1]
            return result

        if cmd == "show-ref":
            result.stdout = self._local_tags
            return result

        if cmd == "ls-remote":
            result.stdout = self._remote_tags
            return result

        if cmd.startswith("status"):
            result.stdout = self.status_message
            return result
