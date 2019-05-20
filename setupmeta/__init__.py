"""
Simplify your setup.py

url: https://github.com/zsimic/setupmeta
download_url: archive/v{version}.tar.gz
author: Zoran Simic zoran@simicweb.com
"""

import os
import platform
import re
import shutil
import subprocess  # nosec
import sys
import tempfile
import warnings

import setuptools


USER_HOME = os.path.expanduser("~")  # Used to pretty-print subfolders of ~
DEBUG = os.environ.get("SETUPMETA_DEBUG")
VERSION_FILE = ".setupmeta.version"  # File used to work with projects that are in a subfolder of a git checkout
SCM_DESCRIBE = "SCM_DESCRIBE"  # Name of env var used as pass-through for cases where git checkout is not available
TESTING = False  # Set to True while running tests
RE_SPACES = re.compile(r"\s+", re.MULTILINE)

PLATFORM = platform.system().lower()
WINDOWS = "windows" in PLATFORM


def abort(message):
    """Abort execution with 'message'"""
    raise UsageError(message)


def warn(message):
    """Issue a warning (coming from setupmeta itself)"""
    warnings.warn(message, stacklevel=2)


def trace(message):
    """Output 'message' if tracing is on"""
    if not DEBUG:
        return
    sys.stderr.write(":: %s\n" % message)
    sys.stderr.flush()


def to_int(text, default=None):
    try:
        return int(text)
    except (ValueError, TypeError):
        return default


def short(text, c=None):
    """ Short representation of 'text' """
    if not text:
        return "%s" % text
    if c is None:
        c = Console.columns()
    result = stringify(text).strip()
    result = result.replace(USER_HOME, "~")
    result = re.sub(RE_SPACES, " ", result)
    if WINDOWS:  # pragma: no cover
        result = result.replace("\\", "/")
    if c and len(result) > abs(c):
        if c < 0:
            return "%s..." % result[:-c]
        if isinstance(text, dict):
            summary = "%s keys" % len(text)
        elif isinstance(text, list):
            summary = "%s items" % len(text)
        else:
            return "%s..." % result[:c - 3]
        cutoff = c - len(summary) - 5
        if cutoff <= 0:
            return summary
        return "%s: %s..." % (summary, result[:cutoff])
    return result


def strip_dash(text):
    """ Strip leading dashes from 'text' """
    if not text:
        return text
    return text.strip("-")


def is_executable(path):
    if WINDOWS:  # pragma: no cover
        return path and os.path.isfile(path) and path.endswith(".exe")
    return path and os.path.isfile(path) and os.access(path, os.X_OK)


def which(program):
    if not program:
        return None
    if WINDOWS and not program.endswith(".exe"):  # pragma: no cover
        program += ".exe"
    if os.path.isabs(program):
        if is_executable(program):
            return program
        return None
    for p in os.environ.get("PATH", "").split(os.pathsep):
        fp = os.path.join(p, program)
        if is_executable(fp):
            return fp
    ppath = project_path(program)
    if is_executable(ppath):
        return ppath
    return None


def represented_args(args, separator=" "):
    result = []
    for text in args:
        text = str(text)
        if not text or " " in text:
            sep = "'" if '"' in text else '"'
            result.append("%s%s%s" % (sep, text, sep))
        else:
            result.append(text)
    return separator.join(result)


def merged(output, error):
    if output and error:
        return "%s\n%s" % (output, error)
    if not output and error:
        return error
    return output


def run_program(program, *args, **kwargs):
    """
    Run 'program' with 'args'

    :param str program: Path to program to run
    :param args: Arguments to pass to program
    :param bool dryrun: When True, do not run, just print what would be ran
    :param bool fatal: When True, exit immediately on return code != 0
    :param bool capture: None: let output pass through, return exit code
                         False: ignore output, return exit code
                         True: return exit code and output/error
    """
    full_path = which(program)
    fatal = kwargs.pop("fatal", False)
    dryrun = kwargs.pop("dryrun", False)
    capture = kwargs.pop("capture", None)
    represented = "%s %s" % (program, represented_args(args))

    if dryrun:
        print("Would run: %s" % represented)
        return None if capture else 0

    problem = None if full_path else "'%s' is not installed" % program
    if problem:
        if fatal:
            sys.exit(problem)
        return None if capture else 1

    if capture is None:
        print("Running: %s" % represented)
        if TESTING:
            # Avoid pass-through chatter in tests
            DEVNULL = open(os.devnull, "w")
            kwargs["stdout"] = DEVNULL
            kwargs["stderr"] = DEVNULL

    else:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        if sys.version_info[0] < 3:
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            kwargs["env"] = env

    p = subprocess.Popen([full_path] + list(args), **kwargs)  # nosec
    output, error = p.communicate()
    output = decode(output)
    error = decode(error)

    trace_msg = "ran [%s], exitcode: %s" % (represented, p.returncode)
    if output:
        trace_msg = "%s, output: [%s]" % (trace_msg, output.strip())
    if error:
        trace_msg = "%s, error: [%s]" % (trace_msg, error.strip())
    trace(trace_msg)

    if capture:
        if output[-1:] == '\n':
            output = output[:-1]
        if capture == "all":
            if error[-1:] == '\n':
                error = error[:-1]
            return merged(output, error)
        return merged(output, None)

    if p.returncode and fatal:
        print("%s exited with code %s" % (represented, p.returncode))
        sys.exit(p.returncode)

    return p.returncode


def decode(value):
    """Python 2/3 friendly decoding of output"""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def quoted(text):
    """Quoted text, with single or double-quotes"""
    if text:
        if "\n" in text:
            return '"""%s"""' % text
        if '"' in text:
            return "'%s'" % text
    return '"%s"' % text


def _strs(value, bracket, first, sep, quote, indent):
    """Stringified iterable"""
    if isinstance(value, dict):
        rep = sep.join("%s: %s" % (stringify(k, quote=quote), stringify(v, quote=quote, indent=indent)) for k, v in sorted(value.items()))
        return "{%s%s%s}" % (first, rep, first[:-4])
    quote = quote or quote is None
    return "%s%s%s%s%s" % (bracket[0], first, sep.join(stringify(s, quote=quote, indent=indent) for s in value), first[:-4], bracket[1])


def _strm(value, bracket, quote, indent, chars=80):
    """Stringified iterable, multiline if representation > chars"""
    result = _strs(value, bracket, "", ", ", quote, indent)
    if len(value) <= 1 or len(result) <= chars:
        return result
    sep = ",\n%s" % indent if indent else ", "
    first = "\n%s" % indent if indent else ""
    return _strs(value, bracket, first, sep, quote, indent)


def stringify(value, quote=None, indent=""):
    """Avoid having the annoying u'..' in str() representations repr"""
    if isinstance(value, list):
        return _strm(value, "[]", quote=quote, indent=indent)
    if isinstance(value, tuple):
        return _strm(value, "()", quote=quote, indent=indent)
    if isinstance(value, dict):
        return _strm(value, "{}", quote=quote, indent=indent)
    if callable(value):
        return "function '%s'" % value.__name__
    if quote:
        return quoted("%s" % value)
    return "%s" % value


def listify(text, separator=None):
    """Turn 'text' into a list using 'separator'"""
    if isinstance(text, list):
        return text
    if isinstance(text, (set, tuple)):
        return list(text)
    if separator:
        text = text.replace("\n", separator)
    return [s.strip() for s in text.split(separator) if s.strip()]


def project_path(*relative_paths):
    """Full path corresponding to 'relative_paths' components"""
    return os.path.join(MetaDefs.project_dir, *relative_paths)


def relative_path(full_path):
    """Relative path to current project_dir"""
    return full_path[len(MetaDefs.project_dir) + 1:] if full_path and full_path.startswith(MetaDefs.project_dir) else full_path


class temp_resource:
    """
    Context manager for creating / auto-deleting a temp working folder
    """

    def __init__(self, is_folder=True):
        self.is_folder = is_folder
        self.old_cwd = os.getcwd()
        if is_folder:
            self.path = tempfile.mkdtemp()
        else:
            _, self.path = tempfile.mkstemp()

    def __enter__(self):
        if self.is_folder:
            os.chdir(self.path)
        else:
            os.chdir(os.path.dirname(self.path))
        return self.path

    def __exit__(self, *args):
        os.chdir(self.old_cwd)
        try:
            if self.is_folder:
                shutil.rmtree(self.path)
            else:
                os.unlink(self.path)
        except OSError:  # pragma: no cover
            pass


def meta_command_init(self, dist, **kwargs):
    """Custom __init__ injected to commands decorated with @MetaCommand"""
    self.setupmeta = getattr(dist, "_setupmeta", None)
    setuptools.Command.__init__(self, dist, **kwargs)


class UsageError(Exception):
    pass


class MetaDefs:
    """
    Meta definitions
    """

    # Our own commands (populated by @MetaCommand decorator)
    commands = []

    # Determined project directory
    project_dir = os.getcwd()

    # See http://setuptools.readthedocs.io/en/latest/setuptools.html listify
    metadata_fields = listify("""
        author author_email bugtrack_url classifiers description download_url keywords
        license long_description long_description_content_type
        maintainer maintainer_email name obsoletes
        platforms provides requires url version
    """)
    dist_fields = listify("""
        cmdclass contact contact_email dependency_links eager_resources
        entry_points exclude_package_data extras_require include_package_data
        install_requires libraries
        namespace_packages package_data package_dir packages py_modules
        python_requires scripts setup_requires tests_require test_suite
        versioning zip_safe
    """)
    all_fields = metadata_fields + dist_fields

    @classmethod
    def register_command(cls, command):
        """ Register our own 'command' """
        command.description = command.__doc__.strip().split("\n")[0]
        command.__init__ = meta_command_init
        if command.initialize_options == setuptools.Command.initialize_options:
            command.initialize_options = lambda x: None
        if command.finalize_options == setuptools.Command.finalize_options:
            command.finalize_options = lambda x: None
        if not hasattr(command, "user_options"):
            command.user_options = []
        cls.commands.append(command)
        return command

    @classmethod
    def dist_to_dict(cls, dist):
        """
        :param distutils.dist.Distribution dist: Distribution or attrs
        :return dict:
        """
        if not dist or isinstance(dist, dict):
            return dist or {}
        result = {}
        for key in cls.all_fields:
            value = cls.get_field(dist, key)
            if value is not None:
                result[key] = value
        return result

    @classmethod
    def fill_dist(cls, dist, attrs):
        for key, value in attrs.items():
            cls.set_field(dist, key, value)

    @classmethod
    def get_field(cls, dist, key):
        """
        :param distutils.dist.Distribution dist: Distribution to examine
        :param str key: Key to extract
        :return: None if 'key' wasn't in setup() call, value otherwise
        """
        if hasattr(dist.metadata, key):
            # Get directly from metadata, those are None by default
            return getattr(dist.metadata, key)
        # dist fields however have a weird '0' default for some...
        # we want to detect fields provided to the original setup() call
        value = getattr(dist, key, None)
        if value or isinstance(value, bool):
            return value
        return None

    @classmethod
    def set_field(cls, dist, key, value):
        if hasattr(dist.metadata, key):
            setattr(dist.metadata, key, value)
        elif hasattr(dist, key):
            setattr(dist, key, value)


class Console:

    _columns = None

    @classmethod
    def columns(cls, default=160):
        if cls._columns is None and sys.stdout.isatty() and "TERM" in os.environ:
            cols = os.popen("tput cols", "r").read()  # nosec
            cols = decode(cols)
            cls._columns = to_int(cols, default=None)
        if cls._columns is None:
            cls._columns = default
        return cls._columns
