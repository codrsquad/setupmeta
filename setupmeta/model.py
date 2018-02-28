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
from setupmeta import listify, MetaDefs, project_path, relative_path, short, trace
from setupmeta.content import find_contents, load_contents, load_list, load_readme, resolved_paths
from setupmeta.license import determined_license


# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = 'explicit'
READMES = ['README.rst', 'README.md', 'README*']

# Accept reasonable variations of name + some separator + email
RE_EMAIL = re.compile(r'(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)')

# Finds simple values of the form: __author__ = 'Someone'
RE_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+?)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
RE_DOC_VALUE = re.compile(r'^([a-z_]+)\s*[:=]\s*(.+?)(\s*#.+)?$')

# Beautify short description
RE_DESCRIPTION = re.compile(
    r'^[\W\s]*((([\w\-]+)\s*[:-])?\s*(.+))$',
    re.IGNORECASE
)


def is_setup_py_path(path):
    """ Is 'path' pointing to a setup.py module? """
    if not path:
        return False
    # Accept also setup.pyc
    return os.path.basename(path).startswith('setup.py')


def find_packages(name, subfolder=None):
    """ Find packages for 'name' (if any), 'subfolder' is like "src" """
    result = set()
    if subfolder:
        path = project_path(subfolder, name)
        trace("looking for packages in '%s/%s'" % (subfolder, name))
    else:
        path = project_path(name)
        trace("looking for packages in '%s'" % name)
    init_py = os.path.join(path, '__init__.py')
    if os.path.isfile(init_py):
        result.add(name)
        trace("found package '%s'" % name)
        for subpackage in setuptools.find_packages(where=path):
            result.add("%s.%s" % (name, subpackage))
            trace("found subpackage '%s.%s'" % (name, subpackage))
    return result


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
        self.sources = []           # type: list(DefinitionEntry)

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
                trace("[merge: %s] %s=%s" % (entry.source, self.key, entry.value))
            self.sources.append(entry)

    def add(self, value, source, override=False):
        """
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        """
        if isinstance(source, list):
            return self.merge_sources(source)
        if override or not self.value:
            self.value = value
        entry = DefinitionEntry(self.key, value, source)
        if override:
            self.sources.insert(0, entry)
            trace("[high: %s] %s=%s" % (source, self.key, short(value)))
        else:
            self.sources.append(entry)
            trace("[low: %s] %s=%s" % (source, self.key, short(value)))

    @property
    def is_meaningful(self):
        """ Should this definition make it to the final setup attrs? """
        return bool(self.value) or self.is_explicit


class Settings:
    """ Collection of key/value pairs with info on where they came from """

    def __init__(self):
        self.definitions = {}                       # type: dict(Definition)

    def __repr__(self):
        project_dir = short(MetaDefs.project_dir)
        return "%s definitions, %s" % (len(self.definitions), project_dir)

    def value(self, key):
        """ Value currently associated to 'key', if any """
        definition = self.definitions.get(key)
        if definition:
            return definition.value
        return None

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
        if key == 'keywords':
            value = listify(value, separator=',')
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
        if not self.exists:
            return

        with io.open(self.full_path, encoding='utf-8') as fh:
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
                    self.add_pair('docstring_lead', line, line_number)
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
        if not m:
            return True
        key = m.group(1)
        value = m.group(2)
        self.add_pair(key, value, line_number)


class RequirementsEntry:
    """ Keeps track of where requirements came from """

    def __init__(self, path):
        self.source = relative_path(path)
        self.reqs = load_list(path)
        self.links = None

        if any(self.is_complex_requirement(line) for line in self.reqs):
            reqs, links = self.parse_requirements(path)
            if reqs:
                self.reqs = reqs
                self.links = links

    @staticmethod
    def is_complex_requirement(line):
        """Allows to save importing pip for very simple requirements.txt files"""
        if line:
            return line.startswith('-') or ':' in line

    @staticmethod
    def parse_requirements(path):
        """Parse a requirements file with pip"""
        try:
            # Note: we can't assume pip is installed
            try:
                from pip.req import parse_requirements
                from pip.download import PipSession
            except ImportError:
                # pip 10.0
                from pip._internal.req import parse_requirements    # pragma: no cover
                from pip._internal.download import PipSession       # pragma: no cover

            reqs = []
            links = []
            session = PipSession()
            for ir in parse_requirements(path, session=session):
                if ir.link:
                    if ir.name:
                        reqs.append(ir.name)
                    links.append(ir.link.url)
                else:
                    reqs.append(str(ir.req))

            return reqs, links

        except ImportError:     # pragma: no cover
            return None, None   # pragma: no cover


class Requirements:
    """ Allows to auto-fill requires from requirements.txt """

    def __init__(self):
        self.links_source = None
        self.install = self.get_requirements('requirements.txt', 'pinned.txt')
        self.test = self.get_requirements(
            'tests/requirements.txt',
            'requirements-dev.txt',
            'dev-requirements.txt',
            'test-requirements.txt'
        )
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
    def get_requirements(*relative_paths):
        """ Read old-school requirements.txt type file """
        for path in relative_paths:
            path = project_path(path)
            if os.path.isfile(path):
                trace("found requirements: %s" % path)
                return RequirementsEntry(path)


class SetupMeta(Settings):
    """ Find usable definitions throughout a project SetupPy SetupMeta """

    def __init__(self, upstream):
        """
        :param upstream: Either a dict or Distribution
        """
        Settings.__init__(self)
        self.attrs = MetaDefs.dist_to_dict(upstream)

        self.find_project_dir(self.attrs.pop('_setup_py_path', None))
        scm = self.attrs.pop('scm', None)

        # Add definitions from setup()'s attrs (highest priority)
        for key, value in self.attrs.items():
            self.add_definition(key, value, EXPLICIT)

        # Allow to auto-fill 'name' from setup.py's __title__, if any
        self.merge(SimpleModule('setup.py'))
        title = self.definitions.get('title')
        if title:
            self.auto_fill('name', title.value, source=title.source)

        packages = self.attrs.get('packages', [])
        py_modules = self.attrs.get('py_modules', [])

        if not packages and not py_modules and self.name:
            # Try to auto-determine a good default from 'self.name'
            direct_packages = find_packages(self.name)
            src_packages = find_packages(self.name, subfolder='src')
            packages = sorted(direct_packages | src_packages)

            if src_packages:
                self.auto_fill('package_dir', {'': 'src'})
            if packages:
                self.auto_fill('packages', packages)

            if os.path.isfile(project_path('%s.py' % self.name)):
                py_modules = [self.name]
                self.auto_fill('py_modules', py_modules)

        # Scan the usual/conventional places
        for py_module in py_modules:
            self.merge(SimpleModule('%s.py' % py_module))

        for package in packages:
            if package and '.' not in package:
                # Look at top level modules only
                self.merge(
                    SimpleModule(package, '__about__.py'),
                    SimpleModule(package, '__version__.py'),
                    SimpleModule(package, '__init__.py'),
                    SimpleModule('src', package, '__about__.py'),
                    SimpleModule('src', package, '__version__.py'),
                    SimpleModule('src', package, '__init__.py'),
                )

        scm = scm or setupmeta.versioning.project_scm(MetaDefs.project_dir)
        self.versioning = setupmeta.versioning.Versioning(self, scm)
        self.versioning.auto_fill_version()

        self.fill_urls()

        self.auto_adjust('author', self.extract_email)
        self.auto_adjust('contact', self.extract_email)
        self.auto_adjust('maintainer', self.extract_email)

        self.requirements = Requirements()
        self.auto_fill_requires('install', 'install_requires')
        self.auto_fill_requires('test', 'tests_require')
        if self.requirements.links:
            self.auto_fill('dependency_links', self.requirements.links, self.requirements.links_source)

        self.auto_fill_classifiers()
        self.auto_fill_entry_points()
        self.auto_fill_license()
        self.auto_fill_long_description()
        self.sort_classifiers()

    def fill_urls(self):
        """ Auto-fill url and download_url """
        url = self.value('url')
        download_url = self.value('download_url')

        if url and self.name:
            parts = url.split('/')
            if len(parts) == 4 and 'github.com' == parts[2]:
                # Convenience: auto-complete url with package name
                url = os.path.join(url, self.name)

        if download_url and url and '://' not in download_url:
            # Convenience: auto-complete relative download_url
            download_url = os.path.join(url, download_url)

        if url:
            # Convenience: allow {name} in url
            url = url.format(name=self.name)

        if download_url:
            # Convenience: allow {name} and {version} in download_url
            download_url = download_url.format(name=self.name, version=self.version)

        self.auto_fill('url', url)
        self.auto_fill('download_url', download_url)

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
        description = contents.strip().partition('\n')[0].strip()
        size = len(description)
        if size < 4 or size > 256:
            return None
        m = RE_DESCRIPTION.match(description)
        name = (self.name or '').lower()
        if m:
            lead = m.group(3)
            if lead and lead.lower() == name:
                description = m.group(4)
            else:
                description = m.group(1)
        if len(description) < 4 or description.lower() == name:
            return None
        return description

    def auto_fill_long_description(self):
        """ Auto-fille descriptions from README file """
        docstring_lead = self.definitions.pop('docstring_lead', None)
        if docstring_lead and not self.value('description'):
            self.auto_fill('description', docstring_lead.value, source=docstring_lead.source)
        for readme in resolved_paths(READMES):
            if self.value('long_description') and self.value('description'):
                return
            value = load_readme(readme)
            if value:
                short_desc = self.extract_short_description(value)
                self.auto_fill('description', short_desc, source="%s:1" % readme)
                self.add_definition('long_description', value, readme, override=short_desc)

    def auto_fill_entry_points(self, key='entry_points'):
        path = "%s.ini" % key
        value = load_contents(path)
        if value:
            self.add_definition(key, value, path)

    def auto_fill_license(self, key='license'):
        """ Try to auto-determine the license """
        contents, _ = find_contents(['LICENSE*'], limit=20)
        short, classifier = determined_license(contents)
        if short:
            self.auto_fill('license', short)
            classifiers = self.value('classifiers')
            if classifiers and isinstance(classifiers, list):
                if classifier not in classifiers:
                    classifiers.append(classifier)

    def auto_fill_requires(self, field, attr):
        req = getattr(self.requirements, field)
        if req is not None:
            self.auto_fill(attr, req.reqs, req.source)

    @property
    def name(self):
        return self.value('name')

    @property
    def version(self):
        return self.value('version')

    def auto_fill_classifiers(self):
        """ Add classifiers from classifiers.txt, if present """
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers = load_list('classifiers.txt')
        if classifiers:
            self.add_definition('classifiers', classifiers, 'classifiers.txt')

    def sort_classifiers(self):
        """ Sort classifiers alphabetically """
        classifiers = self.definitions.get('classifiers')
        if classifiers and isinstance(classifiers.value, list):
            classifiers.value = sorted(classifiers.value)

    def auto_fill(self, field, value, source='auto-fill', override=False):
        """ Auto-fill 'field' with 'value' """
        if value is not None and (override or value != self.value(field)):
            override = override or (field not in self.attrs)
            self.add_definition(field, value, source, override=override)

    def auto_adjust(self, field, adjust):
        """ Auto-adjust 'field' using 'adjust' function """
        for key, value in adjust(field):
            if value:
                self.add_definition(key, value, 'auto-adjust', override=True)

    def extract_email(self, field):
        """ Convenience: one line user+email specification """
        field_email = field + '_email'
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
