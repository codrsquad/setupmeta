from distutils.version import LooseVersion
from io import open
import os
import re
import warnings

import setupmeta
from setupmeta.content import project_path


# Output expected from git describe
RE_GIT_DESCRIBE = re.compile(
    r'^v?(.+?)(-\d+)?(-g\w+)?(-(dirty|broken))*$',
    re.IGNORECASE
)


def strip_dash(text):
    """ Strip leading dashes from 'text' """
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
    auto_patch = False  # True if patch number deduced from number of changes

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
        self.main = LooseVersion(self.main)
        self.canonical = str(self.version)
        if len(self.version.version) < 3:
            # Auto-complete M.m.p with 'p' being number of changes since M.m
            self.canonical += '.%s' % self.changes
            self.auto_patch = True
        elif self.changes:
            self.canonical += 'b%s' % self.changes
        if self.broken:
            self.canonical += 'broken'
        if self.dirty:
            self.canonical += 'dev'
            if self.commit:
                self.canonical += '-%s' % self.commit
        self.version = LooseVersion(self.canonical)

    def __repr__(self):
        return setupmeta.to_str(self.canonical)


def auto_fill_version(meta):
    """
    Auto-fill version using git tag
    :param setupmeta.model.SetupMeta meta: Parent meta object
    """
    gv = git_version(try_pkg=True)
    if not gv:
        return
    if gv.broken:
        warnings.warn("Invalid git version tag: %s" % gv.text)
        return
    vdef = meta.definitions.get('version')
    cv = vdef.sources[0].value if vdef and vdef.sources else None
    if cv and not gv.canonical.startswith(cv):
        source = vdef.sources[0].source
        expected = gv.canonical[:len(cv)]
        msg = "In %s version should be %s, not %s" % (source, expected, cv)
        warnings.warn(msg)
    meta.auto_fill('version', gv.canonical, 'git', override=True)


def git_version(try_pkg=False):
    r = get_git_output(
        'describe',
        '--tags',
        '--dirty',
        '--broken',
        '--first-parent'
    )

    if r is None and try_pkg:
        r = get_pkg_version()

    if r:
        return Version(r)

    return None


def get_pkg_version():
    full_path = project_path('PKG-INFO')
    if not os.path.isfile(full_path):
        return None

    with open(full_path, 'rt') as fh:
        for line in fh.readlines():
            if line.startswith('Version:'):
                s = line.strip().split()
                if len(s) > 1:
                    return "%sP" % s[1]

    return None


def bump(meta, bump_major, bump_minor, bump_patch, commit):
    versioning = meta.value('versioning')
    if not versioning or not versioning.startswith('tag'):
        raise Exception("Project not configured to use setupmeta versioning")

    flags = bump_major + bump_minor + bump_patch
    if flags == 0 or flags > 1:
        raise Exception("Specify exactly one of --major, --minor or --patch")

    gv = git_version()
    if not gv:
        raise Exception("Could not determine version from git tags")
    if gv.broken:
        raise Exception("Invalid git version tag: %s" % gv.text)

    if bump_patch and gv.auto_patch:
        raise Exception("Can't bump patch number, it's auto-filled")

    major, minor, rev = gv.version.version[:3]
    if bump_major:
        major, minor, rev = (major + 1, 0, 0)
    elif bump_minor:
        major, minor, rev = (major, minor + 1, 0)
    else:
        major, minor, rev = (major, minor, rev + 1)

    if gv.auto_patch:
        next_version = "%s.%s" % (major, minor)
    else:
        next_version = "%s.%s.%s" % (major, minor, rev)

    update_sources(meta, next_version, commit)

    bump_msg = "Version %s" % next_version
    run_git(commit, 'tag', '-a', next_version, '-m', bump_msg)
    run_git(commit, 'push', '--tags')


def update_sources(meta, next_version, commit):
    vdefs = meta.definitions.get('version')
    if not vdefs:
        return None

    modified = []
    for vdef in vdefs.sources:
        if '.py:' not in vdef.source:
            continue

        relative_path, _, target_line_number = vdef.source.partition(':')
        full_path = project_path(relative_path)
        target_line_number = int(target_line_number)

        lines = []
        line_number = 0
        with open(full_path, 'rt') as fh:
            for line in fh.readlines():
                line_number += 1
                if line_number == target_line_number:
                    revised = updated_line(line, next_version, vdef)
                    if revised is None:
                        lines = None
                        break
                    if revised != line:
                        line = revised
                lines.append(line)

        if lines:
            modified.append(relative_path)
            with open(full_path, 'wt') as fh:
                fh.writelines(lines)

    if modified:
        run_git(commit, 'add', *modified)
        run_git(commit, 'commit', '-m', "Version %s" % next_version)


def updated_line(line, next_version, vdef):
    if line.startswith('version'):
        return "version: %s\n" % next_version

    if line.startswith('__version__'):
        return "__version__ = '%s'\n" % next_version

    if '=' in line:
        return "%s='%s',\n" % (line.partition('=')[0], next_version)

    warnings.warn("Unknown line format %s: %s" % (vdef.source, line))
    return None


def get_git_output(*args, **kwargs):
    if not os.path.isdir(project_path('.git')):
        return None
    return setupmeta.run_program('git', *args, cwd=project_path(), **kwargs)


def run_git(commit, *args):
    return get_git_output(*args, mode=None if commit else 'dryrun')
