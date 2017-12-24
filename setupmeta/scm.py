from distutils.version import LooseVersion
import re

import setupmeta


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

    text = None         # type: str # Given version text
    version = None      # type: LooseVersion

    major = None        # type: int # Major part of version
    minor = None        # type: int # Minor part of version
    patch = None        # type: int # Patch part of version
    changes = None      # type: int # Number of changes since last tag
    commitid = None     # type: str # Commit id
    dirty = False       # type: bool # Local changes are present
    broken = False      # type: bool # Could not be properly determined

    def __init__(self, text):
        self.text = text.strip()
        m = RE_GIT_DESCRIBE.match(text)
        if not m:
            self.version = LooseVersion(self.text)
            return
        main = m.group(1)
        self.changes = strip_dash(m.group(2))
        self.changes = int(self.changes) if self.changes else 0
        self.commitid = strip_dash(m.group(3))
        self.dirty = '-dirty' in text
        self.broken = '-broken' in text
        self.version = LooseVersion(main)
        triplet = self.bump_triplet()
        self.major = triplet[0]
        self.minor = triplet[1]
        self.patch = triplet[2]

    def __repr__(self):
        return self.text

    def bump_triplet(self):
        """
        :return int, int, int: Major, minor, patch
        """
        version = list(self.version.version)
        major = version and version.pop(0) or 0
        minor = version and version.pop(0) or 0
        patch = version and version.pop(0) or 0
        return major, minor, patch

    def to_dict(self, parts=None):
        result = {}
        for key in dir(self):
            if key.startswith('_'):
                continue
            value = getattr(self, key)
            if value is None or callable(value):
                continue
            if not parts or key in parts:
                result[key] = value
            else:
                result[key] = ''
        return result

    @property
    def alpha(self):
        if self.changes:
            return 'a%s' % self.changes
        return ''

    @property
    def beta(self):
        if self.changes:
            return 'b%s' % self.changes
        return ''

    @property
    def devmarker(self):
        if self.dirty:
            return '.dev1'
        return ''


class Scm:

    def __init__(self, root):
        self.root = root

    def get_branch(self):
        pass

    def get_version(self):
        pass

    def commit_files(self, commit, relative_paths, next_version):
        pass

    def apply_tag(self, commit, branch, next_version):
        pass


class Git(Scm):

    def get_branch(self):
        branch = self.get_git_output(
            'rev-parse',
            '--abbrev-ref',
            'HEAD',
            capture=True
        )
        return branch and branch.strip()

    def get_version(self):
        r = self.get_git_output(
            'describe',
            '--tags',
            '--dirty',
            '--broken',
            '--first-parent',
            capture=True
        )
        if r and '-dirty' in r:
            # git sometimes reports -dirty when used in temp build folders
            exitcode = self.get_git_output(
                'diff',
                '--quiet',
                '--ignore-submodules',
                capture=False
            )
            if exitcode == 0 and '-dirty' in r:
                r = r.replace('-dirty', '')

        if r is None:
            return None

        return Version(r or '0.0')

    def commit_files(self, commit, relative_paths, next_version):
        if not relative_paths:
            return
        self.run_git(commit, 'add', *relative_paths)
        self.run_git(commit, 'commit', '-m', "Version %s" % next_version)

    def apply_tag(self, commit, branch, next_version):
        bump_msg = "Version %s" % next_version
        tag = "v%s" % next_version
        self.run_git(commit, 'tag', '-a', tag, '-m', bump_msg)
        self.run_git(commit, 'push', '--tags', 'origin', branch)

    def get_git_output(self, *args, **kwargs):
        return setupmeta.run_program('git', *args, cwd=self.root, **kwargs)

    def run_git(self, commit, *args):
        return self.get_git_output(*args, fatal=True, dryrun=not commit)
