import os
import re
import sys

import setupmeta

RE_BRANCH_STATUS = re.compile(r"^## (.+)\.\.\.(([^/]+)/)?([^ ]+)\s*(\[(.+)])?$")
RE_GIT_DESCRIBE = re.compile(r"^v?([0-9]+\.[0-9]+.+?)(-\d+)?(-g\w+)?(-dirty)?$", re.IGNORECASE)  # Output expected from git describe


class Scm:
    """API used by setupmeta for versioning using SCM tags"""

    version_tag = None  # type: str # Format for tags to consider as version tags in underlying SCM, when applicable

    def __init__(self, root):
        """
        :param str root: Full path to project checkout folder
        """
        self.root = root

    def __repr__(self):
        return "%s %s" % (self.name, self.root)

    def is_dirty(self):
        """
        Returns:
            (bool): Is checkout folder 'self.root' currently dirty?
        """

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

    def get_diff_report(self):
        """
        This is legacy and will be removed in setupmeta v5.0
        Textual diff report of the current repo, designed to show if any changes are pending (and thus why version is marked "dirty")

        Returns
        -------
        str
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


class Snapshot(Scm):
    """
    Implementation for cases where project lives in a sub-folder of a git checkout

    If one runs: python -m pip wheel ...
    pip copies current folder to a temp location, and invokes setup.py there, any .git info is lost in that case
    This implementation allows to still be able to properly determine version even in that case
    """

    def is_dirty(self):
        v = os.environ.get(setupmeta.SCM_DESCRIBE)
        return v and "dirty" in v

    def get_branch(self):
        """Consider branch to be always HEAD for snapshots"""
        return "HEAD"

    def get_version(self):
        v = os.environ.get(setupmeta.SCM_DESCRIBE)
        if v:
            return Git.parsed_git_describe(v, origin="env var SCM_DESCRIBE")

        path = os.path.join(self.root, setupmeta.VERSION_FILE)
        with open(path) as fh:
            return Git.parsed_git_describe(fh.readline(), origin=path)


class Git(Scm):
    """Implementation for git"""

    _has_origin = None

    def _get_tags(self, *cmd):
        text = self.git_output(*cmd)
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
    def parsed_git_describe(text, origin=None):
        if text:
            m = RE_GIT_DESCRIBE.match(text)
            if m:
                main = m.group(1)
                distance = setupmeta.strip_dash(m.group(2))
                distance = setupmeta.to_int(distance, default=0)
                commitid = setupmeta.strip_dash(m.group(3))
                dirty = bool(m.group(4))
                return Version(main=main, distance=distance, commitid=commitid, dirty=dirty, text=text)

        if origin:
            setupmeta.warn("Ignoring invalid version from %s: %s" % (origin, text))
            return Version(main="0.0.0", dirty=True)

    def is_dirty(self):
        """
        This checks both the working tree and index, in a single command.
        Ref: https://stackoverflow.com/a/2659808/15690
        """
        result = self.run_git("diff", "--quiet", "--ignore-submodules", fatal=False)
        if result.returncode == 0:
            result = self.run_git("diff", "--quiet", "--ignore-submodules", "--staged", fatal=False)

        return result.returncode != 0

    def get_branch(self):
        branch = self.git_output("rev-parse", "--abbrev-ref", "HEAD")
        return branch and branch.strip()

    def get_diff_report(self):
        return self.git_output("diff", "--stat")

    def git_describe_output(self):
        """
        Determine version tag from git
        Unfortunately 'git describe --match' does not accept regexes, otherwise we'd do '^v?[0-9]+\\.'
        """
        override = os.environ.get("SETUPMETA_GIT_DESCRIBE_COMMAND")
        if override:
            # Override was given, just use it as-is
            setupmeta.trace("Using SETUPMETA_GIT_DESCRIBE_COMMAND: %s" % override)
            cmd = override.split(" ")
            return self.git_output(*cmd)

        version_tag = self.version_tag
        cmd = ["describe", "--dirty", "--tags", "--long", "--first-parent", "--match"]
        if version_tag:
            # A custom version tag was configured, use it
            setupmeta.trace("Using configured version_tag: %s" % version_tag)
            return self.git_output(*cmd, version_tag)

        # No overrides, try v*.* first, then fall back to '*.*' if need be
        text = self.git_output(*cmd, "v*.*")
        if not text:
            # TODO(zsimic): Remove this for setupmeta v4.0
            text = self.git_output(*cmd, "*.*")

        return text

    def get_version(self):
        text = self.git_describe_output()
        version = self.parsed_git_describe(text)
        if version:
            return version

        # Try harder
        commitid = self.git_output("rev-parse", "--short", "HEAD")
        commitid = "g%s" % commitid if commitid else ""
        distance = self.git_output("rev-list", "HEAD")
        distance = distance.count("\n") + 1 if distance else 0
        return Version(main=None, distance=distance, commitid=commitid, dirty=self.is_dirty())

    def has_origin(self):
        if self._has_origin is None:
            self._has_origin = bool(self.git_output("config", "--get", "remote.origin.url"))

        return self._has_origin

    def commit_files(self, commit, push, relative_paths, next_version):
        if not relative_paths:
            return

        relative_paths = sorted(set(relative_paths))
        self.run_git("add", *relative_paths, dryrun=not commit, passthrough=True)
        self.run_git("commit", "-m", "Version %s" % next_version, "--no-verify", dryrun=not commit, passthrough=True)
        if push:
            if self.has_origin():
                self.run_git("push", "origin", dryrun=not commit, passthrough=True)

            else:
                print("Won't push: no origin defined")

    def apply_tag(self, commit, push, next_version, branch):
        self.run_git("fetch", "--all", dryrun=not commit, passthrough=True)
        output = self.git_output("status", "--porcelain", "--branch")
        for line in output.splitlines():
            m = RE_BRANCH_STATUS.match(line)
            if m and m.group(1) == branch:
                state = m.group(6)
                if state and ("behind" in state or "gone" in state):
                    # Example: Local branch 'main' is out of date (behind 1), can't bump
                    setupmeta.abort("Local branch '%s' is out of date (%s), can't bump" % (branch, state))

        bump_msg = "Version %s" % next_version
        tag = "v%s" % next_version

        self.run_git("tag", "-a", tag, "-m", bump_msg, dryrun=not commit, passthrough=True)
        if push:
            if self.has_origin():
                self.run_git("push", "--tags", "origin", dryrun=not commit, passthrough=True)

            else:
                print("Not running 'git push --tags origin' as you don't have an origin")

    def git_output(self, *args) -> str:
        result = self.run_git(*args, fatal=False)
        return result.stdout

    def run_program(self, cmd, *args, announce=False, dryrun=False):
        """Used to make mocking easier"""
        return setupmeta.run_program("git", cmd, *args, announce=announce, cwd=self.root, dryrun=dryrun)

    def run_git(self, *args, dryrun=False, fatal=True, passthrough=False):
        """
        Run git with `args`

        Parameters
        ----------
        *args: str
            CLI arguments (example: push origin)
        dryrun : bool
            When True, do not run, just print what would be run
        passthrough: bool
            When True, pass-through stderr/stdout
        fatal: bool
            When True, abort execution is command exited with code != 0

        Returns
        -------
        setupmeta.RunResult
        """
        result = self.run_program(*args, announce=passthrough, dryrun=dryrun)
        if result.returncode and result.stderr:
            if self.should_ignore_error(result):
                result.returncode = 0
                result.stderr = ""

            elif not fatal:
                # Bubble up unexpected non-fatal errors as warnings
                sys.stderr.write(f"WARNING: {result.represented_args} exited with code {result.returncode}, stderr:\n")
                sys.stderr.write(f"{result.stderr}\n")
                result.stderr = ""

        if passthrough and os.environ.get("SETUPMETA_RUNNING_SCENARIOS"):
            passthrough = False  # Reduce chatter when running test scenarios

        if passthrough and result.stdout:
            print(result.stdout)

        if fatal:
            result.require_success()  # stderr is always shown on failure, so don't repeat it with `passthrough` below

        if passthrough and result.stderr:
            sys.stderr.write(f"{result.stderr}\n")

        return result

    @staticmethod
    def should_ignore_error(result):
        """Edge case: don't warn for known expected failures"""
        if result.args[0] in ("rev-list", "rev-parse") and "HEAD" in result.args:
            # No commits yet, brand-new git repo
            return result.stderr and "revision" in result.stderr.lower()

        if result.args[0] == "describe":
            # No tags are present, git states "No names found" in that case
            return result.stderr and "no names" in result.stderr.lower()

        if result.args[0] in ("show-ref", "ls-remote") and "--tags" in result.args:
            # Used for version bump, don't warn if there are no tags yet or no remote defined
            return True


class Version:
    """
    Version broken down for setupmeta usage purposes
    """

    text = None  # type: str # Full text of version as received

    major = 0  # type: int # Major part of version
    minor = 0  # type: int # Minor part of version
    patch = 0  # type: int # Patch part of version
    distance = 0  # type: int # Number of commits since last version tag
    commitid = None  # type: str # Commit id
    dirty = ""  # type: str # Dirty marker
    additional = ""  # type: str # Additional version markers (if any)

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
