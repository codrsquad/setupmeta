import os
import re

import setupmeta


RE_BRANCH_STATUS = re.compile(r"^## (.+)\.\.\.(([^/]+)/)?([^ ]+)\s*(\[(.+)\])?$")
RE_GIT_DESCRIBE = re.compile(r"^v?(.+?)(-\d+)?(-g\w+)?(-dirty)?$", re.IGNORECASE)  # Output expected from git describe


class Scm:
    """API used by setupmeta for versioning using SCM tags"""

    program = None  # type: str # Program name (like 'git' or 'hg')

    def __init__(self, root):
        """
        :param str root: Full path to project checkout folder
        """
        self.root = root

    def __repr__(self):
        return "%s %s" % (self.name, self.root)

    @property
    def name(self):
        return self.__class__.__name__.lower()

    def local_tags(self):
        """Get all local tags"""

    def remote_tags(self):
        """Get all remote tags"""

    def get_branch(self):
        """
        :return str: Current branch name
        """

    def get_version(self):
        """
        :return Version: Current version as computed from latest SCM version tag
        """

    def commit_files(self, commit, push, relative_paths, next_version):
        """
        Commit modified files with 'relative_paths', commit message will be of the form "Version v1.0.0"

        :param bool commit: Dryrun if False, effectively commit if True
        :param bool push: Effectively push if True
        :param list(str) relative_paths: Relative paths to commit
        :param str next_version: Version that is about to be applied, of the form 1.0.0 (used for commit message)
        """

    def apply_tag(self, commit, push, next_version, branch):
        """
        Apply a tag of the form "v1.0.0" at current commit

        :param bool commit: Dryrun if False, effectively apply tag if True
        :param bool push: Effectively push if True
        :param str next_version: Version to use for tag
        :param str branch: Branch on which tag is being applied
        """

    def get_output(self, *args, **kwargs):
        """
        Run SCM's CLI program with 'args' and optional additional 'kwargs' (passed through to subprocess.Popen)
        Command is ran with cwd being 'self.root'

        :param args: CLI arguments (example: describe --tags)
        :param kwargs: Additional named arguments
        :return str|int: Output if kwargs['capture'] is True, exit code otherwise
        """
        capture = kwargs.pop("capture", True)
        cwd = kwargs.pop("cwd", self.root)
        return setupmeta.run_program(self.program, *args, capture=capture, cwd=cwd, **kwargs)

    def run(self, commit, *args, **kwargs):
        """
        Run SCM's CLI program with 'args' and optional additional 'kwargs' (passed through to subprocess.Popen)
        Output is "passed through" to stdout/stderr.

        :param bool commit: Effectively run the command if True, otherwise just print "Would run: ..."
        :param args: CLI arguments (example: push origin)
        :param kwargs: Additional named arguments
        :return int: Exit code (always zero, unless fatal=False is passed explicitly in kwargs)
        """
        fatal = kwargs.pop("fatal", True)
        capture = kwargs.pop("capture", None)
        return self.get_output(*args, capture=capture, fatal=fatal, dryrun=not commit, **kwargs)


class Snapshot(Scm):
    """
    Implementation for cases where project lives in a subfolder of a git checkout

    If one runs: python -m pip wheel ...
    pip copies current folder to a temp location, and invokes setup.py there, any .git info is lost in that case
    This implementation allows to still be able to properly determine version even in that case
    """

    program = None

    def is_dirty(self):
        v = os.environ.get(setupmeta.SCM_DESCRIBE)
        return v and "dirty" in v

    def get_branch(self):
        """Consider branch to be always HEAD for snapshots"""
        return "HEAD"

    def get_version(self):
        v = os.environ.get(setupmeta.SCM_DESCRIBE)
        if v:
            return Git.parsed_version(v)

        path = os.path.join(self.root, setupmeta.VERSION_FILE)
        with open(path) as fh:
            return Git.parsed_version(fh.readline(), False)


class Git(Scm):
    """Implementation for git"""

    program = "git"
    _has_origin = None

    def _get_tags(self, *cmd):
        text = self.get_output(*cmd)
        result = set()
        for line in text.splitlines():
            p = line.rpartition("/")[2]
            tag = str(p.partition("^")[0])
            if tag.startswith("v") or tag[0].isdigit():
                result.add(tag)

        return result

    def local_tags(self):
        """Get all local tags"""
        return self._get_tags("show-ref", "--tags", "-d")

    def remote_tags(self):
        """Get all remote tags"""
        return self._get_tags("ls-remote", "--tags")

    @staticmethod
    def parsed_version(text, dirty=None):
        if text:
            m = RE_GIT_DESCRIBE.match(text)
            if m:
                main = m.group(1)
                distance = setupmeta.strip_dash(m.group(2))
                distance = setupmeta.to_int(distance, default=0)
                commitid = setupmeta.strip_dash(m.group(3))
                if dirty is None:
                    # This is only settable via env var SCM_DESCRIBE
                    dirty = m.group(4) == "-dirty"

                return Version(main, distance, commitid, dirty, text)

        return None

    def is_dirty(self):
        """
        :return bool: Is checkout folder self.root currently dirty?

        This checks both the working tree and index, in a single command.
        Ref: https://stackoverflow.com/a/2659808/15690
        """
        exitcode = self.get_output("diff", "--quiet", "--ignore-submodules", capture=False)
        if exitcode == 0:
            exitcode = self.get_output("diff", "--quiet", "--ignore-submodules", "--staged", capture=False)

        return exitcode != 0

    def get_branch(self):
        branch = self.get_output("rev-parse", "--abbrev-ref", "HEAD")
        return branch and branch.strip()

    def get_version(self):
        dirty = self.is_dirty()
        # Allow to override git describe command via env var SETUPMETA_GIT_DESCRIBE_COMMAND (just in case)
        cmd = os.environ.get("SETUPMETA_GIT_DESCRIBE_COMMAND", "describe --dirty --tags --long --match *.* --first-parent")
        cmd = cmd.split(" ")
        text = self.get_output(*cmd)
        version = self.parsed_version(text, dirty)
        if version:
            return version

        # Try harder
        commitid = self.get_output("rev-parse", "--short", "HEAD")
        commitid = "g%s" % commitid if commitid else ""
        distance = self.get_output("rev-list", "HEAD")
        distance = distance.count("\n") + 1 if distance else 0
        return Version(None, distance, commitid, dirty)

    def has_origin(self):
        if self._has_origin is None:
            self._has_origin = bool(self.get_output("config", "--get", "remote.origin.url"))

        return self._has_origin

    def commit_files(self, commit, push, relative_paths, next_version):
        if not relative_paths:
            return

        relative_paths = sorted(set(relative_paths))
        self.run(commit, "add", *relative_paths)
        self.run(commit, "commit", "-m", "Version %s" % next_version)
        if push:
            if self.has_origin():
                self.run(commit, "push", "origin")

            else:
                print("Won't push: no origin defined")

    def apply_tag(self, commit, push, next_version, branch):
        self.get_output("fetch", "--all")
        output = self.get_output("status", "--porcelain", "--branch")
        for line in output.splitlines():
            m = RE_BRANCH_STATUS.match(line)
            if m and m.group(1) == branch:
                state = m.group(6)
                if state and ("behind" in state or "gone" in state):
                    # Example: Local branch 'master' is out of date (behind 1), can't bump
                    setupmeta.abort("Local branch '%s' is out of date (%s), can't bump" % (branch, state))

        bump_msg = "Version %s" % next_version
        tag = "v%s" % next_version

        self.run(commit, "tag", "-a", tag, "-m", bump_msg)
        if push:
            if self.has_origin():
                self.run(commit, "push", "--tags", "origin")

            else:
                print("Not running 'git push --tags origin' as you don't have an origin")


class Version:
    """
    Version broken down for setupmeta usage purposes
    """

    text = None         # type: str # Full text of version as received

    major = 0           # type: int # Major part of version
    minor = 0           # type: int # Minor part of version
    patch = 0           # type: int # Patch part of version
    distance = 0        # type: int # Number of commits since last version tag
    commitid = None     # type: str # Commit id
    dirty = ""          # type: str # Dirty marker
    additional = ""     # type: str # Additional version markers (if any)

    def __init__(self, main=None, distance=0, commitid=None, dirty=False, text=None):
        """
        :param str|None main: Main part of the version (example: "1.0.0")
        :param int distance: Number of commits since last version tag
        :param str|None commitid: Current commit id (example: g1234567)
        :param bool dirty: Whether checkout is dirty or not
        :param str|None text: Version text as received from SCM
        """
        self.distance = distance or 0
        self.commitid = (commitid or "g0000000").strip()
        self.dirty = ".dirty" if dirty else ""
        main = (main or "0.0.0").strip()
        self.text = text or "v%s-%s-%s" % (main, self.distance, self.commitid)
        self.major, self.minor, self.patch, self.additional, _, _ = setupmeta.version_components(main)

    def __repr__(self):
        return self.text

    @property
    def main_text(self):
        """Main components only"""
        return "%s.%s.%s" % (self.major, self.minor, self.patch)

    @property
    def post(self):
        """
        {post} marker for this version

        :return str: '.post{distance}' for distance > 0, empty string otherwise
        """
        if self.distance:
            return "%s.post%s" % (self.additional, self.distance)

        return self.additional

    @property
    def dev(self):
        """
        {dev} marker for this version

        :return str: '.dev{distance}' for distance > 0, empty string otherwise
        """
        if self.distance or self.dirty:
            return "%s.dev%s" % (self.additional, self.distance)

        return self.additional

    @property
    def devcommit(self):
        """
        {devcommit} marker for this version, alias for ".{commitid}"

        :return str: '.{commitid}' for distance > 0, empty string otherwise
        """
        if self.distance or self.dirty:
            return ".%s" % self.commitid

        return ""
