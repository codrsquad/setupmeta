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
__license__ = 'Apache 2.0'
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
R_DOC_VALUE = re.compile(r'^([a-z_]+)\s*:\s+(.+?)(\s*#.+)?$')

USER_HOME = os.path.expanduser('~')     # Used to pretty-print folder in ~
PROJECT_DIR = os.getcwd()               # Determined project directory


def setup(**attrs):
    """ Drop-in replacement for setuptools.setup() """
    distclass = attrs.pop('distclass', SetupmetaDistribution)
    setuptools.setup(distclass=distclass, **attrs)


def short(text, c=64):
    """ Short representation of 'text' """
    if not text:
        return text
    text = "%s" % text
    text = text.replace(USER_HOME, '~').replace('\n', ' ')
    if c and len(text) > c:
        summary = "%s chars" % len(text)
        cutoff = c - len(summary) - 6
        if cutoff <= 0:
            return summary
        return "%s [%s...]" % (summary, text[:cutoff])
    return text


def to_str(text):
    """ Support python2 and 3 """
    if isinstance(text, bytes):
        return text.decode('utf-8')
    return text


def clean_file(path):
    """ Clean up file with 'path' """
    try:
        os.unlink(path)
    except Exception as e:
        print("Could not clean up %s: %s" % (short(path), e))


def project_path(relative_path):
    """ Full path corresponding to 'relative_path' """
    return os.path.join(PROJECT_DIR, relative_path)


def file_contents(*relative_paths):
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
        try:
            with io.open(project_path(relative_path), encoding='utf-8') as fh:
                return ''.join(fh.readlines()).strip(), relative_path

        except Exception:
            pass

    return None, None


def join(*paths):
    return os.path.join(*paths)


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
    def is_explicit(self):
        """ Did this entry come explicitly from setup(**attrs)? """
        return any(s.is_explicit for s in self.sources)

    def add_entries(self, entries):
        for entry in entries:
            if not self.value:
                self.value = entry.value
            self.sources.append(entry)

    def add(self, value, source, override=False, listify=None):
        """
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        :param str|None listify: Turn value into list
        """
        if isinstance(source, list):
            return self.add_entries(source)
        if listify and value:
            value = value.split(listify)
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

    def add_definition(self, key, value, source, override=False, listify=None):
        """
        :param str key: Key being defined
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        :param str|None listify: Turn value into list
        """
        definition = self.definitions.get(key)
        if definition is None:
            definition = Definition(key)
            self.definitions[key] = definition
        definition.add(value, source, override=override, listify=listify)

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

    def __init__(self, relative_path):
        """
        :param str path: Relative path to python module to scan for definitions
        """
        Settings.__init__(self)
        self.relative_path = relative_path
        self.full_path = project_path(relative_path)
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
                self.scan_line(line, R_PY_VALUE, line_number)

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
            mpath = join(project_path(self.name), '__init__.py')
            if os.path.isfile(mpath):
                packages = [self.name]
                self.auto_fill('packages', packages)

            mpath = join('src', project_path(self.name), '__init__.py')
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
        self.add_full_contents('classifiers', 'classifiers.txt', listify='\n')

        # Entry points are more handily described in their own file
        self.add_full_contents('entry_points', 'entry_points.ini')

        if 'PYGRADLE_PROJECT_VERSION' in os.environ:
            # Convenience: support https://github.com/linkedin/pygradle
            self.add_definition(
                'version',
                os.environ['PYGRADLE_PROJECT_VERSION'],
                'pygradle'
            )

        # Scan the usual/conventional places
        for package in packages:
            self.merge(
                SimpleModule(join(self.name, '__about__.py')),
                SimpleModule(join(self.name, '__version__.py')),
                SimpleModule(join(self.name, '__init__.py')),
                SimpleModule(join('src', self.name, '__about__.py')),
                SimpleModule(join('src', self.name, '__version__.py')),
                SimpleModule(join('src', self.name, '__init__.py')),
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
                url = join(url, self.name)

        if download_url and url and '://' not in download_url:
            # Convenience: auto-complete relative download_url
            download_url = join(url, download_url)

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

    @property
    def name(self):
        return self.value('name')

    @property
    def version(self):
        return self.value('version')

    def add_full_contents(self, key, *paths, **kwargs):
        """ Add full contents of 1st file found in 'paths' under 'key'

        :param str key: Key being defined
        :param list(str) paths: Paths to examine (globs OK)
        """
        value, path = file_contents(*paths)
        if value:
            self.add_definition(key, value, path, **kwargs)

    def auto_fill(self, field, value):
        """ Auto-fill 'field' with 'value' """
        if value and value != self.value(field):
            override = field not in self.attrs
            self.add_definition(field, value, 'auto-fill', override=override)

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
        self._setupmeta = SetupMeta(attrs)

        attrs = self._setupmeta.to_dict()
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
        print(self.distribution._setupmeta.explain())


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
        url = join(url, "master/setupmeta.py")
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
    script = 'setupmeta.py'
    sp = project_path(script)
    ts = '%s.tmp' % script
    if os.path.islink(sp):
        sys.exit("'%s' is a symlink, can't upgrade" % short(sp, c=0))

    try:
        fh = urlopen(args.url)
        contents = to_str(fh.read())

        with open(project_path(ts), 'w') as fh:
            fh.write(contents)

    except Exception as e:
        print("Could not fetch %s: %s" % (args.url, e))
        sys.exit(1)

    tm = SimpleModule(ts)
    try:
        nv = tm.value('version')
        if not nv or not tm.value('url'):
            # Sanity check what we downloaded
            sys.exit("Invalid url %s, please check %s" % (
                args.url,
                short(tm.full_path, c=0))
            )

        current, _ = file_contents(script)
        tc, _ = file_contents(ts)
        if current == tc:
            print("Already up to date, v%s" % __version__)
            sys.exit(0)

        if current:
            if args.dryrun:
                print("Would upgrade to v%s (without --dryrun)" % nv)
                sys.exit(0)
            shutil.copy(tm.full_path, sp)
            print("Upgraded to v%s" % nv)
            sys.exit(0)

        if args.dryrun:
            print("Would seed to v%s (without --dryrun)" % nv)
            sys.exit(0)

        shutil.copy(tm.full_path, sp)
        print("Seeded with v%s" % nv)
        sys.exit(0)

    finally:
        clean_file(tm.full_path)


if __name__ == "__main__":
    self_upgrade()
