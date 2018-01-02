from distutils.version import LooseVersion
import re

import setupmeta


class Scm:
    """
    API used by setupmeta for versioning using SCM tags
    """

    program = None      # type: str # Program name (like 'git' or 'hg')

    def __init__(self, root):
        """
        :param str root: Full path to project checkout folder
        """
        self.root = root

    def get_branch(self):
        """
        :return str: Current branch name
        """
        pass

    def get_version(self):
        """
        :return str: Current version as computed from latest SCM version tag
        """
        pass

    def commit_files(self, commit, relative_paths, next_version):
        """
        Commit modified files with 'relative_paths', commit message will be of the form "Version v1.0.0"

        :param bool commit: Dryrun if False, effectively commit if True
        :param list(str) relative_paths: Relative paths to commit
        :param str next_version: Version that is about to be applied, of the form 1.0.0 (used for commit message)
        """
        pass

    def apply_tag(self, commit, next_version):
        """
        Apply a tag of the form "v1.0.0" at current commit

        :param bool commit: Dryrun if False, effectively apply tag if True
        :param str next_version: Version to use for tag
        """
        pass

    def get_output(self, *args, **kwargs):
        """
        Run SCM's CLI program with 'args' and optional additional 'kwargs' (passed through to subprocess.Popen)
        Command is ran with cwd being 'self.root'

        :param list(str) args: CLI arguments (example: describe --tags)
        :param dict kwargs: Additional named arguments
        :return str|int: Output if kwargs['capture'] is True, exit code otherwise
        """
        capture = kwargs.pop('capture', True)
        cwd = kwargs.pop('cwd', self.root)
        return setupmeta.run_program(self.program, *args, capture=capture, cwd=cwd, **kwargs)

    def run(self, commit, *args, **kwargs):
        """
        Run SCM's CLI program with 'args' and optional additional 'kwargs' (passed through to subprocess.Popen)
        Output is "passed through" to stdout/stderr.

        :param bool commit: Effectively run the command if True, otherwise just print "Would run: ..."
        :param list(str) args: CLI arguments (example: push origin)
        :param dict kwargs: Additional named arguments
        :return int: Exit code (always zero, unless fatal=False is passed explicitly in kwargs)
        """
        fatal = kwargs.pop('fatal', True)
        capture = kwargs.pop('capture', None)
        return self.get_output(*args, capture=capture, fatal=fatal, dryrun=not commit, **kwargs)


class Git(Scm):
    """
    Implementation for git
    """

    program = 'git'

    # Output expected from git describe
    re_describe = re.compile(r'^v?(.+?)(-\d+)?(-g\w+)?$', re.IGNORECASE)

    def is_dirty(self):
        """
        :return bool: Is checkout folder self.root currently dirty? (ie: has pending changes)
        """
        exitcode = self.get_output('diff', '--quiet', '--ignore-submodules', capture=False)
        return exitcode != 0

    def get_branch(self):
        branch = self.get_output('rev-parse', '--abbrev-ref', 'HEAD')
        return branch and branch.strip()

    def get_version(self):
        main = None
        changes = None
        commitid = None
        dirty = self.is_dirty()
        text = self.get_output('describe', '--tags', '--long', '--match', 'v*.*')
        if text:
            m = self.re_describe.match(text)
            if m:
                main = m.group(1)
                changes = setupmeta.strip_dash(m.group(2))
                changes = setupmeta.to_int(changes, default=0)
                commitid = setupmeta.strip_dash(m.group(3))

        if not text or not main:
            dirty = True
            commitid = self.get_output('rev-parse', '--short', 'HEAD')
            commitid = 'g%s' % commitid if commitid else ''
            changes = self.get_output('rev-list', 'HEAD')
            changes = changes.count('\n') + 1 if changes else 0

        return Version(main, changes, commitid, dirty, text)

    def commit_files(self, commit, relative_paths, next_version):
        if not relative_paths:
            return
        relative_paths = sorted(set(relative_paths))
        self.run(commit, 'add', *relative_paths)
        self.run(commit, 'commit', '-m', "Version %s" % next_version)
        self.run(commit, 'push', 'origin')

    def apply_tag(self, commit, next_version):
        bump_msg = "Version %s" % next_version
        tag = "v%s" % next_version
        self.run(commit, 'tag', '-a', tag, '-m', bump_msg)
        self.run(commit, 'push', '--tags', 'origin')


class Version:
    """
    Version broken down for setupmeta usage purposes
    """

    text = None         # type: str # Full text of version as received
    version = None      # type: LooseVersion # Distutils LooseVersion object representing the 'main' part

    major = 0           # type: int # Major part of version
    minor = 0           # type: int # Minor part of version
    patch = 0           # type: int # Patch part of version
    changes = 0         # type: int # Number of changes since last version tag
    commitid = None     # type: str # Commit id
    dirty = ''          # type: str # Dirty marker

    def __init__(self, main=None, changes=0, commitid=None, dirty=False, text=None):
        """
        :param str|None main: Main part of the version (example: "1.0.0")
        :param int changes: Number of commits since last version tag
        :param str|None commitid: Current commit id (example: g1234567)
        :param bool dirty: Whether checkout has pending changes currently or not
        :param str|None text: Version text as received from SCM
        """
        self.changes = changes or 0
        self.commitid = (commitid or 'initial').strip()
        self.dirty = '.dirty' if dirty else ''
        main = (main or '0.0.0').strip()
        self.text = text or "v%s-%s-%s" % (main, self.changes, self.commitid)
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

    @property
    def post(self):
        """
        {post} marker for this version

        :return str: '.post{changes}' for changes > 0, empty string otherwise
        """
        if self.changes:
            return '.post%s' % self.changes
        return ''
