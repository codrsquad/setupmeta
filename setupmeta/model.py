"""
Model of our view on how setup.py + files in a project can come together
"""

import inspect
import io
import os
import re
import sys

from setupmeta.content import find_contents, find_packages, listify
from setupmeta.content import load_list, load_readme
from setupmeta.content import MetaDefs, project_path, short, to_str
from setupmeta.license import determined_license
from setupmeta.pipfile import load, Pipfile


# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = 'explicit'
READMES = ['README.rst', 'README.md', 'README*']

# Accept reasonable variations of name + some separator + email
RE_EMAIL = re.compile(r'(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)')

# Finds simple values of the form: __author__ = 'Someone'
RE_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+?)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
RE_DOC_VALUE = re.compile(r'^([a-z_]+)\s*[:=]\s*(.+?)(\s*#.+)?$')


def get_old_spec(*relative_paths):
    """ Read old-school requirements.txt type file """
    contents, path = find_contents(relative_paths, loader=load_list)
    if contents:
        return RequirementsEntry(contents, path)
    return None


def is_setup_py_path(path):
    """ Is 'path' pointing to a setup.py module? """
    if not path:
        return False
    # Accept also setup.pyc
    return os.path.basename(path).startswith('setup.py')


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

    def explain(self, form, prefix, max_chars):
        """ Representation used for 'explain' command """
        preview = short(self.value, c=max_chars)
        return form % (prefix, self.source, preview)


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
            if not self.value:
                self.value = entry.value
            if not self.sources or self.key != 'description':
                # Count 1st line in docstring as description only once
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
        else:
            self.sources.append(entry)

    @property
    def is_meaningful(self):
        """ Should this definition make it to the final setup attrs? """
        return bool(self.value) or self.is_explicit

    def explain(self, form, max_chars=200):
        """ Representation used for 'explain' command """
        result = ""
        for source in self.sources:
            if result:
                prefix = "\_"
            elif self.key not in MetaDefs.all_fields:
                prefix = "%s*" % self.key
            else:
                prefix = self.key
            result += source.explain(form, prefix, max_chars=max_chars)
        return result


class Settings:
    """ Collection of key/value pairs with info on where they came from """

    def __init__(self):
        self.definitions = {}                       # type: dict(Definition)
        # Keys to ignore, optionally
        self.ignore = set()                         # type: set(str)

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
        if not key or not value or key in self.ignore:
            return
        definition = self.definitions.get(key)
        if definition is None:
            definition = Definition(key)
            self.definitions[key] = definition
        definition.add(value, source, override=override)

    def merge(self, *others):
        """ Merge settings from 'others' """
        for other in others:
            for definition in other.definitions.values():
                self.add_definition(
                    definition.key,
                    definition.value,
                    definition.sources
                )

    def explain(self, max_chars=160):
        result = ""
        if not self.definitions:
            return result
        longest_key = min(24, max(len(key) for key in self.definitions))
        sources = sum((d.sources for d in self.definitions.values()), [])
        longest_source = min(32, max(len(s.source) for s in sources))
        form = "%%%ss: (%%%ss) %%s\n" % (longest_key, -longest_source)
        max_chars -= longest_key + longest_source + 4
        for definition in sorted(self.definitions.values()):
            result += definition.explain(form, max_chars=max_chars)
        return result


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
        self.description = None
        if not self.exists:
            return

        regex = RE_PY_VALUE
        if self.relative_path.endswith('.properties'):
            regex = RE_DOC_VALUE

        with io.open(self.full_path, encoding='utf-8') as fh:
            docstring_marker = None
            docstring_start = None
            docstring = []
            line_number = 0
            for line in fh:
                line_number += 1
                line = to_str(line).rstrip()
                if docstring_marker:
                    if line.endswith(docstring_marker):
                        docstring_marker = None
                        self.scan_docstring(
                            docstring,
                            line_number=docstring_start - 1
                        )
                        continue
                    docstring.append(line)
                    continue
                if line.startswith('"""') or line.startswith("'''"):
                    docstring_start = line_number
                    docstring_marker = line[:3]
                    docstring.append(line[3:])
                    continue
                self.scan_line(line, regex, line_number)

    def add_pair(self, key, value, line, **kwargs):
        source = self.relative_path
        if line:
            source = "%s:%s" % (source, line)
        self.add_definition(key, value, source, **kwargs)

    def scan_docstring(self, lines, line_number=0):
        """ Scan docstring for definitions """
        if not lines:
            return
        if not lines[0]:
            # Disregard the 1st empty line, it's very common
            lines.pop(0)
            line_number += 1
        for line in lines:
            line_number += 1
            line = line.rstrip()
            if self.description is None:
                # Count as description only 1st lines that seem reasonable
                if len(line) < 5 or not line[0].isalnum():
                    self.description = ''
                else:
                    self.description = (line, line_number)
            else:
                self.scan_line(line, RE_DOC_VALUE, line_number)
        if self.description:
            description, line_number = self.description
            self.add_pair('description', description, line_number)

    def scan_line(self, line, regex, line_number):
        m = regex.match(line)
        if not m:
            return
        key = m.group(1)
        value = m.group(2)
        self.add_pair(key, value, line_number)


class RequirementsEntry:
    """ Keeps track of where requirements came from """

    def __init__(self, reqs, source):
        if isinstance(reqs, Pipfile):
            self.source = 'Pipfile'
            self.reqs = []
            section = reqs.data.get(source, {})
            for name, info in section.items():
                spec = pip_spec(name, info)
                if spec:
                    self.reqs.append(spec)
            self.reqs = sorted(self.reqs)
        else:
            self.reqs = reqs
            self.source = source


def pip_spec(name, info):
    """ Convert pipfile spec into an old-school pip-style spec """
    if not info or info == "*":
        return name
    if not isinstance(info, dict):
        return "%s%s" % (name, info)
    version = info.get('version')
    markers = info.get('markers')
    if info.get('editable') or version is None:
        # Old pips don't support editable + not really useful when publishing
        return None
    result = [name]
    if version and version != "*":
        result.append(version)
    if markers:
        result.append(" ; %s" % markers)
    return ''.join(result)


class Requirements:
    """ Allows to auto-fill requires from pipfile, or requirements.txt """

    def __init__(self):
        pipfile_path = project_path('Pipfile')
        if os.path.isfile(pipfile_path):
            pipfile = load(pipfile_path)
            if pipfile and pipfile.data:
                self.install = RequirementsEntry(pipfile, 'default')
                self.test = RequirementsEntry(pipfile, 'develop')
                return
        self.install = get_old_spec('requirements.txt', 'pinned.txt')
        self.test = get_old_spec(
            'requirements-dev.txt',
            'dev-requirements.txt',
            'test-requirements.txt'
        )


class SetupMeta(Settings):
    """ Find usable definitions throughout a project SetupPy SetupMeta """

    def __init__(self, upstream):
        """
        :param upstream: Either a dict or Distribution
        """
        Settings.__init__(self)
        self.attrs = MetaDefs.dist_to_dict(upstream)

        # _setup_py_path passed in by tests, or special usages
        setup_py_path = self.attrs.pop('_setup_py_path', None)

        # Add definitions from setup()'s attrs (highest priority)
        for key, value in self.attrs.items():
            self.add_definition(key, value, EXPLICIT)

        if not setup_py_path:
            # Determine path to setup.py module from call stack
            for frame in inspect.stack():
                module = inspect.getmodule(frame[0])
                if module and is_setup_py_path(module.__file__):
                    setup_py_path = module.__file__
                    break

        if not setup_py_path and sys.argv:
            if is_setup_py_path(sys.argv[0]):
                setup_py_path = sys.argv[0]

        if is_setup_py_path(setup_py_path):
            setup_py_path = os.path.abspath(setup_py_path)
            MetaDefs.project_dir = os.path.dirname(setup_py_path)

        if self.value('use_scm_version'):
            # Don't look for version, let setuptools_scm do its thing
            self.ignore.add('version')

        # Allow to auto-fill 'name' from setup.py's __title__, if any
        self.merge(SimpleModule('setup.py'))
        title = self.definitions.get('title')
        if title:
            self.auto_fill('name', title.value, source=title.source)

        packages = self.attrs.get('packages', [])
        py_modules = self.attrs.get('py_modules', [])

        if not packages and not py_modules and self.name:
            # Try to auto-determine a good default from 'self.name'
            packages = find_packages(self.name)
            if packages:
                self.auto_fill('packages', packages)

            packages = find_packages(self.name, subfolder='src')
            if packages:
                self.auto_fill('packages', packages)
                self.auto_fill('package_dir', {'': 'src'})

            packages = self.value('packages') or []

            if os.path.isfile(project_path('%s.py' % self.name)):
                py_modules = [self.name]
                self.auto_fill('py_modules', py_modules)

        # Get long description from README (in this order)
        self.add_full_contents(
            'long_description',
            READMES,
            loader=load_readme
        )

        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        self.add_classifiers()

        # Entry points are more handily described in their own file
        self.add_full_contents('entry_points', ['entry_points.ini'])

        pygradle_version = os.environ.get('PYGRADLE_PROJECT_VERSION')
        if pygradle_version:
            # Convenience: support https://github.com/linkedin/pygradle
            self.add_definition('version', pygradle_version, 'pygradle')
        elif os.path.isfile(project_path('gradle.properties')):
            # Convenience: calling pygradle setup.py outside of pygradle
            props = SimpleModule('gradle.properties')
            vdef = props.definitions.get('version')
            if vdef:
                self.add_definition(vdef.key, vdef.value, vdef.source)

        # Scan the usual/conventional places
        for py_module in py_modules:
            self.merge(SimpleModule('%s.py' % py_module))

        for package in packages:
            if not package or '.' in package:
                # Don't look at submodules
                continue
            self.merge(
                SimpleModule(package, '__about__.py'),
                SimpleModule(package, '__version__.py'),
                SimpleModule(package, '__init__.py'),
                SimpleModule('src', package, '__about__.py'),
                SimpleModule('src', package, '__version__.py'),
                SimpleModule('src', package, '__init__.py'),
            )

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
            download_url = download_url.format(
                name=self.name,
                version=self.version
            )

        self.auto_fill('url', url)
        self.auto_fill('download_url', download_url)

        self.auto_adjust('author', self.extract_email)
        self.auto_adjust('contact', self.extract_email)
        self.auto_adjust('maintainer', self.extract_email)
        self.listify('keywords:,')

        self.requirements = Requirements()
        self.auto_fill_requires('install', 'install_requires')
        self.auto_fill_requires('test', 'tests_require')

        if os.path.isdir(project_path('tests')):
            self.auto_fill('test_suite', 'tests')

        self.auto_fill_license()

    def auto_fill_license(self, key='license'):
        """ Try to auto-determine the license """
        if self.value(key):
            return
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
        if req:
            self.auto_fill(attr, req.reqs, req.source)

    def listify(self, *keys):
        """ Ensure values for 'keys' are lists """
        for key in keys:
            key, _, sep = key.partition(':')
            definition = self.definitions.get(key)
            if not definition or not definition.value:
                continue
            if isinstance(definition.value, list):
                continue
            value = listify(definition.value, separator=sep or None)
            definition.sources[0].value = definition.value = value

    @property
    def name(self):
        return self.value('name')

    @property
    def version(self):
        return self.value('version')

    def add_full_contents(self, key, paths, loader=None):
        """ Add full contents of 1st file found in 'paths' under 'key'

        :param str key: Key being defined
        :param list(str) paths: Paths to examine (globs OK)
        :param callable|None loader: Optional custom loader function
        """
        value, path = find_contents(paths, loader=loader)
        if value:
            self.add_definition(key, value, path)

    def add_classifiers(self):
        """ Add classifiers from classifiers.txt, if present """
        classifiers = load_list('classifiers.txt')
        if classifiers:
            self.add_definition('classifiers', classifiers, 'classifiers.txt')

    def auto_fill(self, field, value, source='auto-fill', override=False):
        """ Auto-fill 'field' with 'value' """
        if value and value != self.value(field):
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
