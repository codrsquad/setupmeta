"""
Simplify your setup.py

See https://github.com/zsimic/setupmeta
"""

import distutils.dist
import glob
import inspect
import io
import os
import re
import setuptools
import setuptools.command.test
import shutil
import sys


__version__ = '0.0.4'
__license__ = 'MIT'
__url__ = "https://github.com/zsimic/setupmeta"
__download_url__ = 'archive/v{version}.tar.gz'
__author__ = 'Zoran Simic zoran@simicweb.com'

# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = 'explicit'
READMES = ['README.rst', 'README.md', 'README*']

# Recognized README tokens
RE_README_TOKEN = re.compile(r'(.?)\.\. \[\[([a-z]+) (.+)\]\](.)?')

# Accept reasonable variations of name + some separator + email
RE_EMAIL = re.compile(r'(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)')

# Finds simple values of the form: __author__ = 'Someone'
RE_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+?)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
RE_DOC_VALUE = re.compile(r'^([a-z_]+)\s*[:=]\s*(.+?)(\s*#.+)?$')

USER_HOME = os.path.expanduser('~')     # Used to pretty-print folder in ~
PROJECT_DIR = os.getcwd()               # Determined project directory

# Used for poor-man's toml parsing (can't afford to import toml)
CLOSERS = {'"': '"', "'": "'", '{': '}', '[': ']'}


def abort(message):
    from distutils.errors import DistutilsClassError
    raise DistutilsClassError(message)


def distutils_hook(dist, command, *args, **kwargs):
    """ distutils.dist.Distribution.get_option_dict replacement

    distutils calls this right after having processed 'setup_requires'
    It really calls self.get_option_dict(command), we jump in
    so we can decorate the 'dist' object appropriately for our own commands
    """
    if not hasattr(dist, '_setupmeta'):
        # Add our ._setupmeta object
        # (distutils calls this several times, we need only one)
        dist._setupmeta = SetupMeta(dist)
        MetaDefs.fill_dist(dist, dist._setupmeta.to_dict())
    original = MetaDefs.dd_original
    return original(dist, command, *args, **kwargs)


def register(*args, **kwargs):
    """ Hook into distutils in order to do our magic """
    if MetaDefs.dd_original is None:
        # Replace Distribution.get_option_dict so we can inject our parsing
        # This is the earliest I found after 'setup_requires' are imported
        # Do the replacement only once (distutils calls this several times...)
        MetaDefs.dd_original = distutils.dist.Distribution.get_option_dict
        distutils.dist.Distribution.get_option_dict = distutils_hook


def project_path(*relative_paths):
    """ Full path corresponding to 'relative_paths' components """
    return os.path.join(PROJECT_DIR, *relative_paths)


def load_contents(relative_path):
    """ Return contents of file with 'relative_path'

    :param str relative_path: Relative path to file
    :return str|None: Contents, if any
    """
    try:
        with io.open(project_path(relative_path), encoding='utf-8') as fh:
            return to_str(''.join(fh.readlines())).strip()

    except Exception:
        pass


def load_readme(relative_path):
    """ Loader for README files """
    content = []
    try:
        with io.open(project_path(relative_path), encoding='utf-8') as fh:
            for line in fh.readlines():
                m = RE_README_TOKEN.search(line)
                if not m:
                    content.append(line)
                    continue
                pre, post = m.group(1), m.group(4)
                pre = pre and pre.strip()
                post = post and post.strip()
                if pre or post:
                    content.append(line)
                    continue    # Not beginning/end, or no spaces around
                action = m.group(2)
                param = m.group(3)
                if action == 'end' and param == 'long_description':
                    break
                if action == 'include':
                    included = load_readme(param)
                    if included:
                        content.append(included)

            return to_str(''.join(content)).strip()

    except IOError:
        return None


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


def find_contents(relative_paths, loader=None):
    """ Return contents of first file found in 'relative_paths', globs OK

    :param list(str) relative_paths: Ex: "README.rst", "README*"
    :param callable|None loader: Optional custom loader function
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
    if loader is None:
        loader = load_contents
    for relative_path in candidates:
        contents = loader(relative_path)
        if contents:
            return contents, relative_path
    return None, None


def short(text, c=64):
    """ Short representation of 'text' """
    if not text:
        return text
    text = to_str(text).strip()
    text = text.replace(USER_HOME, '~').replace('\n', ' ')
    if c and len(text) > c:
        summary = "%s chars" % len(text)
        cutoff = c - len(summary) - 6
        if cutoff <= 0:
            return summary
        return "%s [%s...]" % (summary, text[:cutoff])
    return text


def listify(text, separator=None):
    """ Turn 'text' into a list using 'separator' """
    value = to_str(text).split(separator)
    return filter(bool, map(str.strip, value))


if sys.version_info[0] < 3:
    def strify(value):
        """ Avoid having the annoying u'..' in str() representations """
        if isinstance(value, unicode):
            return value.encode('ascii', 'ignore')
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return [strify(s) for s in value]
        if isinstance(value, tuple):
            return tuple(strify(s) for s in value)
        if isinstance(value, dict):
            return dict((strify(k), strify(v)) for (k, v) in value.items())
        return value

    def to_str(text):
        """ Pretty string representation of 'text' for python2 """
        return str(strify(text))

else:
    def to_str(text):
        """ Pretty string representation of 'text' for python3 """
        if isinstance(text, bytes):
            return text.decode('utf-8')
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
    section = sections
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
        else:
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
    contents, path = find_contents(relative_paths, loader=load_list)
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


def meta_command_init(self, dist, **kw):
    """ Custom __init__ injected to commands decorated with @MetaCommand """
    self.setupmeta = getattr(dist, '_setupmeta', None)
    if not self.setupmeta:
        abort("Missing setupmeta information")
    setuptools.Command.__init__(self, dist, **kw)


class MetaDefs:
    """
    Meta definitions
    """

    # Original distutils.dist.Distribution.get_option_dict
    dd_original = None

    # Our own commands (populated by @MetaCommand decorator)
    commands = []

    # See http://setuptools.readthedocs.io/en/latest/setuptools.html listify
    metadata_fields = listify("""
        author author_email classifiers description download_url keywords
        license long_description maintainer maintainer_email name obsoletes
        platforms provides requires url version
    """)
    dist_fields = listify("""
        cmdclass contact contact_email dependency_links eager_resources
        entry_points exclude_package_data extras_require include_package_data
        install_requires libraries long_description_content_type
        namespace_packages package_data package_dir packages py_modules
        python_requires scripts setup_requires tests_require test_suite
        zip_safe
    """)
    all_fields = metadata_fields + dist_fields

    @staticmethod
    def is_setup_py_path(path):
        """ Is 'path' pointing to a setup.py module? """
        if not path:
            return False
        # Accept also setup.pyc
        return os.path.basename(path).startswith('setup.py')

    @classmethod
    def register_command(cls, command):
        """ Register our own 'command' """
        command.description = command.__doc__.strip().split('\n')[0]
        command.__init__ = meta_command_init
        if command.initialize_options == setuptools.Command.initialize_options:
            command.initialize_options = lambda x: None
        if command.finalize_options == setuptools.Command.finalize_options:
            command.finalize_options = lambda x: None
        if not hasattr(command, 'user_options'):
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
        if key in self.ignore:
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
        return MetaDefs.is_setup_py_path(self.relative_path)

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
            self.scan_line(line, RE_DOC_VALUE, line_number)

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
                if MetaDefs.is_setup_py_path(module.__file__):
                    setup_py_path = module.__file__
                    break

        if not setup_py_path and sys.argv:
            setup_py_path = os.path.abspath(os.path.expanduser(sys.argv[0]))
            setup_py_path = os.path.dirname(setup_py_path)

        if setup_py_path:
            global PROJECT_DIR
            PROJECT_DIR = os.path.dirname(os.path.abspath(setup_py_path))

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
            if os.path.isfile(project_path(self.name, '__init__.py')):
                packages = [self.name]
                self.auto_fill('packages', packages)

            if os.path.isfile(project_path('src', self.name, '__init__.py')):
                packages = [self.name]
                self.auto_fill('packages', packages)
                self.auto_fill('package_dir', {'': 'src'})

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
        for py_module in py_modules:
            self.merge(SimpleModule('%s.py' % py_module))

        for package in packages:
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


def MetaCommand(cls):
    """ Decorator allowing for less boilerplate in our commands """
    return MetaDefs.register_command(cls)


@MetaCommand
class ExplainCommand(setuptools.Command):
    """ Show a report of where key/values setup(attr) come from """

    def run(self):
        print("Definitions:")
        print("------------")
        print(self.setupmeta.explain())


@MetaCommand
class EntryPointsCommand(setuptools.Command):
    """ List entry points for pygradle consumption """

    def run(self):
        entry_points = self.setupmeta.value('entry_points')
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


@MetaCommand
class TestCommand(setuptools.command.test.test):
    """ Run all tests via py.test """

    def run_tests(self):
        try:
            import pytest

        except ImportError:
            print('pytest is not installed, falling back to default')
            return setuptools.command.test.test.run_tests(self)

        suite = self.setupmeta.value('test_suite') or 'tests'
        args = ['-vvv'] + suite.split()
        errno = pytest.main(args)
        sys.exit(errno)


@MetaCommand
class UploadCommand(setuptools.Command):
    """ Build and publish the package """

    def run(self):
        try:
            print('Cleaning up dist...')
            dist = project_path('dist')
            shutil.rmtree(dist)
        except OSError:
            pass

        print('Building Source and Wheel (universal) distribution...')
        run_program(
            sys.executable,
            project_path('setup.py'),
            'sdist',
            'bdist_wheel',
            '--universal'
        )

        print('Uploading the package to pypi via twine...')
        os.system('twine upload dist/*')
        sys.exit()


def run_program(*commands):
    """ Run shell program 'commands' """
    import subprocess
    p = subprocess.Popen(commands)
    if p.returncode:
        sys.exit(p.returncode)
