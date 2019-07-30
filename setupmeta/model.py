"""
Model of our view on how setup.py + files in a project can come together
"""

import inspect
import io
import os
import re
import sys

import setuptools

import setupmeta.versioning
from setupmeta import listify, MetaDefs, project_path, relative_path, short, temp_resource, trace
from setupmeta.content import find_contents, load_contents, load_list, load_readme, resolved_paths
from setupmeta.license import determined_license


# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = "explicit"
CLASSIFIERS = "classifiers.txt"
READMES = ["README.rst", "README.md", "README*"]

RE_WORDS = re.compile(r"[^\w]+")

# Accept reasonable variations of name + some separator + email
RE_EMAIL = re.compile(r"(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)")

# Finds simple values of the form: __author__ = 'Someone'
RE_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+?)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
RE_DOC_VALUE = re.compile(r"^([a-z_]+)\s*[:=]\s*(.+?)(\s*#.+)?$")

# Beautify short description
RE_DESCRIPTION = re.compile(r"^[\W\s]*((([\w\-]+)\s*[:-])?\s*(.+))$", re.IGNORECASE)

KNOWN_SECTIONS = set("abstract pinned indirect".split())


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


def is_setup_py_path(path):
    """ Is 'path' pointing to a setup.py module? """
    if path:
        # Accept also setup.pyc
        return os.path.basename(path).startswith("setup.py")


def find_packages(name, subfolder=None):
    """ Find packages for 'name' (if any), 'subfolder' is like "src" """
    result = set()
    if subfolder:
        path = project_path(subfolder, name)
        trace("looking for packages in '%s/%s'" % (subfolder, name))
    else:
        path = project_path(name)
        trace("looking for packages in '%s'" % name)
    init_py = os.path.join(path, "__init__.py")
    if os.path.isfile(init_py):
        result.add(name)
        trace("found package '%s'" % name)
        for subpackage in setuptools.find_packages(where=path):
            result.add("%s.%s" % (name, subpackage))
            trace("found subpackage '%s.%s'" % (name, subpackage))
    return result


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
        return bool(self.value) or self.is_explicit


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

    def to_dict(self):
        """ Resolved attributes to pass to setuptools """
        result = {}
        for definition in self.definitions.values():
            if definition.is_meaningful:
                result[definition.key] = definition.value
        return result

    def add_definition(self, key, value, source, override=False):
        """
        :param str key: Key being defined
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        """
        if key and value:
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


def get_pip():
    """We can't assume pip is installed"""
    try:
        # pip < 10.0
        from pip.req import parse_requirements
        from pip.download import PipSession

        return parse_requirements, PipSession

    except ImportError:
        pass

    try:
        # pip >= 10.0
        from pip._internal.req import parse_requirements
        from pip._internal.download import PipSession

        return parse_requirements, PipSession

    except ImportError:
        setupmeta.warn("Can't find PipSession, won't auto-fill requirements")
        return None, None


def parse_requirements(requirements):
    """Parse requirements with pip"""
    # Note: we can't assume pip is installed
    pip_parse_requirements, pip_session = get_pip()
    if not pip_parse_requirements or not requirements:
        return None, None

    reqs = []
    links = []
    session = pip_session()
    try:
        if not isinstance(requirements, list):
            # Parse given file path as-is (when not abstracting)
            for ir in pip_parse_requirements(requirements, session=session):
                if ir.link:
                    if ir.name:
                        reqs.append(ir.name)
                    links.append(ir.link.url)
                else:
                    reqs.append(str(ir.req))

            return reqs, links

        with temp_resource(is_folder=False) as temp:
            # Passed list is "complex reqs" that were not abstracted by the simple convention described here:
            # https://github.com/zsimic/setupmeta/blob/master/docs/requirements.rst
            with open(temp, "wt") as fh:
                fh.write("\n".join(requirements))

            for ir in pip_parse_requirements(temp, session=session):
                if ir.link:
                    if ir.name:
                        reqs.append(ir.name)
                    links.append(ir.link.url)
                else:
                    reqs.append(str(ir.req))

    except Exception:
        return None, None

    return reqs, links


def is_complex_requirement(line):
    """Allows to save importing pip for very simple requirements.txt files"""
    return line and (line.startswith("-") or ":" in line)


def pythonified_name(name):
    if name:
        words = [s.strip() for s in RE_WORDS.split(name)]
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
    _list_types = ["classifiers", "long_description"]

    def __init__(self, root):
        self.path = os.path.join(root, "PKG-INFO")
        self.info = {}
        self.name = None
        self.dependency_links_txt = None
        self.entry_points_txt = None
        self.requires_txt = None
        lines = load_contents(self.path)
        if not lines:
            return

        # Parse PKG-INFO when present
        line_number = 0
        key = None
        for line in lines.split("\n"):
            line_number += 1
            if line.startswith(" "):
                self.info[key].append(line[8:])
                continue

            if ": " in line:
                key, _, value = line.partition(": ")
                key = self.canonical_key(key)
                if key is None:
                    continue
                if key in self._list_types:
                    if key not in self.info:
                        self.info[key] = []
                    self.info[key].append(value)

                else:
                    self.info[key] = value

                continue

            setupmeta.trace("Unknown format line %s in %s: %s" % (line_number, self.path, line))

        self.name = self.info.get("name")
        self.pythonified_name = pythonified_name(self.name)
        self.info["long_description"] = "\n".join(self.info.get("long_description", []))
        self.load_more_info(root)

    def canonical_key(self, key):
        """
        :param str key: Key from PKG-INFO
        :return str|None: Corresponding key for setuptools.setup(), if any
        """
        key = key.lower().replace("-", "_")
        key = self._canonical_names.get(key, key)
        if key in MetaDefs.all_fields:
            return key

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
            self.dependency_links_txt = self.checked_file(path, "dependency_links.txt")
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


class RequirementsEntry:
    """ Keeps track of where requirements came from """

    def __init__(self, path, abstract=False):
        """
        :param str path: Path to req file
        :param bool abstract: If True, abstract away simple pinning (applicable to install_requires only)
        """
        self.source = relative_path(path)
        self.notes = {}
        self.reqs = []
        self.abstracted = []
        self.untouched = []
        self.ignored = []

        if abstract:
            self.parse_with_comments()

        else:
            reqs, links = parse_requirements(self.source)
            if reqs:
                self.reqs = reqs
                self.links = links

    def parse_with_comments(self):
        # We're abstracting, allow comments to tweak how we do that
        current_section = None
        for line in load_list(self.source, comment=None):
            if line.startswith("#"):
                # Lines containing only a comment can start a "section", all requirements below this will respect that section
                word = first_word(line[1:])
                if word in KNOWN_SECTIONS:
                    current_section = word
                continue

            line_section = current_section
            note = None
            if "# " in line:
                # Trailing comments can direct us to treat that particular line in a certain way regarding pinning
                i = line.index("# ")
                word = first_word(line[i + 2:])
                line = line[:i].strip()
                if word in KNOWN_SECTIONS:
                    line_section = word
                    note = "'%s' stated on line" % word

            if line_section == "indirect":
                # 'indirect' means the pinning was done to satisfy some indirect dependency,
                # but should not be considered as our project's dep
                self.ignored.append("%s # %s" % (line, note or "indirect section"))
                continue

            if (not line_section or line_section == "abstract") and "==" in line:
                # By default (or if in explicit 'abstract' section), trim away simple '==' pinning
                i = line.index("==")
                line = line[:i].strip()
                if not note:
                    if line_section:
                        note = "in '%s' section" % line_section
                    else:
                        note = "abstracted by default"
                self.abstracted.append("%s # %s" % (line, note))

            elif line and (line[0].isalnum() or line.startswith("-e")):
                # Count as untouched only actual deps (ignore flags such as -i)
                if note:
                    self.untouched.append("%s # %s" % (line, note))
                else:
                    self.untouched.append(line)

            if note:
                self.notes[line] = note or "abstract by default"

            self.reqs.append(line)

        self.links = None

        if any(is_complex_requirement(line) for line in self.reqs):
            reqs, links = parse_requirements(self.reqs)
            if reqs:
                self.reqs = reqs
                self.links = links


class Requirements:
    """ Allows to auto-fill requires from requirements.txt """

    def __init__(self, pkg_info):
        """
        :param PackageInfo pkg_info: PKG-INFO, when available
        """
        self.links_source = None
        self.install = self.get_requirements(True, pkg_info.requires_txt, "requirements.txt", "pinned.txt")
        self.test = self.get_requirements(
            False,
            "tests/requirements.txt",  # Preferred
            "requirements-dev.txt",  # Also accept other common variations
            "dev-requirements.txt",
            "test-requirements.txt",
            "requirements-test.txt",
        )

        if pkg_info.dependency_links_txt:
            self.links_source = setupmeta.relative_path(pkg_info.dependency_links_txt)
            self.links = load_list(pkg_info.dependency_links_txt)

        else:
            self.links = []
            self.add_links(self.install)
            self.add_links(self.test)

    def add_links(self, entries):
        if entries and entries.links:
            if not self.links_source:
                self.links_source = entries.source
            for link in entries.links:
                if link not in self.links:
                    self.links.append(link)

    @staticmethod
    def get_requirements(abstract, *relative_paths):
        """ Read old-school requirements.txt type file """
        for path in relative_paths:
            if path:
                path = project_path(path)
                if os.path.isfile(path):
                    trace("found requirements: %s" % path)
                    return RequirementsEntry(path, abstract=abstract)


class SetupMeta(Settings):
    """ Find usable definitions throughout a project SetupPy SetupMeta """

    def __init__(self, upstream):
        """
        :param upstream: Either a dict or Distribution
        """
        Settings.__init__(self)
        self.attrs = MetaDefs.dist_to_dict(upstream)

        self.find_project_dir(self.attrs.pop("_setup_py_path", None))
        scm = self.attrs.pop("scm", None)

        # Add definitions from setup()'s attrs (highest priority)
        for key, value in self.attrs.items():
            self.add_definition(key, value, EXPLICIT)

        # Add definitions from PKG-INFO, when available
        self.pkg_info = PackageInfo(MetaDefs.project_dir)
        for key, value in self.pkg_info.info.items():
            if key in MetaDefs.all_fields:
                self.add_definition(key, value, setupmeta.relative_path(self.pkg_info.path))

        # Allow to auto-fill 'name' from setup.py's __title__, if any
        self.merge(SimpleModule("setup.py"))
        title = self.definitions.get("title")
        if title:
            self.auto_fill("name", title.value, source=title.source)

        packages = self.attrs.get("packages", [])
        py_modules = self.attrs.get("py_modules", [])

        if not packages and not py_modules and self.name:
            # Try to auto-determine a good default from 'self.name'
            name = self.pythonified_name
            direct_packages = find_packages(name)
            src_packages = find_packages(name, subfolder="src")
            packages = sorted(direct_packages | src_packages)

            if src_packages:
                self.auto_fill("package_dir", {"": "src"})
            if packages:
                self.auto_fill("packages", packages)

            if os.path.isfile(project_path("%s.py" % name)):
                py_modules = [name]
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

        scm = scm or setupmeta.versioning.project_scm(MetaDefs.project_dir)
        self.versioning = setupmeta.versioning.Versioning(self, scm)
        self.versioning.auto_fill_version()

        self.fill_urls()

        self.auto_adjust("author", self.extract_email)
        self.auto_adjust("contact", self.extract_email)
        self.auto_adjust("maintainer", self.extract_email)

        self.requirements = Requirements(self.pkg_info)
        self.auto_fill_requires("install", "install_requires")
        self.auto_fill_requires("test", "tests_require")
        if self.requirements.links:
            self.auto_fill("dependency_links", self.requirements.links, self.requirements.links_source)

        self.auto_fill_classifiers()
        self.auto_fill_entry_points()
        self.auto_fill_license()
        self.auto_fill_long_description()
        self.sort_classifiers()

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
            self.add_definition(key, load_contents(self.pkg_info.entry_points_txt), setupmeta.relative_path(self.pkg_info.entry_points_txt))
        path = "%s.ini" % key
        self.add_definition(key, load_contents(path), path)

    def auto_fill_license(self, key="license"):
        """ Try to auto-determine the license """
        contents, _ = find_contents(["LICENSE*"], limit=20)
        short, classifier = determined_license(contents)
        if short:
            self.auto_fill("license", short)
            classifiers = self.value("classifiers")
            if classifiers and isinstance(classifiers, list):
                if classifier not in classifiers:
                    classifiers.append(classifier)

    def auto_fill_requires(self, field, attr):
        req = getattr(self.requirements, field)
        if req:
            self.auto_fill(attr, req.reqs, req.source)

    @property
    def name(self):
        return self.value("name")

    @property
    def pythonified_name(self):
        return pythonified_name(self.name)

    @property
    def version(self):
        return self.value("version")

    def auto_fill_classifiers(self):
        """ Add classifiers from classifiers.txt, if present """
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        self.add_definition("classifiers", load_list(CLASSIFIERS), CLASSIFIERS)

    def sort_classifiers(self):
        """ Sort classifiers alphabetically """
        classifiers = self.definitions.get("classifiers")
        if classifiers and isinstance(classifiers.value, list):
            classifiers.value = sorted(classifiers.value)

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
