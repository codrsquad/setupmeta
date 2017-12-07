"""
Functionality related to interacting with project and distutils content
"""

import glob
import io
import os
import re
import setuptools
import sys


# Recognized README tokens
RE_README_TOKEN = re.compile(r'(.?)\.\. \[\[([a-z]+) (.+)\]\](.)?')

USER_HOME = os.path.expanduser('~')     # Used to pretty-print folder in ~


def abort(message):
    from distutils.errors import DistutilsClassError
    raise DistutilsClassError(message)


def project_path(*relative_paths):
    """ Full path corresponding to 'relative_paths' components """
    return os.path.join(MetaDefs.project_dir, *relative_paths)


def find_packages(name, subfolder=None):
    """ Find packages for 'name' (if any), 'subfolder' is like "src" """
    result = None
    if subfolder:
        path = project_path(subfolder, name)
    else:
        path = project_path(name)
    init_py = os.path.join(path, '__init__.py')
    if os.path.isfile(init_py):
        result = [name]
        for subpackage in setuptools.find_packages(where=path):
            result.append("%s.%s" % (name, subpackage))
    return result


def load_contents(relative_path, limit=0):
    """ Return contents of file with 'relative_path'

    :param str relative_path: Relative path to file
    :param int limit: Max number of lines to load
    :return str|None: Contents, if any
    """
    try:
        with io.open(project_path(relative_path), encoding='utf-8') as fh:
            lines = []
            for line in fh:
                limit -= 1
                if limit == 0:
                    break
                lines.append(line)
            return to_str(''.join(lines)).strip()

    except IOError:
        pass


def load_readme(relative_path, limit=0):
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
                    included = load_readme(param, limit=limit)
                    if included:
                        content.append(included)

            return to_str(''.join(content)).strip()

    except IOError:
        return None


def extract_list(content, comment='#'):
    """ List of non-comment, non-empty strings from 'content'

    :param str|None content: Text content
    :param str|None comment: Optional comment marker
    :return list(str)|None: Contents, if any
    """
    if not content:
        return None
    result = []
    for line in content.strip().split('\n'):
        if comment and comment in line:
            i = line.index(comment)
            line = line[:i]
        line = line.strip()
        if line:
            result.append(line)
    return result


def load_list(relative_path, comment='#', limit=0):
    """ List of non-comment, non-empty strings from file

    :param str relative_path: Relative path to file
    :param str|None comment: Optional comment marker
    :param int limit: Max number of lines to load
    :return list(str)|None: Contents, if any
    """
    return extract_list(
        load_contents(relative_path, limit=limit),
        comment=comment
    )


def find_contents(relative_paths, loader=None, limit=0):
    """ Return contents of first file found in 'relative_paths', globs OK

    :param list(str) relative_paths: Ex: "README.rst", "README*"
    :param callable|None loader: Optional custom loader function
    :param int limit: Max number of lines to load
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
        contents = loader(relative_path, limit=limit)
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


def meta_command_init(self, dist, **kw):
    """ Custom __init__ injected to commands decorated with @MetaCommand """
    self.setupmeta = getattr(dist, '_setupmeta', None)
    if not self.setupmeta:
        abort("Missing setupmeta information")
    setuptools.Command.__init__(self, dist, **kw)


def MetaCommand(cls):
    """ Decorator allowing for less boilerplate in our commands """
    return MetaDefs.register_command(cls)


class MetaDefs:
    """
    Meta definitions
    """

    # Original distutils.dist.Distribution.get_option_dict
    dd_original = None

    # Our own commands (populated by @MetaCommand decorator)
    commands = []

    # Determined project directory
    project_dir = os.getcwd()

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
