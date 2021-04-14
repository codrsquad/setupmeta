"""
Model of our view on how setup.py + files in a project can come together
"""

import inspect
import io
import os
import re
import sys

import setuptools

from setupmeta import current_folder, get_words, listify, MetaDefs, PKGID, project_path, readlines, relative_path
from setupmeta import Requirements, requirements_from_file, short, trace, warn
from setupmeta.content import find_contents, load_contents, load_readme, resolved_paths
from setupmeta.license import determined_license
from setupmeta.versioning import project_scm, Versioning

try:
    basestring

except NameError:
    basestring = str


# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = "explicit"
READMES = ["README.rst", "README.md", "README*"]

# Accept reasonable variations of name + some separator + email
RE_EMAIL = re.compile(r"(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)")

# Finds simple values of the form: __author__ = 'Someone'
RE_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+?)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
RE_DOC_VALUE = re.compile(r"^([a-z_]+)\s*[:=]\s*(.+?)(\s*#.+)?$")

# Match PKG-INFO metadata, of the form: Some-Key: some value
RE_PKG_KEY_VALUE = re.compile(r"^(%s):\s?(.*)$" % PKGID)

# Beautify short description
RE_DESCRIPTION = re.compile(r"^[\W\s]*((([\w\-]+)\s*[:-])?\s*(.+))$", re.IGNORECASE)


def is_setup_py_path(path):
    """ Is 'path' pointing to a setup.py module? """
    if path:
        # Accept also setup.pyc
        return os.path.basename(path).startswith("setup.py")


def content_type_from_filename(filename):
    """Determined content type from 'filename'"""
    if filename:
        if filename.endswith(".rst"):
            return "text/x-rst"
        if filename.endswith(".md"):
            return "text/markdown"
    return None


class DefinitionEntry:
    """ Record of where a definition was found and where it came from """

    def __init__(self, key, value, source):
        """
        :param str key: Key (for setuptools.setup()) being defined
        :param value: Value
        :param str source: Source where this definition entry was found
        """
        self.key = key
        self.value = value
        self.source = source

    def __repr__(self):
        return "%s=%s from %s" % (self.key, short(self.value), self.source)

    @property
    def is_explicit(self):
        """ Did this entry come explicitly from setup(**attrs)? """
        return self.source == EXPLICIT


class Definition(object):
    """ Record definitions for a given key, and where they were found """

    def __init__(self, key):
        """
        :param str key: Key being defined
        """
        self.key = key
        self.value = None
        self.sources = []  # type: list[DefinitionEntry]

    def __repr__(self):
        if len(self.sources) == 1:
            source = self.sources[0].source
        else:
            source = "%s sources" % len(self.sources)
        return "%s=%s from %s" % (self.key, short(self.value), source)

    def __eq__(self, other):
        return isinstance(other, Definition) and self.key is other.key

    def __lt__(self, other):
        return isinstance(other, Definition) and self.key < other.key

    @property
    def actual_source(self):
        """Actual source, first non-adjusted source"""
        for source in self.sources:
            if source.source and not source.source.startswith("auto-"):
                return source.source

    @property
    def source(self):
        """ Winning source """
        if self.sources:
            return self.sources[0].source

    @property
    def is_explicit(self):
        """ Did this entry come explicitly from setup(**attrs)? """
        return any(s.is_explicit for s in self.sources)

    def merge_sources(self, sources):
        """ Record the fact that we saw this definition in 'sources' """
        for entry in sources:
            if not self.value and entry.value:
                self.value = entry.value
                trace("[-- %s] %s=%s" % (entry.source, self.key, entry.value))
            self.sources.append(entry)

    def add(self, value, source, override=False):
        """
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        """
        if isinstance(source, list):
            self.merge_sources(source)
            return
        if override or not self.value:
            self.value = value
        entry = DefinitionEntry(self.key, value, source)
        if override:
            self.sources.insert(0, entry)
            trace("[<- %s] %s=%s" % (source, self.key, short(value)))
        else:
            self.sources.append(entry)
            trace("[-> %s] %s=%s" % (source, self.key, short(value)))

    @property
    def is_meaningful(self):
        """ Should this definition make it to the final setup attrs? """
        return self.value is not None or self.is_explicit


class Settings:
    """ Collection of key/value pairs with info on where they came from """

    def __init__(self):
        self.definitions = {}  # type: dict[str, Definition]

    def __repr__(self):
        project_dir = short(MetaDefs.project_dir)
        return "%s definitions, %s" % (len(self.definitions), project_dir)

    def value(self, key):
        """ Value currently associated to 'key', if any """
        definition = self.definitions.get(key)
        return definition and definition.value

    def to_dict(self, only_meaningful=True):
        """ Resolved attributes to pass to setuptools """
        result = {}
        for definition in self.definitions.values():
            if not only_meaningful or definition.is_meaningful:
                result[definition.key] = definition.value
        return result

    def add_definition(self, key, value, source, override=False):
        """
        :param str key: Key being defined
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        """
        if key and (value or override):
            if key in ("keywords", "setup_requires"):
                value = listify(value, separator=",")
            definition = self.definitions.get(key)
            if definition is None:
                definition = Definition(key)
                self.definitions[key] = definition
            definition.add(value, source, override=override)

    def merge(self, *others):
        """ Merge settings from 'others' """
        for other in others:
            for definition in other.definitions.values():
                self.add_definition(definition.key, definition.value, definition.sources)


class SimpleModule(Settings):
    """ Simple settings extracted from a module, such as __about__.py """

    def __init__(self, *relative_paths):
        """
        :param list(str) relative_paths: Relative path to scan for definitions
        """
        Settings.__init__(self)
        self.relative_path = os.path.join(*relative_paths)
        self.full_path = project_path(*relative_paths)
        self.exists = os.path.isfile(self.full_path)
        if self.exists:
            with io.open(self.full_path, "rt") as fh:
                docstring_marker = None
                docstring_start = None
                docstring = []
                line_number = 0
                for line in fh:
                    line_number += 1
                    line = line.rstrip()
                    if docstring_marker:
                        if line.endswith(docstring_marker):
                            docstring_marker = None
                            if docstring:
                                self.scan_docstring(docstring, line_number=docstring_start - 1)
                        else:
                            docstring.append(line)
                        continue
                    if line.startswith('"""') or line.startswith("'''"):
                        docstring_marker = line[:3]
                        if len(line) > 3 and line.endswith(docstring_marker):
                            # Single docstring line edge case
                            docstring_marker = None
                            continue
                        docstring_start = line_number
                        docstring.append(line[3:])
                        continue
                    self.scan_line(line, RE_PY_VALUE, line_number)

    def add_pair(self, key, value, line, **kwargs):
        if key and value:
            source = self.relative_path
            if line:
                source = "%s:%s" % (source, line)
            self.add_definition(key, value, source, **kwargs)

    def scan_docstring(self, lines, line_number=0):
        """ Scan docstring for definitions """
        if not lines[0]:
            # Disregard the 1st empty line, it's very common
            lines.pop(0)
            line_number += 1
        if lines and lines[0]:
            if not RE_DOC_VALUE.match(lines[0]):
                # Take first non-empty, non key-value line as docstring lead
                line = lines.pop(0).rstrip()
                line_number += 1
                if len(line) > 5 and line[0].isalnum():
                    self.add_pair("docstring_lead", line, line_number)
        if lines and not lines[0]:
            # Skip blank line after lead, if any
            lines.pop(0)
            line_number += 1
        for line in lines:
            line_number += 1
            line = line.rstrip()
            if not line or self.scan_line(line, RE_DOC_VALUE, line_number):
                # Look at first paragraph after lead only
                break

    def scan_line(self, line, regex, line_number):
        """ Scan 'line' using 'regex', return True if no match found """
        m = regex.match(line)
        if m:
            key = m.group(1)
            value = m.group(2)
            self.add_pair(key, value, line_number)
            return False
        return True


def get_pip():  # pragma: no cover, see https://github.com/pypa/setuptools/issues/2355
    """
    Deprecated, see https://github.com/codrsquad/setupmeta/issues/49
    Left around for a while because some callers import this, they will have to adapt to pip 20.1+
    """
    try:
        # pip >= 19.3
        from pip._internal.req import parse_requirements
        from pip._internal.network.session import PipSession

        return parse_requirements, PipSession

    except ImportError:
        pass

    try:
        # pip >= 10.0
        from pip._internal.req import parse_requirements
        from pip._internal.download import PipSession

        return parse_requirements, PipSession

    except ImportError:
        pass

    try:
        # pip < 10.0
        from pip.req import parse_requirements
        from pip.download import PipSession

        return parse_requirements, PipSession

    except ImportError:
        from setupmeta import warn

        warn("Can't find PipSession, won't auto-fill requirements")
        return None, None


def pythonified_name(name):
    if name:
        words = get_words(name)
        name = "_".join(s for s in words if s)

    return name


class PackageInfo:
    """Retrieves info from PKG-INFO"""

    _canonical_names = {
        "classifier": "classifiers",
        "description": "long_description",
        "description_content_type": "long_description_content_type",
        "home_page": "url",
        "summary": "description",
    }
    _list_types = {"classifiers", "long_description"}

    def __init__(self, root):
        self.path = os.path.join(root, "PKG-INFO")
        self.info = {}
        self.name = None
        self.entry_points_txt = None
        self.requires_txt = None
        lines = readlines(self.path)
        if not lines:
            return

        # Parse PKG-INFO when present
        key = None
        for line_number, line in enumerate(lines, start=1):
            m = RE_PKG_KEY_VALUE.match(line)
            if m:
                key = m.group(1).lower().replace("-", "_")
                key = self._canonical_names.get(key, key)
                if key not in MetaDefs.all_fields:
                    continue

                value = m.group(2)
                if key in self._list_types:
                    if key not in self.info:
                        self.info[key] = []

                    self.info[key].append(value)

                else:
                    self.info[key] = value

            elif key in self._list_types:
                # Indented description applying to previous key
                self.info[key].append(line[8:].rstrip())

            elif line.strip():
                trace("Unknown format line %s in %s: %s" % (line_number, self.path, line))

        self.name = self.info.get("name")
        self.pythonified_name = pythonified_name(self.name)
        self.info["long_description"] = "\n".join(self.info.get("long_description", []))
        self.load_more_info(root)

    def load_more_info(self, folder, depth=3):
        """
        :param str folder: Folder to scan for .egg-info file
        :param int depth: Do not scan folder for more than 'depth'
        :return bool: True when .egg-info was found and leveraged
        """
        if not self.name or not os.path.isdir(folder) or depth <= 0:
            return False

        path = os.path.join(folder, "%s.egg-info" % self.pythonified_name)
        if os.path.isdir(path):
            self.entry_points_txt = self.checked_file(path, "entry_points.txt")
            self.requires_txt = self.checked_file(path, "requires.txt")
            return True

        for fname in os.listdir(folder):
            if self.load_more_info(os.path.join(folder, fname), depth=depth - 1):
                return True

    def checked_file(self, folder, filename):
        """
        :param str folder: Folder
        :param str filename: Basename
        :return str|None: Full path to file, if it exists
        """
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path


class SetupMeta(Settings):
    """ Find usable definitions throughout a project SetupPy SetupMeta """

    def __init__(self):
        """
        :param upstream: Either a dict or Distribution
        """
        Settings.__init__(self)
        self.attrs = {}

    def preprocess(self, upstream):
        self.find_project_dir(MetaDefs.dist_to_dict(upstream).pop("_setup_py_path", None))

        for require_field in ("install_requires", "tests_require"):
            value = getattr(upstream, require_field)
            if isinstance(value, basestring) and value.startswith("@"):
                self.add_definition(require_field, value, EXPLICIT)
                self.add_definition(require_field, requirements_from_file(value[1:]) or [], source=value[1:], override=True)

        if isinstance(upstream.extras_require, dict):
            if any([isinstance(deps, basestring) and deps.startswith("@") for deps in upstream.extras_require.values()]):
                self.add_definition("extras_require", upstream.extras_require, EXPLICIT)
                self.add_definition("extras_require", {
                        extra: (requirements_from_file(deps[1:]) or []) if isinstance(deps, basestring) and deps.startswith("@") else deps
                        for extra, deps in upstream.extras_require.items()
                    }, "preprocessed", override=True)

        return self

    def finalize(self, upstream):
        self.attrs.update(MetaDefs.dist_to_dict(upstream))

        self.find_project_dir(self.attrs.pop("_setup_py_path", None))
        scm = self.attrs.pop("scm", None)

        # Add definitions from setup()'s attrs (highest priority)
        for key, value in self.attrs.items():
            if key not in self.definitions:
                self.add_definition(key, value, EXPLICIT)

        # Add definitions from PKG-INFO, when available
        self.pkg_info = PackageInfo(MetaDefs.project_dir)
        for key, value in self.pkg_info.info.items():
            if key in MetaDefs.all_fields:
                self.add_definition(key, value, relative_path(self.pkg_info.path))

        # Allow to auto-fill 'name' from setup.py's __title__, if any
        self.merge(SimpleModule("setup.py"))
        title = self.definitions.get("title")
        if title:
            self.auto_fill("name", title.value, source=title.source)

        if "--name" in sys.argv[1:3]:
            # No need to waste time auto-filling anything if all we need to show is package name
            return self

        packages = self.attrs.get("packages", [])
        py_modules = self.attrs.get("py_modules", [])

        if not packages and not py_modules and self.name:
            # Try to auto-determine a good default from 'self.name'
            name = self.pythonified_name
            src_folder = project_path("src")
            if os.path.isdir(src_folder):
                trace("looking for src packages in %s" % src_folder)
                packages = setuptools.find_packages(where=src_folder)
                if not packages and os.path.isfile(project_path("src", "%s.py" % name)):
                    py_modules = [name]

                if packages or py_modules:
                    self.auto_fill("package_dir", {"": "src"})

            else:
                src_folder = project_path()
                if os.path.isdir(src_folder):
                    trace("looking for direct packages in %s" % src_folder)
                    with current_folder(src_folder):
                        raw_packages = setuptools.find_packages()
                        if raw_packages:
                            # Keep only packages that start with the expected name
                            # For any other use-case, user must explicitly list their packages
                            packages = [p for p in raw_packages if p.startswith(name)]
                            if packages != raw_packages:
                                trace("all packages found: %s" % raw_packages)

                if not packages and os.path.isfile(project_path("%s.py" % name)):
                    py_modules = [name]

            if packages:
                self.auto_fill("packages", sorted(packages))

            if py_modules:
                self.auto_fill("py_modules", py_modules)

        # Scan the usual/conventional places
        for py_module in py_modules:
            self.merge(SimpleModule("%s.py" % py_module))

        for package in packages:
            if package and "." not in package:
                # Look at top level modules only
                self.merge(
                    SimpleModule(package, "__about__.py"),
                    SimpleModule(package, "__version__.py"),
                    SimpleModule(package, "__init__.py"),
                    SimpleModule("src", package, "__about__.py"),
                    SimpleModule("src", package, "__version__.py"),
                    SimpleModule("src", package, "__init__.py"),
                )

        if not self.name:
            warn("'name' not specified in setup.py, auto-fill will be incomplete")

        elif not self.definitions.get("packages") and not self.definitions.get("py_modules"):
            warn("No 'packages' or 'py_modules' defined, this is an empty python package")

        scm = scm or project_scm(MetaDefs.project_dir)
        self.versioning = Versioning(self, scm)
        self.versioning.auto_fill_version()

        self.fill_urls()

        self.auto_adjust("author", self.extract_email)
        self.auto_adjust("contact", self.extract_email)
        self.auto_adjust("maintainer", self.extract_email)

        self.requirements = Requirements(self.pkg_info)
        self.auto_fill_requires("install_requires")
        self.auto_fill_requires("tests_require")
        self.auto_fill_entry_points()
        self.auto_fill_license()
        self.auto_fill_long_description()
        self.auto_fill_include_package_data()

        return self

    def resolved_url(self, url, base=None):
        """
        :param str|None url: Url to resolve
        :return str|None: Resolve {name} and {version} markers in given url
        """
        if base and url and "://" not in url:
            # Convenience: auto-complete relative urls
            url = os.path.join(base, url)

        return url and url.format(name=self.name, version=self.version)

    def fill_urls(self):
        """ Auto-fill url and download_url """
        url = self.value("url")
        download_url = self.value("download_url")
        bugtrack_url = self.value("bugtrack_url")

        if url and self.name:
            parts = [s for s in url.split("/") if s]
            if 3 <= len(parts) <= 4 and parts[1] == "github.com":
                # Convenience: auto-complete url with package name
                if len(parts) == 3:
                    url = os.path.join(url, "{name}")

                if not bugtrack_url:
                    bugtrack_url = os.path.join(url, "issues")

        self.auto_fill("url", self.resolved_url(url))
        self.auto_fill("download_url", self.resolved_url(download_url, base=url))
        self.auto_fill("bugtrack_url", self.resolved_url(bugtrack_url, base=url))

    def find_project_dir(self, setup_py_path):
        """
        :param str|None setup_py_path: Given setup.py (when invoked from test)
        """
        if not setup_py_path:
            # Determine path to setup.py module from call stack
            for frame in inspect.stack():
                module = inspect.getmodule(frame[0])
                if module and is_setup_py_path(module.__file__):
                    setup_py_path = module.__file__
                    trace("setup.py found from call stack: %s" % setup_py_path)
                    break

        if not setup_py_path and sys.argv:
            if is_setup_py_path(sys.argv[0]):
                setup_py_path = sys.argv[0]
                trace("setup.py found from sys.argv: %s" % setup_py_path)

        if is_setup_py_path(setup_py_path):
            setup_py_path = os.path.abspath(setup_py_path)
            MetaDefs.project_dir = os.path.dirname(setup_py_path)
            trace("project dir: %s" % MetaDefs.project_dir)

    def extract_short_description(self, contents):
        """
        :param str contents: Readme file contents
        :return str|None:
        """
        description = contents.strip().partition("\n")[0].strip()
        size = len(description)
        if 4 <= size <= 256:
            m = RE_DESCRIPTION.match(description)
            candidates = set([s.lower() for s in (self.name, self.pythonified_name) if s])
            if m:
                lead = m.group(3)
                description = m.group(4 if lead and lead.lower() in candidates else 1)
            if len(description) >= 4 and description.lower() not in candidates:
                return description

    def auto_fill_long_description(self):
        """ Auto-fille descriptions from README file """
        docstring_lead = self.definitions.pop("docstring_lead", None)
        if docstring_lead and not self.value("description"):
            self.auto_fill("description", docstring_lead.value, source=docstring_lead.source)
        best_content_type = None
        best_readme = None
        best_long = None
        for readme in resolved_paths(READMES):
            value = load_readme(readme)
            if not value:
                continue
            short_desc = self.extract_short_description(value)
            if not best_long or len(best_long) < 512 <= len(value):
                # The best README is the 1st one found
                best_content_type = content_type_from_filename(readme)
                best_readme = readme
                best_long = value
            if short_desc:
                self.auto_fill("description", short_desc, source="%s:1" % readme)
                break
        self.add_definition("long_description", best_long, best_readme)
        self.add_definition("long_description_content_type", best_content_type, best_readme)

    def auto_fill_entry_points(self, key="entry_points"):
        if self.pkg_info.entry_points_txt:
            self.add_definition(key, load_contents(self.pkg_info.entry_points_txt), relative_path(self.pkg_info.entry_points_txt))
        path = "%s.ini" % key
        self.add_definition(key, load_contents(path), path)

    def auto_fill_license(self, key="license"):
        """ Try to auto-determine the license """
        contents, _ = find_contents(["LICENSE*"], limit=20)
        short = determined_license(contents)
        if short:
            self.auto_fill("license", short)

    def auto_fill_requires(self, field):
        req = getattr(self.requirements, field)
        if req:
            self.auto_fill(field, req.filled_requirements, req.source)

    @property
    def name(self):
        return self.value("name")

    @property
    def pythonified_name(self):
        return pythonified_name(self.name)

    @property
    def version(self):
        return self.value("version")

    def auto_fill_include_package_data(self):
        """Auto-fill 'include_package_data' if a MANIFEST.in file exists in project"""
        if "include_package_data" not in self.attrs:
            manifest = os.path.join(MetaDefs.project_dir, "MANIFEST.in")
            if os.path.isfile(manifest):
                self.add_definition("include_package_data", True, os.path.basename(manifest))

    def auto_fill(self, field, value, source="auto-fill", override=False):
        """ Auto-fill 'field' with 'value' """
        if value and (override or value != self.value(field)):
            override = override or field not in self.attrs
            self.add_definition(field, value, source, override=override)

    def auto_adjust(self, field, adjust):
        """ Auto-adjust 'field' using 'adjust' function """
        for key, value in adjust(field):
            self.add_definition(key, value, "auto-adjust", override=True)

    def extract_email(self, field):
        """ Convenience: one line user+email specification """
        field_email = field + "_email"
        user_email = self.value(field_email)
        if user_email:
            # Caller already separated email, nothing to do
            return
        user = self.value(field)
        if not user:
            return
        m = RE_EMAIL.match(user)
        if m:
            yield field, m.group(1)
            yield field_email, m.group(2)
