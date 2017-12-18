from distutils.version import LooseVersion
import re
import warnings

import setupmeta
from setupmeta.content import project_path


RE_GIT_DESCRIBE = re.compile(r'^v?(.+?)(-\d+)?(-g\w+)?(-(dirty|broken))*$', re.IGNORECASE)


def strip_dash(text):
    if not text:
        return text
    return text.strip('-')


class Version:
    """ Parsed version, including git describe notation """

    text = None         # Given version text
    canonical = None    # Parsed canonical version from 'text'
    version = None      # Canonical LooseVersion object
    main = None         # Main part of the version
    changes = None      # Number of changes since last git tag
    commit = None       # Git commit it
    dirty = False       # True if local changes are present
    broken = False      # True if git could not output version

    def __init__(self, text):
        self.text = text.strip()
        self.canonical = text
        m = RE_GIT_DESCRIBE.match(text)
        if not m:
            self.version = LooseVersion(self.text)
            return
        self.main = m.group(1)
        self.changes = strip_dash(m.group(2))
        self.changes = int(self.changes) if self.changes else 0
        self.commit = strip_dash(m.group(3))
        self.dirty = '-dirty' in text
        self.broken = '-broken' in text
        self.version = LooseVersion(self.main)
        self.canonical = str(self.version)
        if len(self.version.version) < 3:
            # Auto-complete M.m.p with 'p' being number of changes since M.m
            self.canonical += '.%s' % self.changes
        elif self.changes:
            self.canonical += 'b%s' % self.changes
        if self.broken:
            self.canonical += 'broken'
        elif self.dirty:
            self.canonical += 'dev-%s' % self.commit
        self.version = LooseVersion(self.canonical)

    def __repr__(self):
        return repr(self.version)


def auto_fill_version(meta):
    """
    Auto-fill version using git tag
    :param setupmeta.model.SetupMeta meta: Parent meta object
    """
    gv = git_version()
    if not gv:
        return
    vdef = meta.definitions.get('version')
    cv = vdef.sources[0].value if vdef and vdef.sources else None
    if cv and not gv.canonical.startswith(cv):
        source = vdef.sources[0].source
        expected = gv.canonical[:len(cv)]
        msg = "In %s version should be %s, not %s" % (source, expected, cv)
        warnings.warn(msg)
    meta.auto_fill('version', gv.canonical, 'git', override=True)


def git_version():
    r = setupmeta.run_program(
        'git',
        'describe',
        '--tags',
        '--dirty',
        '--broken',
        '--first-parent',
        cwd=project_path()
    )
    return Version(r or '0.0')
