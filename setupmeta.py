#!/usr/bin/env python
"""
This module aims to disrupt copy-paste technology in setup.py
Ideally, this should be in setuptools.setup()
"""

import glob
import inspect
import io
import logging
import os
import re
import setuptools
import shutil
import sys


__version__ = '1.0.0'
__license__ = 'Apache 2.0'
__url__ = "https://github.com/zsimic/setupmeta"
__release__ = 'archive/{version}.tar.gz'        # Relative download_url path

# Used to mark which key/values were provided explicitly in setup.py
EXPLICIT = 'explicit'

# Accept reasonable variations of name + some separator + email
R_EMAIL = re.compile(r'(.+)[\s<>()\[\],:;]+([^@]+@[a-zA-Z0-9._-]+)')

# Finds simple values of the form: __author__ = 'Someone'
R_PY_VALUE = re.compile(r'^__([a-z_]+)__\s*=\s*u?[\'"](.+)[\'"]\s*(#.+)?$')

# Finds simple docstring entries like: author: Zoran Simic
R_DOC_VALUE = re.compile(r'^([a-z_]+)\s*:\s+(.+?)(\s*#.+)?$')

# Whitelist fields to extract from modules
# Don't include everything blindly...
SIMPLE_FIELDS = """
description download_url license keywords platforms url version
author author_email
contact contact_email
maintainer maintainer_email
"""

SIMPLE_FIELDS = set(filter(bool, map(str.strip, SIMPLE_FIELDS.split())))

# These are not real attrs and don't need to be passed through
HELPER_FIELDS = set('repo release'.split())

USER_HOME = os.path.expanduser('~')


def short(text, max_chars=64):
    """ Short representation of 'text' """
    if not text:
        return text
    text = "%s" % text
    text = text.replace(USER_HOME, '~').replace('\n', ' ')
    if len(text) > max_chars:
        summary = "%s chars" % len(text)
        cutoff = max_chars - len(summary) - 6
        if cutoff <= 0:
            return summary
        return "%s [%s...]" % (summary, text[:cutoff])
    return text


def is_setup_py(path):
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

    def explain(self, form, prefix, max_chars):
        """ Representation used for 'explain' command """
        preview = short(self.value, max_chars=max_chars)
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

    def add(self, value, source, override=False):
        """
        :param value: Value to add (first value wins, unless override used)
        :param str source: Where this key/value came from
        :param bool override: If True, 'value' is forcibly taken
        """
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
        return self.key not in HELPER_FIELDS and bool(self.value)

    def explain(self, form, max_chars=200):
        """ Representation used for 'explain' command """
        result = ""
        for source in self.sources:
            prefix = "\_" if result else self.key
            result += source.explain(form, prefix, max_chars=max_chars)
        return result


class Attributes:
    """ Find usable definitions throughout a project """

    def __init__(self, attrs):
        """
        :param dict attrs: 'attrs' as received in original setup() call
        """
        self.attrs = attrs or {}
        setup_py = self.attrs.pop('_setup_py', None)
        if setup_py:
            self.project_dir = os.path.dirname(os.path.abspath(setup_py))
        else:
            self.project_dir = None

        self.definitions = {}                       # type: dict(Definition)
        self.name = self.attrs.get('name')          # type: str
        self.packages = self.attrs.get('packages')  # type: list(str)
        self.version = None                         # type: str
        self.classifiers = []                       # type: list(str)

        # Not part of usual attrs, gives extra anti copy-paste protection
        self.repo = None                            # type: str

        # Add definitions from setup()'s attrs (highest priority)
        for key, value in self.attrs.items():
            self.add_definition(key, value, EXPLICIT)

        # Auto-fill packages if need be
        if not self.packages:
            self.packages = []
            if self.name:
                self.packages.append(self.name)
                self.auto_fill('packages', self.packages)

        # Get long description from README (in this order)
        readme_paths = ['README.rst', 'README.md', 'README*']
        self.add_full_contents('long_description', readme_paths)

        if 'PYGRADLE_PROJECT_VERSION' in os.environ:
            # Convenience: support https://github.com/linkedin/pygradle
            self.add_definition(
                'version',
                os.environ['PYGRADLE_PROJECT_VERSION'],
                'pygradle'
            )

        # Scan the usual/conventional places
        if self.project_dir:
            for package in self.packages:
                if os.path.isdir(self.full_path(package)):
                    self.scan_module(os.path.join(package, '__version__.py'))
                    self.scan_module(os.path.join(package, '__init__.py'))
                else:
                    self.scan_module('%s.py' % package)
            self.scan_module('setup.py')

        # Bonus auto-fills format
        self.version = self.value('version')
        self.repo = self.value('repo')
        if self.repo and self.name:
            # Convenience: deduct github project url from repo
            parts = self.repo.split('/')
            if len(parts) == 4 and 'github.com' == parts[2]:
                self.repo = os.path.join(self.repo, self.name)

        url = self.repo or self.value('url')
        release = self.value('download_url') or self.value('release')

        if release and url and '://' not in release:
            # Convenience: support download_url relative to url
            release = os.path.join(url, release)

        if url:
            # Convenience: allow {name} in url
            url = url.format(name=self.name)

        if release:
            # Convenience: allow {name} and {version} in download_url
            release = release.format(name=self.name, version=self.version)

        self.auto_fill('url', url)
        self.auto_fill('download_url', release)

        self.auto_adjust('author', self.extract_email)
        self.auto_adjust('contact', self.extract_email)
        self.auto_adjust('maintainer', self.extract_email)

    def __repr__(self):
        project_dir = short(self.project_dir)
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
            if definition.key in self.attrs or definition.is_meaningful:
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

    def scan_module(self, source):
        """ Look for definitions in modules
        :param str path: Relative path to python module to scan for definitions
        """
        full_path = self.full_path(source)
        if not full_path or not os.path.isfile(full_path):
            return
        with io.open(full_path, encoding='utf-8') as fh:
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
                            source,
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
                self.scan_line(line, R_PY_VALUE, source, line_number)

    def scan_docstring(self, lines, source, line_number=0):
        """ Scan docstring for definitions """
        description = None
        for line in lines:
            line_number += 1
            if is_setup_py(source):
                if line.strip() and not description:
                    description = line.strip()
                    self.add_definition('description', description, source)
                    continue
                # https://pypi.python.org/pypi?%3Aaction=list_classifiers
                self.find_classifier(line)
            self.scan_line(line, R_DOC_VALUE, source, line_number)

        if is_setup_py(source) and self.classifiers:
            self.add_definition('classifiers', self.classifiers, source)

    def scan_line(self, line, regex, source, line_number):
        m = regex.match(line)
        if not m:
            return
        key = m.group(1)
        value = m.group(2)
        if key in SIMPLE_FIELDS or key in HELPER_FIELDS:
            precise_source = "%s:%s" % (source, line_number)
            self.add_definition(key, value, precise_source)

    def find_classifier(self, line):
        """ Look for classifier definition in 'line' """
        if ' :: ' in line:
            self.classifiers.append(line.strip())

    def full_path(self, relative_path):
        """ Full path corresponding to 'relative_path' """
        if not self.project_dir:
            return None
        return os.path.join(self.project_dir, relative_path)

    def add_full_contents(self, key, paths):
        """ Add full contents of 1st file found in 'paths' under 'key'

        :param str key: Key being defined
        :param list(str) paths: Paths to examine
        """
        if not self.project_dir:
            return
        candidates = []
        for path in paths:
            # De-dupe and respect order (especially for globbed paths)
            if '*' in path:
                full_path = self.full_path(path)
                for expanded in glob.glob(full_path):
                    relative_path = os.path.basename(expanded)
                    if relative_path not in candidates:
                        candidates.append(relative_path)
                continue
            if path not in candidates:
                candidates.append(path)
        for path in candidates:
            value = self.file_contents(path)
            if value:
                self.add_definition(key, value, path)
                return

    def file_contents(self, relative_path):
        """
        :param str relative_path: Path of file to examine
        :return str|None: Contents, if any
        """
        try:
            full_path = self.full_path(relative_path)
            with io.open(full_path, encoding='utf-8') as fh:
                return ''.join(fh.readlines()).strip()

        except Exception:
            return None

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


class StandardDistribution(setuptools.dist.Distribution):
    """ Our Distribution implementation that makes this possible """

    def __init__(self, attrs):
        self._attributes = Attributes(attrs)

        attrs = self._attributes.to_dict()
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
        definitions = self.distribution._attributes.definitions
        principal = []
        helpers = []
        for definition in definitions.values():
            if definition.key in HELPER_FIELDS:
                helpers.append(definition)
            else:
                principal.append(definition)
        sys.stdout.write(self.report(principal, "Definitions"))
        if helpers:
            sys.stdout.write("\n")
            sys.stdout.write(self.report(helpers, "Helpers"))

    def report(self, definitions, title):
        result = ""
        result += "%s:\n" % title
        result += "%s-\n" % ('-' * len(title))
        if definitions:
            longest_key = min(24, max(len(d.key) for d in definitions))
            sources = sum((d.sources for d in definitions), [])
            longest_source = min(32, max(len(s.source) for s in sources))
            form = "%%%ss: (%%%ss) %%s\n" % (longest_key, -longest_source)
            try:
                max_chars = int(os.environ.get('COLUMNS'))
            except Exception:
                max_chars = 160
            max_chars -= longest_key + longest_source + 4
            for definition in sorted(definitions):
                result += definition.explain(form, max_chars=max_chars)
        return result


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
            dist = self.distribution.full_path('dist')
            shutil.rmtree(dist)
        except OSError:
            pass

        print('Building Source and Wheel (universal) distribution...')
        os.system('%s setup.py sdist bdist_wheel --universal' % sys.executable)

        print('Uploading the package to PyPi via Twine...')
        os.system('twine upload dist/*')

        sys.exit()


def setup(**attrs):
    """ Drop-in replacement for setuptools.setup() """
    setup_py = attrs.pop('_setup_py', None)
    if not setup_py:
        for frame in inspect.stack():
            module = inspect.getmodule(frame[0])
            if is_setup_py(module.__file__):
                setup_py = module.__file__
                break

    distclass = attrs.pop('distclass', StandardDistribution)
    setuptools.setup(distclass=distclass, _setup_py=setup_py, **attrs)


if __name__ == "__main__":
    # Convenience: auto-upgrade self
    import argparse
    import urllib

    parser = argparse.ArgumentParser(description="Install/upgrade setupmeta")
    parser.add_argument(
        '--url',
        help="URL to get setupmeta from (default: %s)" % __url__
    )
    parser.add_argument(
        'target',
        nargs='?',
        help="Folder to install/upgrade (default: .)"
    )
    args = parser.parse_args()

    if not args.url:
        args.url = __url__.replace("github.com", "raw.githubusercontent.com")
        args.url = "%s/master/setupmeta.py" % args.url
    if not args.target:
        args.target = os.getcwd()
    f = urllib.urlopen(args.url)
    contents = f.read()
    print("%s: %s" % (type(contents), len(contents)))
    temp_target = os.path.join(args.target, 'setupmeta.py.tmp')
    with open(temp_target, 'w') as fh:
        fh.write(contents)
