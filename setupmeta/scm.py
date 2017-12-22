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

    text = None         # Given version text
    canonical = None    # Parsed canonical version from 'text'
    version = None      # Canonical LooseVersion object
    main = None         # Main part of the version
    changes = None      # Number of changes since last tag
    commit_id = None    # Commit id
    dirty = False       # True if local changes are present
    broken = False      # True if version could not be properly determined
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
        self.commit_id = strip_dash(m.group(3))
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
            self.canonical += '.broken'
        if self.dirty:
            self.canonical += '.dev1'
        self.version = LooseVersion(self.canonical)

    def __repr__(self):
        return self.canonical


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
        if commit:
            return self.get_git_output(*args, fatal=True)
        else:
            return self.get_git_output(*args, dryrun=True)
