"""
Simplify your setup.py

url: https://github.com/codrsquad/setupmeta
download_url: archive/v{version}.tar.gz
author: Zoran Simic zoran@simicweb.com
"""

import contextlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import warnings

USER_HOME = os.path.expanduser("~")  # Used to pretty-print subfolders of ~
TRACE_ENABLED = os.environ.get("SETUPMETA_DEBUG")
VERSION_FILE = ".setupmeta.version"  # File used to work with projects that are in a subfolder of a git checkout
SCM_DESCRIBE = "SCM_DESCRIBE"  # Name of env var used as pass-through for cases where git checkout is not available
RE_SPACES = re.compile(r"\s+", re.MULTILINE)
RE_VERSION_COMPONENT = re.compile(r"(\d+|[A-Za-z]+)")

PLATFORM = platform.system().lower()
PKGID = "[A-Za-z0-9][-A-Za-z0-9_.]*"

# Simplistic parsing of known formats used in requirements.txt
RE_SIMPLE_PIN = re.compile(r"^(%s)\s*==\s*([^;\s]+)\s*(;.*)?$" % PKGID)
RE_WORDS = re.compile(r"\W+")
RE_PKG_NAME = re.compile(r"^(%s)$" % PKGID)

ABSTRACT = "abstract"
INDIRECT = "indirect"
PINNED = "pinned"
KNOWN_SECTIONS = {ABSTRACT, INDIRECT, PINNED}


def abort(message):
    """Abort execution with 'message'"""
    raise UsageError(message)


def warn(message):
    """Issue a warning (coming from setupmeta itself)"""
    warnings.warn(message, stacklevel=2)


def trace(message):
    """Output `message` if tracing is on"""
    if TRACE_ENABLED:
        sys.stderr.write(f":: {message}\n")
        sys.stderr.flush()


def get_words(text):
    if text:
        return [s.strip() for s in RE_WORDS.split(text) if s.strip()]


def to_int(text, default=None):
    try:
        return int(text)

    except (ValueError, TypeError):
        return default


def short(text, c=None):
    """Short representation of 'text'"""
    if not text:
        return f"{text}"

    if c is None:
        c = Console.columns()

    result = stringify(text).strip()
    result = result.replace(USER_HOME, "~")
    result = re.sub(RE_SPACES, " ", result)
    if c and len(result) > abs(c):
        if c < 0:
            return f"{result[:-c]}..."

        if isinstance(text, dict):
            summary = f"{len(text)} keys"

        elif isinstance(text, list):
            summary = f"{len(text)} items"

        else:
            return f"{result[: c - 3]}..."

        cutoff = c - len(summary) - 5
        return summary if cutoff <= 0 else f"{summary}: {result[:cutoff]}..."

    return result


def strip_dash(text):
    """Strip leading dashes from 'text'"""
    if not text:
        return text

    return text.strip("-")


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
            qualifier = f"{qualifier}{component}"
            continue

        if not additional and not qualifier and len(main_triplet) < 3:
            main_triplet.append(component)
            continue

        if qualifier is not None:
            if distance is None and qualifier in ("dev", "post"):
                distance = component

            component = f"{qualifier}{component}"
            qualifier = ""

        additional.append(str(component))

    while len(main_triplet) < 3:
        main_triplet.append(0)

    if qualifier:
        if not qualifier[-1].isdigit():
            # PEP-440 states additional components such as 'rc' must be followed by a number
            qualifier += "0"

        additional.append(qualifier)

    dirty = "dirty" in additional
    return main_triplet[0], main_triplet[1], main_triplet[2], ".".join(additional), distance, dirty


def represented_args(args, separator=" "):
    result = []
    for text in args:
        text = str(text)
        if not text or " " in text:
            sep = "'" if '"' in text else '"'
            result.append(f"{sep}{text}{sep}")

        else:
            result.append(text)

    return separator.join(result)


class FullPathCache:
    """Used to find and trace full paths to programs once."""

    def __init__(self):
        self.cache = {}

    def which(self, program):
        if program not in self.cache:
            full_path = shutil.which(program)
            self.cache[program] = full_path
            trace(f"Full path for {program}: {full_path or '-not installed-'}")

        return self.cache[program]


class RunResult:
    full_path_cache = FullPathCache()

    def __init__(self, program=None, args=None, returncode=0, stdout="", stderr=""):
        self.program = program
        self.full_path = self.full_path_cache.which(program)
        self.full_args = [self.full_path or program, *args]
        self.args = args
        self.represented_args = f"{program} {represented_args(args)}".strip()
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        if not self.full_path:
            self.returncode = returncode or 1
            self.stderr = stderr or f"'{program}' is not installed"

    def require_success(self):
        """Abort execution if run was not successful"""
        if self.returncode:
            sys.stderr.write(f"{self.represented_args} exited with code {self.returncode}:\n{self.stderr or '-no stderr-'}\n")
            sys.exit(self.returncode)

    def trace_message(self):
        trace_msg = f"{self.represented_args} exited with code: {self.returncode}"
        if self.stdout:
            trace_msg += f", stdout: [{self.stdout}]"

        if self.stderr:
            trace_msg += f", stderr: [{self.stderr}]"

        return trace_msg


def run_program(program, *args, announce=False, cwd=None, dryrun=False, env=None):
    """
    Run `program` with `args`

    Parameters
    ----------
    program : str
        Program to run
    *args : str
        Arguments to pass to program
    announce : bool
        If True, announce the run
    cwd : str | None
        Working directory
    dryrun : bool
        When True, do not run, just print what would be run
    env : dict | None
        Environment variables

    Returns
    -------
    RunResult
    """
    result = RunResult(program, args)
    if dryrun:
        print(f"Would run: {result.represented_args}")

    elif announce:
        print(f"Running: {result.represented_args}")

    if dryrun or not result.full_path:
        return result

    if not announce:
        trace(f"Running: {result.represented_args}")

    r = subprocess.run(result.full_args, capture_output=True, cwd=cwd, env=env, text=True)  # noqa: S603
    result.returncode = r.returncode
    result.stdout = r.stdout.rstrip()
    result.stderr = r.stderr.rstrip()
    trace(result.trace_message())
    return result


def quoted(text):
    """Quoted text, with single or double-quotes"""
    if text:
        if "\n" in text:
            return f'"""{text}"""'

        if '"' in text:
            return f"'{text}'"

    return f'"{text}"'


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
    return full_path[len(MetaDefs.project_dir) + 1 :] if full_path and full_path.startswith(MetaDefs.project_dir) else full_path


def readlines(relative_path, limit=0):
    if relative_path:
        try:
            result = []
            full_path = project_path(relative_path)
            with open(full_path, "rt") as fh:
                for line in fh:
                    limit -= 1
                    if limit == 0:
                        break

                    result.append(line)

            trace("read %s lines from %s" % (len(result), relative_path))

        except IOError:
            return None

        else:
            return result


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
    r = RequirementsFile()
    r.scan(text.splitlines())
    r.finalize()
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


def first_word(text):
    """
    :param str|None text: Text to extract first word from
    :return str: Lower case of first word from 'text', if any
    """
    words = get_words(text)
    if words:
        return words[0].lower()


def standard_req(line):
    """
    :param str line: Line from requirements.txt to inspect
    :return str: Req that should be auto-filled (if usable)
    """
    if line and line[0].isalpha() and not line.startswith("file:") and not os.path.isabs(line):
        return line


class ReqEntry(object):
    def __init__(self, parent, source_path, line_number, parent_section, line):
        """
        :param RequirementsFile parent: Requirements.txt file where this line came from
        :param str source_path: Where this req came from
        :param int line_number: Corresponding line number
        :param str|None parent_section: Optional parent section, one of: abstract, indirect or pinned
        :param str line: Line to parse
        """
        self.parent = parent
        self.source_path = source_path
        self.source = relative_path(source_path)
        self.line_number = line_number
        self.parent_section = parent_section
        self.local_section = None
        line = line.replace("\t", " ").strip()
        self.given = line  # Given parsed line, as-is
        self.comment = None  # Extracted comment, if any
        self.editable = False  # True if entry was marked `--editable` (or `-e` for short)
        self.requirement = None  # Associated requirement name, if any
        self.abstracted = None  # True if self.requirement was auto-abstracted
        self.refers = None  # Another requirements.txt this one refers to
        if not line or line.startswith("#"):
            s = self._set_comment(line[1:])
            if s:
                self.parent_section = s

            return

        if " #" in line:
            # Trailing comments can direct us to treat that particular line in a certain way regarding pinning
            i = line.index(" #")
            self.local_section = self._set_comment(line[i + 2 :])
            line = line[:i].strip()

        if line.startswith(("-e ", "--editable ")):
            self.editable = True
            p = line.partition(" ")
            line = p[2].strip()

        elif line.startswith(("-r ", "--requirement ")):
            _, _, self.refers = line.partition(" ")
            self.refers = self.refers.strip()
            if self.refers:
                if self.source_path:
                    base = os.path.dirname(self.source_path)
                    if base:
                        self.refers = os.path.join(base, self.refers)

                self.refers = os.path.abspath(self.refers)

            return

        self.requirement = standard_req(line)
        if not self.requirement:
            self.comment = None  # Ensure potential comment on the line doesn't count as section
            return

        if self.parent.do_abstract and self.section != INDIRECT:
            # Abstract only very specific and simple name==version reqs, that are not in an explicitly 'pinned' section
            self.abstracted = False
            if self.section != PINNED:
                m = RE_SIMPLE_PIN.match(self.requirement)
                if m:
                    prev = self.requirement
                    name = m.group(1)
                    spec = m.group(3)
                    self.requirement = name if not spec else "%s%s" % (name, spec)
                    trace("  abstracted [%s] -> [%s]" % (prev, self.requirement))
                    self.abstracted = True

    def __repr__(self):
        result = []
        if self.editable:
            result.append("-e")

        if self.refers:
            result.append("-r %s" % (self.source or self.refers))

        elif self.requirement:
            result.append(self.requirement)

        result.append(self.source_description)
        return " ".join(result)

    @property
    def is_empty(self):
        return not self.requirement and not self.refers

    @property
    def section(self):
        return self.local_section or self.parent_section

    @property
    def source_description(self):
        msg = "from %s:%s" % (self.source or "adhoc", self.line_number)
        if self.abstracted is not None:
            if self.local_section:
                msg += ", '%s' stated on line" % self.local_section

            elif self.parent_section:
                msg += ", in '%s' section" % self.parent_section

            elif self.abstracted:
                msg += ", abstracted by default"

        return msg

    @property
    def is_ignored(self):
        return self.section == INDIRECT

    def _set_comment(self, comment):
        comment = comment.strip()
        if comment:
            self.comment = comment
            w = first_word(self.comment)
            if w in KNOWN_SECTIONS:
                return w


def non_repeat(items):
    result = []
    for i in items:
        if i and i not in result:
            result.append(i)

    return result


def iterate_req_txt(seen, parent, source_path, lines):
    if lines:
        current_section = None
        for n, line in enumerate(lines, start=1):
            req_entry = ReqEntry(parent, source_path, n, current_section, line)
            if req_entry.is_empty:
                if req_entry.parent_section:
                    # Lines containing only a comment can start a "section", all requirements below this will respect that section
                    current_section = req_entry.parent_section

                continue

            trace("  req entry: %s" % req_entry)
            if req_entry.refers and req_entry.refers not in seen:
                seen.add(req_entry.refers)
                for r in iterate_req_txt(seen, parent, req_entry.refers, readlines(req_entry.refers)):
                    yield r

            elif req_entry.requirement not in seen:
                seen.add(req_entry.requirement)
                yield req_entry


class RequirementsFile:
    """Keeps track of where requirements came from"""

    def __init__(self, do_abstract=True):
        self.do_abstract = do_abstract
        self.reqs = None
        self.abstracted = None
        self.filled_requirements = None
        self.ignored = None
        self.untouched = None
        self.source = None

    def scan(self, lines, source_path=None):
        if lines is None:
            return

        if self.reqs is None:
            self.reqs = []

        seen = set()
        if source_path:
            seen.add(source_path)

        for r in iterate_req_txt(seen, self, source_path, lines):
            self.reqs.append(r)

    def finalize(self):
        self.filled_requirements = non_repeat([r.requirement for r in self.reqs if r.requirement and not r.is_ignored])
        self.abstracted = [r for r in self.reqs if r.abstracted is True]
        self.ignored = [r for r in self.reqs if r.requirement and r.is_ignored]
        self.untouched = [r for r in self.reqs if r.abstracted is False]
        for r in self.reqs:
            if r.source:
                self.source = r.source
                break

    @classmethod
    def from_file(cls, path, do_abstract=True):
        """
        :param str path: Path to requirements.txt file to read
        :param bool do_abstract: If True, automatically abstract reqs of the form <name>==<version>
        :return RequirementsFile|None: Associated object, if possible
        """
        req = cls(do_abstract=do_abstract)
        if path:
            req.scan(readlines(path), source_path=os.path.abspath(path))

        if req.reqs is not None:
            req.finalize()
            return req

    @classmethod
    def from_lines(cls, lines, do_abstract=False, source_path=None):
        """
        :param list[str] lines: Requirement lines, as found in METADATA 'Requires-Dist:' for example
        :param bool do_abstract: If True, automatically abstract reqs of the form <name>==<version>
        :param str source_path: Reference to file where 'lines' came from
        :return RequirementsFile|None: Associated object, if possible
        """
        req = cls(do_abstract=do_abstract)
        req.scan(lines, source_path=source_path)
        if req.reqs is not None:
            req.finalize()
            return req


def find_requirements(*relative_paths):
    """Read old-school requirements.txt type file"""
    for path in relative_paths:
        if path:
            path = project_path(path)
            if os.path.isfile(path):
                do_abstract = not path.endswith(".in")
                trace("found requirements: %s %s" % (path, " (auto-abstracted)" if do_abstract else ""))
                r = RequirementsFile.from_file(path, do_abstract=do_abstract)
                if r is not None:
                    return r


class Requirements:
    """Allows to auto-fill requires from requirements.txt"""

    def __init__(self, pkg_info):
        """
        :param setupmeta.model.PackageInfo pkg_info: PKG-INFO, when available
        """
        if pkg_info:
            self.install_requires = pkg_info.get_requirements()
            if self.install_requires:
                return

        self.install_requires = find_requirements(
            "requirements.in",  # .in files are preferred when present
            "requirements.txt",
            "pinned.txt",  # To be phased out as well
        )


class current_folder:
    """
    Temporarily change current folder
    """

    def __init__(self, path):
        self.old_cwd = os.getcwd()
        self.path = path

    def __enter__(self):
        if self.path:
            os.chdir(self.path)

    def __exit__(self, *args):
        if self.path:
            os.chdir(self.old_cwd)


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
        with contextlib.suppress(OSError):
            shutil.rmtree(self.path)


def meta_command_init(self, dist, **_):
    """Custom __init__ injected to commands decorated with @MetaCommand"""
    self.setupmeta = getattr(dist, "_setupmeta", None)
    super(self.__class__, self).__init__(dist)


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

    # Fields that setuptools expects in `dist.metadata`
    metadata_fields = listify("""
        author author_email bugtrack_url classifiers description download_url extras_require install_requires
        keywords license long_description long_description_content_type
        maintainer maintainer_email name obsoletes
        platforms project_urls provides requires url version
    """)

    # Fields that setuptools expects in `dist` (some are found in both `dist.metadata` and `dist`)
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
        """Register our own 'command'"""
        command.description = command.__doc__.strip().split("\n")[0]
        command.__init__ = meta_command_init
        cls.commands.append(command)
        return command

    @classmethod
    def dist_to_dict(cls, dist):
        """
        :param setuptools.dist.Distribution dist: Distribution or attrs
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
        if key in cls.metadata_fields and hasattr(dist.metadata, key):
            setattr(dist.metadata, key, value)

        # setuptools 68.2+ needs some info in both `dist.metadata` AND `dist`, see https://github.com/thatch/debug-setupmeta
        if key in cls.dist_fields and hasattr(dist, key):
            setattr(dist, key, value)


class Console:
    """Small helper to determine terminal width, used to try and get a nice fit for commands like 'explain'"""

    _columns = None

    @classmethod
    def columns(cls, default=160):
        if cls._columns is None and sys.stdout.isatty() and "TERM" in os.environ:
            result = run_program("tput", "cols")
            cls._columns = to_int(result.stdout, default=None)

        if cls._columns is None:
            cls._columns = default

        return cls._columns
