#!/usr/bin/env python
"""
This file comes from https://github.com/zsimic/setupmeta, do not edit

Due to current limitations of setuptools,
this file has to be copied to your project folder.
See url above for how to get it / update it.

With setuptools 38.2.3+, it's becoming possible to
have this functionality come in via setup_requires=['setupmeta']
instead of direct copy in project folder.
"""

import glob
import inspect
import io
import os
import re
import setuptools
import shutil
import sys


__version__ = '0.0.1'
__license__ = 'MIT'
__url__ = "https://github.com/zsimic/setupmeta"
__author__ = 'Zoran Simic zoran@simicweb.com'

# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = 'explicit'
READMES = ['README.rst', 'README.md', 'README*']

# Accept reasonable variations of name + some separator + email
R_EMAIL = re.compile(r'(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)')

# Finds simple values of the form: __author__ = 'Someone'
R_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
R_DOC_VALUE = re.compile(r'^([a-z_]+)\s*[:=]\s*(.+?)(\s*#.+)?$')

USER_HOME = os.path.expanduser('~')     # Used to pretty-print folder in ~
PROJECT_DIR = os.getcwd()               # Determined project directory

# Used for poor-man's toml parsing (can't afford to import toml)
CLOSERS = {'"': '"', "'": "'", '{': '}', '[': ']'}


def setup(**attrs):
    """ Drop-in replacement for setuptools.setup() """
    distclass = attrs.pop('distclass', SetupmetaDistribution)
    setuptools.setup(distclass=distclass, **attrs)


def project_path(*relative_paths):
    """ Full path corresponding to 'relative_paths' components """
    return os.path.join(PROJECT_DIR, *relative_paths)


def clean_file(full_path):
    """ Clean up file with 'path' """
    try:
        os.unlink(full_path)
    except Exception as e:
        print("Could not clean up %s: %s" % (short(full_path), e))


def load_contents(relative_path):
    """ Return contents of file with 'relative_path'

    :param str relative_path: Relative path to file
    :return str|None: Contents, if any
    """
    try:
        with io.open(project_path(relative_path), encoding='utf-8') as fh:
            return ''.join(fh.readlines()).strip()

    except Exception:
        pass


def extract_list(content):
    """ List of non-comment, non-empty strings from 'content'

    :param str|unicode|None content: Text content
    :return list(str)|None: Contents, if any
    """
    if not content:
        return None
    result = []
    for line in content.strip().split('\n'):
        if '#' in line:
            i = line.index('#')
            line = line[:i]
        line = line.strip()
        if line:
            result.append(line)
    return result


def load_list(relative_path):
    """ List of non-comment, non-empty strings from file

    :param str relative_path: Relative path to file
    :return list(str)|None: Contents, if any
    """
    return extract_list(load_contents(relative_path))


def load_pipfile(relative_path):
    """ Poor-man's parsing of a pipfile, can't afford to depend on pipfile """
    return parsed_toml(load_list(relative_path))


def find_contents(*relative_paths, **kwargs):
    """ Return contents of first file found in 'relative_paths', globs OK

    :param list(str) relative_paths: Ex: "README.rst", "README*"
    :return str|None, str|None: Contents and path where they came from, if any
    """
    candidates = []
    for path in relative_paths:
        # De-dupe and respect order (especially for globbed paths)
        if '*' in path:
            for expanded in glob.glob(project_path(path)):
                relative_path = os.path.basename(expanded)
                if relative_path not in candidates:
                    candidates.append(relative_path)
            continue
        if path not in candidates:
            candidates.append(path)
    for relative_path in candidates:
        loader = kwargs.get('loader', load_contents)
        contents = loader(relative_path)
        if contents:
            return contents, relative_path
    return None, None


def short(text, c=64):
    """ Short representation of 'text' """
    if not text:
        return text
    text = to_str(text)
    text = text.replace(USER_HOME, '~').replace('\n', ' ')
    if c and len(text) > c:
        summary = "%s chars" % len(text)
        cutoff = c - len(summary) - 6
        if cutoff <= 0:
            return summary
        return "%s [%s...]" % (summary, text[:cutoff])
    return text


if sys.version_info[0] < 3:
    def to_str(text):
        """ Pretty string representation of 'text' for python2 """
        if isinstance(text, list):
            text = [to_str(s) for s in text]
            return to_str("%s" % text)
        if isinstance(text, dict):
            text = dict((to_str(k), to_str(v)) for (k, v) in text.items())
            return to_str("%s" % text)
        text = "%s" % text
        if isinstance(text, unicode):
            return text.encode('ascii', 'ignore')
        return text

else:
    def to_str(text):
        """ Pretty string representation of 'text' for python3 """
        return str(text)


def toml_key_value(line):
    line = line and line.strip()
    if not line:
        return None, None
    if '=' not in line:
        return None, line
    key, _, value = line.partition('=')
    key = key.strip()
    value = value.strip()
    if not key or not value:
        return None, None
    key = toml_key(key)
    if key is None:
        return None, line
    return key, value


def toml_accumulated_value(acc, text):
    if acc:
        return "%s %s" % (acc, text)
    return text


def is_toml_section(line):
    if not line or len(line) < 3:
        return False
    if line[0] == '[' and line[-1] == ']':
        line = line[1:-1]
        if len(line) >= 3 and line[0] == '[' and line[-1] == ']':
            line = line[1:-1]
        return toml_key(line) is not None


def normalized_toml(lines):
    """ Collapse toml multi-lines into one line """
    if not lines:
        return None
    result = []
    prev_key = None
    acc = None
    for line in lines:
        key, value = toml_key_value(line)
        if key or is_toml_section(line):
            if acc:
                if prev_key:
                    result.append("%s=%s" % (prev_key, acc))
                else:
                    result.append(acc)
                acc = None
            prev_key = key
            acc = toml_accumulated_value(acc, value)
            continue
        acc = toml_accumulated_value(acc, line)
    if prev_key:
        result.append("%s=%s" % (prev_key, acc))
    return result


def parsed_toml(text):
    """ Can't afford to require toml """
    if isinstance(text, dict):
        return text
    if text and not isinstance(text, list):
        text = text.split('\n')
    text = normalized_toml(text)
    if not text:
        return None
    sections = {}
    section = None
    for line in text:
        key, value = toml_key_value(line)
        if key is None and value is None:
            continue
        if key is None and is_toml_section(value):
            section_name = line.strip('[]')
            section = sections.get(section_name)
            if section is None:
                section = {}
                sections[section_name] = section
            continue
        section[key] = toml_value(value)
    return sections


def toml_key(text):
    text = text and text.strip()
    if not text or len(text) < 2:
        return text
    fc = text[0]
    if fc == '"' or fc == "'":
        if text[-1] != fc:
            return None
        return text[1:-1]
    return text


def toml_value(text):
    text = text and text.strip()
    if not text:
        return text
    if text.startswith('{'):
        rdict = {}
        for line in text.strip('{}').split(','):
            key, _, value = line.partition('=')
            rdict[toml_key(key)] = toml_value(value)
        return rdict
    if text.startswith('['):
        rlist = []
        for line in text.strip('[]').split(','):
            rlist.append(toml_value(line))
        return rlist
    if text.startswith('"'):
        return toml_key(text)
    if text == 'true':
        return True
    if text == 'false':
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def get_old_spec(*relative_paths):
    """ Read old-school requirements.txt type file """
    contents, path = find_contents(*relative_paths, loader=load_list)
    if contents:
        return RequirementsEntry(contents, path)
    return None


def pip_spec(name, info):
    """ Convert pipfile spec into an old-school pip-style spec """
    if not info or info == "*":
        return name
    if not isinstance(info, dict):
        return "%s%s" % (name, info)
    version = info.get('version')
    markers = info.get('markers')
    if info.get('editable'):
        # Old pips don't support this -e,
        # and I'm not sure it's useful for setup.py
        return None
    result = [name]
    if version and version != "*":
        result.append(version)
    if markers:
        result.append(" ; %s" % markers)
    return ''.join(result)


def pipfile_spec(section):
    """ Extract old-school pip-style reqs from pipfile 'section' """
    result = []
    for name, info in section.items():
        spec = pip_spec(name, info)
        if spec:
            result.append(spec)
    return sorted(result)


class Meta:
    """
    Meta things
    """

    # Whitelist simple fields to extract from modules
    # Don't include everything blindly...
    # A "simple field" is a variable assignment with a string constant
    # of the form: __var__ = 'constant value'
    simple = set(filter(bool, map(str.strip, """
        description download_url license keywords platforms url version
        author author_email
        contact contact_email
        maintainer maintainer_email
    """.split())))

    @classmethod
    def is_known(cls, name):
        """ Is field with 'name' meaningful to consider for setup()? """
        return name in cls.simple

    @staticmethod
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
        return "%s=%s from %s sources" % (
            self.key,
            short(self.value),
            len(self.sources)
        )

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

    def add_entries(self, entries):
        for entry in entries:
            if not self.value:
                self.value = entry.value
            self.sources.append(entry)

    def add(self, value, source, override=False):
        """
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        """
        if isinstance(source, list):
            return self.add_entries(source)
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
            prefix = "\_" if result else self.key
            result += source.explain(form, prefix, max_chars=max_chars)
        return result


class Settings:
    """ Collection of key/value pairs with info on where they came from """

    def __init__(self):
        self.definitions = {}                       # type: dict(Definition)

    def __repr__(self):
        project_dir = short(PROJECT_DIR)
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
        if not self.exists:
            return

        regex = R_PY_VALUE
        if self.relative_path.endswith('.properties'):
            regex = R_DOC_VALUE

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

    @property
    def is_setup_py(self):
        """ Is this a setup.py module? """
        return Meta.is_setup_py_path(self.relative_path)

    def add_pair(self, key, value, line, **kwargs):
        source = self.relative_path
        if line:
            source = "%s:%s" % (source, line)
        self.add_definition(key, value, source, **kwargs)

    def scan_docstring(self, lines, line_number=0):
        """ Scan docstring for definitions """
        description = None
        for line in lines:
            line_number += 1
            if self.is_setup_py and line.strip() and not description:
                description = line.strip()
                self.add_pair('description', description, line_number)
                continue
            self.scan_line(line, R_DOC_VALUE, line_number)

    def scan_line(self, line, regex, line_number):
        m = regex.match(line)
        if not m:
            return
        key = m.group(1)
        value = m.group(2)
        if Meta.is_known(key):
            self.add_pair(key, value, line_number)


class RequirementsEntry:
    """ Keeps track of where requirements came from """

    def __init__(self, reqs, source):
        self.reqs = reqs
        self.source = source


class Requirements:
    """ Allows to auto-fill requires from pipfile, or requirements.txt """

    def __init__(self):
        pipfile = load_pipfile('Pipfile')
        if pipfile:
            self.install = RequirementsEntry(
                pipfile_spec(pipfile.get('packages', {})),
                'Pipfile'
            )
            self.test = RequirementsEntry(
                pipfile_spec(pipfile.get('dev-packages', {})),
                'Pipfile'
            )
            return
        self.install = get_old_spec('requirements.txt', 'pinned.txt')
        self.test = get_old_spec('requirements-dev.txt')


class SetupMeta(Settings):
    """ Find usable definitions throughout a project SetupPy SetupMeta """

    def __init__(self, attrs):
        """
        :param dict attrs: 'attrs' as received in original setup() call
        """
        Settings.__init__(self)
        self.attrs = attrs or {}

        # _setup_py_path passed in by tests, or special usages
        setup_py_path = self.attrs.pop('_setup_py_path', None)

        # Add definitions from setup()'s attrs (highest priority)
        for key, value in self.attrs.items():
            self.add_definition(key, value, EXPLICIT)

        if not setup_py_path:
            # Determine path to setup.py module from call stack
            for frame in inspect.stack():
                module = inspect.getmodule(frame[0])
                if Meta.is_setup_py_path(module.__file__):
                    setup_py_path = module.__file__
                    break

        if setup_py_path:
            global PROJECT_DIR
            PROJECT_DIR = os.path.dirname(os.path.abspath(setup_py_path))

        packages = self.attrs.get('packages', [])
        py_modules = self.attrs.get('py_modules', [])

        if not packages and not py_modules and self.name:
            # Try to auto-determine a good default from 'self.name'
            mpath = project_path(self.name, '__init__.py')
            if os.path.isfile(mpath):
                packages = [self.name]
                self.auto_fill('packages', packages)

            mpath = project_path('src', self.name, '__init__.py')
            if os.path.isfile(mpath):
                packages = [self.name]
                self.auto_fill('packages', packages)
                self.auto_fill('package_dir', {'': 'src'})

            if os.path.isfile(project_path('%s.py' % self.name)):
                py_modules = [self.name]
                self.auto_fill('py_modules', py_modules)

        # Get long description from README (in this order)
        self.add_full_contents('long_description', *READMES)

        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        self.add_classifiers()

        # Entry points are more handily described in their own file
        self.add_full_contents('entry_points', 'entry_points.ini')

        if 'PYGRADLE_PROJECT_VERSION' in os.environ:
            # Convenience: support https://github.com/linkedin/pygradle
            self.add_definition(
                'version',
                os.environ['PYGRADLE_PROJECT_VERSION'],
                'pygradle'
            )
        elif os.path.isfile(project_path('gradle.properties')):
            # Convenience: calling pygradle setup.py outside of pygradle
            props = SimpleModule('gradle.properties')
            vdef = props.definitions.get('version')
            if vdef:
                self.add_definition(
                    vdef.key,
                    vdef.value,
                    vdef.source
                )

        # Scan the usual/conventional places
        for package in packages:
            self.merge(
                SimpleModule(package, '__about__.py'),
                SimpleModule(package, '__version__.py'),
                SimpleModule(package, '__init__.py'),
                SimpleModule('src', package, '__about__.py'),
                SimpleModule('src', package, '__version__.py'),
                SimpleModule('src', package, '__init__.py'),
            )

        for py_module in py_modules:
            self.merge(SimpleModule('%s.py' % py_module))

        self.merge(SimpleModule('setup.py'))

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

        self.requirements = Requirements()
        self.auto_fill_requires('install', 'install_requires')
        self.auto_fill_requires('test', 'tests_require')

    def auto_fill_requires(self, field, attr):
        req = getattr(self.requirements, field)
        if not req:
            return
        self.auto_fill(
            attr,
            req.reqs,
            req.source,
        )

    @property
    def name(self):
        return self.value('name')

    @property
    def version(self):
        return self.value('version')

    def add_full_contents(self, key, *paths):
        """ Add full contents of 1st file found in 'paths' under 'key'

        :param str key: Key being defined
        :param list(str) paths: Paths to examine (globs OK)
        """
        value, path = find_contents(*paths)
        if value:
            self.add_definition(key, value, path)

    def add_classifiers(self):
        """ Add classifiers from classifiers.txt, if present """
        classifiers = load_list('classifiers.txt')
        if classifiers:
            classifiers = '\n'.join(classifiers)
            self.add_definition('classifiers', classifiers, 'classifiers.txt')

    def auto_fill(self, field, value, source='auto-fill'):
        """ Auto-fill 'field' with 'value' """
        if value and value != self.value(field):
            override = field not in self.attrs
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
        m = R_EMAIL.match(user)
        if m:
            yield field, m.group(1)
            yield field_email, m.group(2)


class SetupmetaDistribution(setuptools.dist.Distribution):
    """ Our Distribution implementation that makes this possible """

    def __init__(self, attrs):
        self.setupmeta = SetupMeta(attrs)

        attrs = self.setupmeta.to_dict()
        customize_commands(attrs)

        setuptools.dist.Distribution.__init__(self, attrs)


def customize_commands(attrs):
    """ Customize commands defined in 'attrs' """
    cmdclass = attrs.get('cmdclass')
    if cmdclass is None:
        cmdclass = {}
        attrs['cmdclass'] = cmdclass
    for name, obj in globals().items():
        if inspect.isclass(obj) and issubclass(obj, setuptools.Command):
            name = obj.__name__.lower().replace('command', '')
            if obj.__doc__:
                desc = obj.__doc__.strip()
                if desc:
                    obj.description = desc[0].lower() + desc[1:]
            if name not in cmdclass:
                cmdclass[name] = obj


class ExplainCommand(setuptools.Command):
    """ Show a report of where key/values setup(attr) come from """

    user_options = []

    def initialize_options(self):
        """ Not needed """

    def finalize_options(self):
        """ Not needed """

    def run(self):
        print("Definitions:")
        print("------------")
        print(self.distribution.setupmeta.explain())


class EntryPointsCommand(setuptools.Command):
    """ List entry points for pygradle consumption """

    user_options = []

    def initialize_options(self):
        """ Not needed """

    def finalize_options(self):
        """ Not needed """

    def run(self):
        entry_points = self.distribution.setupmeta.value('entry_points')
        entry_points = parsed_toml(entry_points)
        if not entry_points:
            return
        console_scripts = entry_points.get('console_scripts')
        if not console_scripts:
            return
        if isinstance(console_scripts, list):
            for ep in console_scripts:
                print(ep)
            return
        for key, value in console_scripts.items():
            print("%s = %s" % (key, value))


class UploadCommand(setuptools.Command):
    """ Build and publish the package """

    user_options = []

    def initialize_options(self):
        """ Not needed """

    def finalize_options(self):
        """ Not needed """

    def run(self):
        try:
            print('Removing previous builds...')
            dist = project_path('dist')
            shutil.rmtree(dist)
        except OSError:
            pass

        print('Building Source and Wheel (universal) distribution...')
        os.system('%s setup.py sdist bdist_wheel --universal' % sys.executable)

        print('Uploading the package to PyPi via Twine...')
        os.system('twine upload dist/*')

        sys.exit()


def default_upgrade_url(url=__url__):
    """ Default upgrade url, friendly for test customizations """
    url = url.replace("github.com", "raw.githubusercontent.com")
    if 'raw.github' in url and not url.endswith('setupmeta.py'):
        url = os.path.join(url, 'master/setupmeta.py')
    return url


def self_upgrade(*argv):
    """ Install/upgrade setupmeta """

    global PROJECT_DIR
    import argparse

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    parser = argparse.ArgumentParser(description=self_upgrade.__doc__.strip())
    parser.add_argument(
        '-u', '--url',
        default=default_upgrade_url(),
        help="URL to get setupmeta from (default: %(default)s)"
    )
    parser.add_argument(
        '-n', '--dryrun',
        action='store_true',
        help="Don't actually install, simply check for updates"
    )
    parser.add_argument(
        'target',
        default='.',
        nargs='?',
        help="Folder to install/upgrade (default: %(default)s)"
    )
    args = parser.parse_args(*argv)

    args.target = os.path.abspath(os.path.expanduser(args.target))
    if not os.path.isdir(args.target):
        sys.exit("'%s' is not a valid directory" % args.target)

    PROJECT_DIR = args.target
    csm = SimpleModule('setupmeta.py')  # current script module
    rsmlp = 'setupmeta.tmp'             # remote script module local path
    if os.path.islink(csm.full_path):
        # Symlink is convenient when iterating on setupmeta itself:
        # I symlink setupmeta.py to my own checkout of the main setupmeta...
        short_path = short(csm.full_path, c=0)
        sys.exit("'%s' is a symlink, can't upgrade" % short_path)

    try:
        fh = urlopen(args.url)
        contents = to_str(fh.read())

        with open(project_path(rsmlp), 'w') as fh:
            fh.write(contents)

    except Exception as e:
        print("Could not fetch %s: %s" % (args.url, e))
        sys.exit(1)

    rsm = SimpleModule(rsmlp)           # remote script module
    try:
        nv = rsm.value('version')
        if not nv or not rsm.value('url'):
            # Sanity check what we downloaded
            sys.exit("Invalid url %s, please check %s" % (
                args.url,
                short(rsm.full_path, c=0))
            )

        current = load_contents(csm.relative_path)
        tc = load_contents(rsmlp)
        if current == tc:
            print("Already up to date, v%s" % __version__)
            sys.exit(0)

        if current:
            if args.dryrun:
                print("Would upgrade to v%s (without --dryrun)" % nv)
                sys.exit(0)
            shutil.copy(rsm.full_path, csm.full_path)
            print("Upgraded to v%s" % nv)
            sys.exit(0)

        if args.dryrun:
            print("Would seed to v%s (without --dryrun)" % nv)
            sys.exit(0)

        shutil.copy(rsm.full_path, csm.full_path)
        print("Seeded with v%s" % nv)
        sys.exit(0)

    finally:
        clean_file(rsm.full_path)


if __name__ == "__main__":
    self_upgrade()
