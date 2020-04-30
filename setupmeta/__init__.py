"""
Simplify your setup.py

url: https://github.com/zsimic/setupmeta
download_url: archive/v{version}.tar.gz
author: Zoran Simic zoran@simicweb.com
"""

import io
import os
import platform
import re
import shutil
import subprocess  # nosec
import sys
import tempfile
import warnings

import setuptools

try:
    import pkg_resources

except ImportError:  # pragma: no cover
    warnings.warn("pkg_resources is not available, expect limited functionality", category=RuntimeWarning)
    pkg_resources = None


USER_HOME = os.path.expanduser("~")  # Used to pretty-print subfolders of ~
DEBUG = os.environ.get("SETUPMETA_DEBUG")
VERSION_FILE = ".setupmeta.version"  # File used to work with projects that are in a subfolder of a git checkout
SCM_DESCRIBE = "SCM_DESCRIBE"  # Name of env var used as pass-through for cases where git checkout is not available
TESTING = False  # Set to True while running tests
RE_SPACES = re.compile(r"\s+", re.MULTILINE)
RE_VERSION_COMPONENT = re.compile(r"(\d+|[A-Za-z]+)")

PLATFORM = platform.system().lower()
WINDOWS = "windows" in PLATFORM

# Simplistic parsing of known formats used in requirements.txt
RE_DEPENDENCY_AT = re.compile(r"\s*([-A-Za-z0-9_.]+)\s*@\s*(.+)")
RE_DEPENDENCY_EGG = re.compile(r".+#egg=([-A-Za-z0-9_.]+).*")
RE_SIMPLE_PIN = re.compile(r"^([-A-Za-z0-9_.]+)\s*==\s*([A-Za-z0-9.]+)\s*(;.*)?$")

K_ABSTRACT = "abstract"
K_INDIRECT = "indirect"
K_PINNED = "pinned"
KNOWN_SECTIONS = {K_ABSTRACT, K_INDIRECT, K_PINNED}


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


def pkg_req(text):
    """
    :param str|None text: Text to parse
    :return pkg_resources.Requirement|None: Corresponding parsed requirement, if valid
    """
    if text:
        try:
            return pkg_resources.Requirement(text)

        except Exception:
            return None


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


def version_components(text):
    """
    :param str text: Text to parse
    :return (int, int, int, str): Main triplet + additional version info found
    """
    components = [to_int(x, default=x) for x in RE_VERSION_COMPONENT.split(text) if x and x.isalnum()]
    main_triplet = []
    additional = []
    qualifier = ""
    distance = None
    for component in components:
        if not isinstance(component, int):
            qualifier = "%s%s" % (qualifier, component)
            continue

        if not additional and not qualifier and len(main_triplet) < 3:
            main_triplet.append(component)
            continue

        if qualifier is not None:
            if distance is None and qualifier in ("dev", "post"):
                distance = component

            component = "%s%s" % (qualifier, component)
            qualifier = ""

        additional.append(component)

    while len(main_triplet) < 3:
        main_triplet.append(0)

    if qualifier:
        additional.append(qualifier)

    dirty = "dirty" in additional

    return main_triplet[0], main_triplet[1], main_triplet[2], ".".join(additional), distance, dirty


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
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.PIPE

    else:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        env = kwargs.get("env", os.environ)
        if sys.version_info[0] < 3 and "PYTHONIOENCODING" not in env:
            if not isinstance(env, dict):
                env = dict(env)

            env["PYTHONIOENCODING"] = "utf-8"
            kwargs["env"] = env

    p = subprocess.Popen([full_path] + list(args), **kwargs)  # nosec
    output, error = p.communicate()
    output = decode(output)
    error = decode(error)

    trace_msg = "ran [%s], exitcode: %s" % (represented, p.returncode)
    if output:
        output = output.rstrip()
        trace_msg = "%s, output: [%s]" % (trace_msg, output.strip())

    if error:
        error = error.rstrip()
        trace_msg = "%s, error: [%s]" % (trace_msg, error.strip())

    trace(trace_msg)

    if capture:
        if capture == "all":
            return merged(output, error)

        if p.returncode:
            if not args or args[0] != "describe" or not error or "no names" not in error.lower():
                # Edge case: don't warn when no tags are present, git states "No names found" in that case...
                warn("%s exited with error code %s\n%s" % (represented, p.returncode, error))

        return merged(output, None)

    if p.returncode and fatal:
        print("%s exited with code %s:\n%s" % (represented, p.returncode, error))
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


def readlines(relative_path, limit=0):
    if relative_path:
        try:
            result = []
            full_path = project_path(relative_path)
            with io.open(full_path, "rt") as fh:
                for line in fh:
                    limit -= 1
                    if limit == 0:
                        break

                    result.append(line)

            return result

        except IOError:
            return None


def requirements_from_text(text):
    """Transform contents of a requirements.txt file to an appropriate form for install_requires
    Example:
        foo==1.0
        bar==2.0; python_version >= '3.6'
        baz>=1.2

    Transformed to: ["foo", "bar; python_version >= '3.6'", "baz>=1.2"]

    :param str text: Contents (text) of a requirements.txt file
    :return list: List of parsed and abstracted requirements
    """
    r = RequirementsFile("adhoc", text.splitlines())
    return r.filled_requirements


def requirements_from_file(path):
    """Transform contents of a requirements.txt file to an appropriate form for install_requires
    Example:
        foo==1.0
        bar==2.0; python_version >= '3.6'
        baz>=1.2

    Transformed to: ["foo", "bar; python_version >= '3.6'", "baz>=1.2"]

    :param str path: Path of requirements.txt file to read
    :return list|None: List of parsed and abstracted requirements
    """
    r = RequirementsFile.from_file(path)
    if r is not None:
        return r.filled_requirements


def extracted_dependency_link(line):
    if line.startswith("file:"):
        return line, None

    m = RE_DEPENDENCY_EGG.match(line)
    if m:
        return line, m.group(1)

    m = RE_DEPENDENCY_AT.match(line)
    if m:
        return m.group(2), m.group(1)

    if os.path.isabs(line):
        return "file://%s" % line, None

    return None, None


def first_word(text):
    """
    :param str|None text: Text to extract first word from
    :return str: Lower case of first word from 'text', if any
    """
    if text:
        text = text.strip()

    if not text:
        return text

    return text.split()[0].lower()


class ReqLine(object):
    def __init__(self, parent, line_number, parent_section, line):
        """
        :param RequirementsFile parent: Requirements.txt file where this line came from
        :param int line_number: Corresponding line number
        :param str|None parent_section: Optional parent section
        :param str line: Line to parse
        """
        self.parent = parent
        self.line_number = line_number
        self.parent_section = parent_section
        self.local_section = None
        line = line.strip()
        self.original = line
        self.comment = None
        self.editable = False
        self.requirement = None
        self.abstracted = None
        self.link = None
        self.note = None
        if not line or line.startswith("#"):
            self._set_comment(line[1:])
            return

        if line[0] not in "-_./\\" and not line[0].isalnum():
            # Ignore anything that doesn't look like valid req or option
            return

        if " #" in line:
            # Trailing comments can direct us to treat that particular line in a certain way regarding pinning
            i = line.index(" #")
            self._set_comment(line[i + 2:])
            line = line[:i].strip()

        if line.startswith("-e") or line.startswith("--editable"):
            self.editable = True
            p = line.partition(" ")
            line = p[2]

        if line.startswith("-"):
            return

        link, name = extracted_dependency_link(line)
        if link:
            if self.editable and "git" in link and not link.startswith("git+"):
                # Couldn't find a reference explaining why a git:// uri ends up being git+git:// when -e is used
                link = "git+%s" % link

            self.link = link
            self.requirement = name
            self.abstracted = name
            return

        self._set_requirement(line)

    def __repr__(self):
        return self.original

    @property
    def empty(self):
        return not self.link and not self.requirement

    @property
    def section(self):
        return self.local_section or self.parent_section

    @property
    def is_direct(self):
        return self.requirement and self.section != K_INDIRECT

    def _set_requirement(self, line):
        self.requirement = line
        if self.local_section:
            self.note = "'%s' stated on line" % self.local_section

        elif self.parent_section:
            self.note = "in '%s' section" % self.parent_section

        if not self.is_direct:
            return

        self.abstracted = line
        if self.section != K_PINNED:
            # Abstract only very specific and simple name==version reqs, that are not in an explicitly 'pinned' section
            m = RE_SIMPLE_PIN.match(line)
            if m:
                name = m.group(1)
                spec = m.group(3)
                self.abstracted = name if not spec else "%s%s" % (name, spec)
                if not self.note:
                    self.note = "abstracted by default"

    def _set_comment(self, comment):
        comment = comment.strip()
        if comment:
            self.comment = comment
            w = first_word(self.comment)
            if w in KNOWN_SECTIONS:
                self.local_section = w


def decorated_line(content, comment):
    if not comment:
        return content

    return "%s  # %s" % (content, comment)


class RequirementsFile:
    """ Keeps track of where requirements came from """

    def __init__(self, source, lines):
        """
        :param str source: Name identifying where `lines` came from
        :param list|None lines: Line contents to parse
        """
        self.source = source
        self.filled_requirements = []
        self.dependency_links = None
        self.abstracted = []
        self.ignored = []
        self.untouched = []
        self.lines = []
        current_section = None
        for n, line in enumerate(lines, start=1):
            req_line = ReqLine(self, n, current_section, line)
            self.lines.append(req_line)
            if req_line.empty:
                if req_line.local_section:
                    # Lines containing only a comment can start a "section", all requirements below this will respect that section
                    current_section = req_line.local_section

                continue

            used = False
            if req_line.link:
                used = True
                if self.dependency_links is None:
                    self.dependency_links = []

                if req_line.link not in self.dependency_links:
                    self.dependency_links.append(req_line.link)

            if req_line.is_direct:
                used = True
                req = req_line.abstracted
                if req_line.requirement == req_line.abstracted:
                    self.untouched.append(decorated_line(req_line.requirement, req_line.note))

                else:
                    self.abstracted.append(decorated_line(req_line.abstracted, req_line.note))

                if req not in self.filled_requirements:
                    self.filled_requirements.append(req)

            if not used:
                # Reqs in 'indirect' sections are ignored (pinning was done to satisfy some indirect dependency)
                # but should NOT be considered as our project's dep
                self.ignored.append(decorated_line(req_line.requirement, req_line.note))

    @classmethod
    def from_file(cls, path):
        """
        :param str path: Path to requirements.txt file to read
        :return RequirementsFile|None: Associated object, if possible
        """
        lines = readlines(path)
        if lines is not None:
            return cls(relative_path(path), lines)


def find_requirements(*relative_paths):
    """ Read old-school requirements.txt type file """
    for path in relative_paths:
        if path:
            path = project_path(path)
            if os.path.isfile(path):
                trace("found requirements: %s" % path)
                return RequirementsFile.from_file(path)


class Requirements:
    """ Allows to auto-fill requires from requirements.txt """

    def __init__(self, pkg_info):
        """
        :param setupmeta.model.PackageInfo pkg_info: PKG-INFO, when available
        """
        self.links_source = None
        self.install_requires = find_requirements(pkg_info.requires_txt, "requirements.txt", "pinned.txt")
        self.tests_require = find_requirements(
            "tests/requirements.txt",  # Preferred
            "requirements-dev.txt",  # Also accept other common variations
            "dev-requirements.txt",
            "test-requirements.txt",
            "requirements-test.txt",
        )

        if pkg_info.dependency_links:
            rf = RequirementsFile.from_file(pkg_info.dependency_links)
            self.links_source = rf.source
            self.dependency_links = rf.dependency_links

        else:
            self.dependency_links = []
            self.add_dependency_links(self.install_requires)
            self.add_dependency_links(self.tests_require)

    def add_dependency_links(self, entries):
        if entries and entries.dependency_links:
            if not self.links_source:
                self.links_source = entries.source

            for link in entries.dependency_links:
                if link not in self.dependency_links:
                    self.dependency_links.append(link)


class temp_resource:
    """
    Context manager for creating / auto-deleting a temp working folder
    """

    def __init__(self):
        self.old_cwd = os.getcwd()
        self.path = tempfile.mkdtemp()
        # OSX edge case: /var/<temp> is really /private/var/<temp>
        self.path = os.path.realpath(self.path)

    def __enter__(self):
        os.chdir(self.path)
        return self.path

    def __exit__(self, *args):
        os.chdir(self.old_cwd)
        try:
            shutil.rmtree(self.path)

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
        :param setuptools.dist.Distribution dist: Distribution to examine
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
    """Small helper to determine terminal width, used to try and get a nice fit for commands like 'explain'"""
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
