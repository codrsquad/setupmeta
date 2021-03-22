import io
import os
import re

import setupmeta
from setupmeta.scm import Git, Snapshot, Version

try:
    basestring

except NameError:
    basestring = str


BUMPABLE = {"major", "minor", "patch"}
MAIN_BITS = {"{major}", "{minor}", "{patch}", "{distance}", "{post}", "{dev}"}
RE_VERSIONING = re.compile(r"^(branch(\([\w\s,\-]+\))?:)?(.*?)([ +@#%^/]!?(.*))?(;(.*))?$")
RE_BITS = re.compile(r"{[^}]*}")
PRECONFIGURED = {
    "post": "{major}.{minor}.{patch}{post}+{dirty}",
    "dev": "{major}.{minor}.{patch}{dev}+{dirty}",
    "distance": "{major}.{minor}.{distance}+{dirty}",
    "devcommit": "{major}.{minor}.{patch}{dev}+{devcommit}{dirty}",
    "build-id": "{major}.{minor}.{distance}+h{$*BUILD_ID:local}.{commitid}{dirty}",
}
PRECONFIGURED_ALIAS = {
    "": "post",
    "changes": "distance",
    "default": "post",
    "tag": "post",
}


def find_scm_root(root, name):
    if not root:
        return None

    if os.path.exists(os.path.join(root, name)):
        return root

    parent = os.path.dirname(root)
    if parent == root:
        return None

    return find_scm_root(parent, name)


def project_scm(root):
    """
    :param str root: Path to project folder
    :return setupmeta.scm.Scm: SCM used by project, if any
    """
    if os.environ.get(setupmeta.SCM_DESCRIBE):
        return Snapshot(root)

    scm_root = find_scm_root(os.path.abspath(root), ".git")
    if scm_root:
        return Git(scm_root)

    version_file = os.path.join(root, setupmeta.VERSION_FILE)
    if os.path.isfile(version_file):
        return Snapshot(root)

    setupmeta.trace("could not determine SCM for '%s'" % root)
    return None


class VersionBit:
    def __init__(self, strategy, text, alternative=None, constant=False):
        self.strategy = strategy
        self.text = text
        self.alternative = alternative
        self.constant = constant
        self.renderer = None  # type: callable
        self.problem = None
        if self.constant:
            self.renderer = self.rendered_constant

        elif "$" in self.text:
            self.renderer = self.rendered_env_var

        elif not hasattr(Version, self.text):
            self.problem = "invalid versioning part '%s'" % self.text

        else:
            self.renderer = self.rendered_attr

    def __repr__(self):
        text = self.text
        if self.alternative:
            text = "%s:%s" % (text, self.alternative)

        if self.constant:
            text = "'%s'" % text

        else:
            text = "{%s}" % text

        if self.problem:
            text = " [%s]" % self.problem

        return text

    def auto_bumped(self):
        """
        :return VersionBit: Instance of this version bit, but with auto-next renderer
        """
        result = VersionBit(self.strategy, self.text, alternative=self.alternative, constant=self.constant)
        result.renderer = result.rendered_attr_auto_bumped
        return result

    def rendered_attr_auto_bumped(self, version):
        """
        :param Version version: Version to render
        :return str: Auto-bumped if possible
        """
        value = self.rendered_attr(version)
        return setupmeta.to_int(value) + 1

    def rendered_attr(self, version):
        """
        :param Version version: Version to render
        :return str: Rendered version bit
        """
        return getattr(version, self.text, None)

    def rendered_constant(self, version):
        """
        :param Version version: Version to render
        :return str: Rendered version bit
        """
        return self.text

    def rendered_env_var(self, version):
        """
        :param Version version: Version to render
        :return str: Rendered version bit
        """
        i = self.text.index("$")
        prefix = self.text[:i]
        env_var = self.text[i + 1:]
        if env_var.startswith("*") and env_var.endswith("*"):
            env_var = env_var[1:-1]
            candidates = [n for n in os.environ if env_var in n]

        elif env_var.startswith("*"):
            env_var = env_var[1:]
            candidates = [n for n in os.environ if n.endswith(env_var)]

        elif env_var.endswith("*"):
            env_var = env_var[:-1]
            candidates = [n for n in os.environ if n.startswith(env_var)]

        else:
            candidates = [env_var]

        value = None
        if candidates:
            value = os.environ.get(sorted(candidates)[0])

        if value is None:
            value = self.alternative

        if value is None:
            if prefix:
                return ""

            return None

        return "%s%s" % (prefix, value)

    def rendered(self, version):
        """
        :param Version version: Version to render
        :return str: Rendered version bit
        """
        if not self.renderer:
            return "invalid"

        value = self.renderer(version)
        return str(value)


class Strategy:
    def __init__(self, main, extra, branches, hook, **kwargs):
        self.main = main
        self.extra = extra
        if kwargs:
            setupmeta.warn("Ignored fields for 'versioning': %s" % kwargs)

        self.main_bits = self.bits(main)
        if isinstance(self.main_bits, list):
            self.bumpable = [b.text for b in self.main_bits if b.text in BUMPABLE]

        else:
            self.bumpable = []

        self.extra_bits = self.bits(extra)
        self.branches = branches
        self.hook = hook
        if self.branches and hasattr(self.branches, "lstrip"):
            self.branches = self.branches.lstrip("(").rstrip(")")

        self.branches = setupmeta.listify(self.branches, separator=",")
        self.text = self.formatted(self.branches, self.main, self.extra)
        if not self.main_bits:
            self.problem = "No versioning format specified"
            return

        all_bits = self.main_bits if isinstance(self.main_bits, list) else []
        if isinstance(self.extra_bits, list):
            all_bits = all_bits + self.extra_bits

        problems = [bit.problem for bit in all_bits if bit.problem]
        self.problem = "\n".join(problems) if problems else None

    @staticmethod
    def formatted(branches, main, extra):
        if isinstance(branches, list):
            branches = ",".join(branches)

        result = ""
        if main:
            result += setupmeta.stringify(main)

        if extra:
            if result:
                result += "+"

            result += setupmeta.stringify(extra)

        if branches:
            result = "branch(%s):%s" % (branches, result)

        return result

    def bits(self, fmt):
        if callable(fmt):
            return fmt

        result = []
        if not fmt:
            return result

        before, _, after = fmt.partition("{")
        if before:
            result.append(VersionBit(self, before, constant=True))

        if not after:
            return result

        part, _, rest = after.partition("}")
        if ":" in part:
            left, _, right = part.partition(":")
            left = VersionBit(self, left, alternative=right)
            result.append(left)

        else:
            part = VersionBit(self, part)
            result.append(part)

        result.extend(self.bits(rest))
        return result

    def __repr__(self):
        return self.text

    def rendered(self, version, extra=True, auto_bumped=True):
        """
        :param Version version: Version to render
        :param bool extra: Render extra part?
        :param bool auto_bumped: Perform .dev strategy auto-bump?
        :return str: Rendered version
        """
        bits = self.main_bits
        if isinstance(bits, list) and len(bits) > 1 and not version.additional and (version.distance > 0 or version.dirty):
            # Support for '.dev' versioning scheme: apply it only for:
            # - regular versioning (no special hook, no additional version bits given)
            # - only if it's "simple enough", ie: last bit is "dev", and the bit before that is bumpable
            bits = list(bits)
            last = bits[-1]
            prelast = bits[-2]
            if auto_bumped and last and (last.text == "dev" or last.text == "devcommit") and prelast and prelast.text in BUMPABLE:
                bits[-2] = prelast.auto_bumped()

        result = self.rendered_bits(version, bits)
        result = "" if not result else "".join(result)
        if extra and self.extra:
            extra = self.rendered_bits(version, self.extra_bits)
            if extra:
                extra = [str(s) for s in extra if str(s)]
                extra = "".join(extra)

            if extra:
                result = "%s+%s" % (result, extra.strip("."))

        return result

    @staticmethod
    def rendered_bits(version, bits):
        if isinstance(bits, list):
            return [x for x in (bit.rendered(version) for bit in bits) if x]

        if callable(bits):
            value = bits(version)
            if value:
                return [value]

        return None

    def bumped(self, what, current_version):
        """
        :param str what: Which component to bump
        :param Version current_version: Current version
        :return str: Represented next version, with 'what' bumped
        """
        if not isinstance(self.main_bits, list):
            setupmeta.abort("Main format is not a list: %s" % setupmeta.stringify(self.main_bits))

        if what not in self.bumpable:
            msg = "Can't bump '%s', it's out of scope" % what
            msg += " of main format '%s'" % self.main
            msg += " acceptable values: %s" % ", ".join(self.bumpable)
            setupmeta.abort(msg)

        major, minor, rev = current_version.major, current_version.minor, current_version.patch
        if what == "major":
            major, minor, rev = (major + 1, 0, 0)

        elif what == "minor":
            major, minor, rev = (major, minor + 1, 0)

        elif what == "patch":
            major, minor, rev = (major, minor, rev + 1)

        next_version = Version(main="%s.%s.%s" % (major, minor, rev))
        return self.rendered(next_version, extra=False)

    @classmethod
    def from_meta(cls, given):
        if not given:
            return None

        main, extra, branches, hook, rest_from_upstream = _parsed_versioning(given)
        return cls(main, extra, branches, hook, **rest_from_upstream)


def _parsed_versioning(given):
    # Defaults:
    main = "post"
    extra = "{dirty}"
    branches = "main,master"
    hook = None
    rest_from_upstream = {}
    if isinstance(given, dict):
        # User wants advanced mode: passed a dict as versioning= in setup.py
        given = dict(given)
        main = given.pop("main", main)
        extra = given.pop("extra", extra)
        branches = given.pop("branches", branches)
        hook = given.pop("hook", hook)
        rest_from_upstream = given
        given = main

    if isinstance(given, basestring):
        m = RE_VERSIONING.match(given)
        if m.group(2):
            branches = m.group(2)

        main = m.group(3)
        main = PRECONFIGURED_ALIAS.get(main, main)
        if main in PRECONFIGURED:
            main, _, extra = PRECONFIGURED[main].partition("+")

        if isinstance(main, basestring) and isinstance(extra, basestring):
            extra = _parsed_extra(m.group(4), extra)
            if m.group(7):
                hook = m.group(7)

            to_be_moved = []
            for bit in RE_BITS.findall(main):
                if bit not in MAIN_BITS:
                    main = main.replace(bit, "")
                    to_be_moved.append(bit)

            for bit in reversed(to_be_moved):
                if bit not in extra:
                    extra = "%s%s" % (bit, extra)

            main = main.strip(".")
            extra = extra.strip(".")

    return main, extra, branches, hook, rest_from_upstream


def _parsed_extra(given, default):
    if not given:
        return default

    if given[0] not in "+!":
        setupmeta.warn("PEP-440 allows only '+' as local version separator, please update your setup.py")

    given = given[1:]
    if not given:
        return given

    if given[0] == "!":
        setupmeta.warn("'!' character in 'versioning' is now deprecated, please remove it")
        given = given[1:]
        if not given:
            return given

    if given == "devcommit":
        # Allow for convenience notation of the form "dev+devcommit" or "post+devcommit" etc
        return "{devcommit}{dirty}"

    if given == "build-id":
        # Allow for convenience notation of the form "dev+build-id" or "post+build-id" etc
        return "h{$*BUILD_ID:local}.{commitid}{dirty}"

    return given


class Versioning:
    def __init__(self, meta, scm):
        """
        :param setupmeta.model.SetupMeta meta: Parent meta object
        :param Scm scm: Backend SCM
        """
        self.meta = meta
        given = meta.value("versioning")
        self.strategy = Strategy.from_meta(given)
        self.enabled = bool(given and self.strategy and not self.strategy.problem)
        self.scm = scm
        self.generate_version_file = scm and scm.root != setupmeta.MetaDefs.project_dir and not os.environ.get(setupmeta.SCM_DESCRIBE)
        self.problem = None
        if not self.strategy:
            self.problem = "setupmeta versioning not enabled"

        elif self.strategy.problem:
            self.problem = self.strategy.problem

        elif not self.scm:
            self.problem = "project not under a supported SCM"

        setupmeta.trace("versioning given: '%s', strategy: [%s], problem: [%s]" % (given, self.strategy, self.problem))

    def auto_fill_version(self):
        """
        Auto-fill version as defined by self.strategy
        :param setupmeta.model.SetupMeta meta: Parent meta object
        """
        pygradle_version = os.environ.get("PYGRADLE_PROJECT_VERSION")
        if pygradle_version:
            # Minimal support for https://github.com/linkedin/pygradle
            self.meta.auto_fill("version", pygradle_version, "pygradle", override=True)
            return

        if not self.enabled:
            setupmeta.trace("not auto-filling version, versioning is disabled")
            return

        vdef = self.meta.definitions.get("version")
        if vdef and vdef.source and vdef.source.lower().endswith("-info"):
            # We already got version from PKG-INFO
            return

        cv = vdef.sources[0].value if vdef and vdef.sources else None
        if self.problem:
            if not cv:
                self.meta.auto_fill("version", "0.0.0", "missing")

            if self.strategy:
                setupmeta.warn(self.problem)

            setupmeta.trace("not auto-filling version due to problem: [%s]" % self.problem)
            return

        gv = self.scm.get_version()
        if self.generate_version_file:
            path = setupmeta.project_path(setupmeta.VERSION_FILE)
            with open(path, "w") as fh:
                fh.write("%s" % gv)

        if gv.patch and "patch" not in self.strategy.bumpable:
            msg = "patch version component should be .0 for versioning strategy '%s', " % self.strategy
            msg += "'.%s' from current version tag '%s' will be ignored" % (gv.patch, gv)
            setupmeta.warn(msg)

        rendered = self.strategy.rendered(gv)
        if cv and gv:
            cv_adapted = Version(cv, distance=gv.distance, commitid=gv.commitid, dirty=gv.dirty)
            actual = cv_adapted.main_text
            expected = gv.main_text
            if actual != expected:
                source = vdef.sources[0].source
                msg = "In %s version should be '%s', not '%s'" % (source, expected, cv)
                setupmeta.warn(msg)

        self.meta.auto_fill("version", rendered, self.scm.name, override=True)

    def get_bump(self, what):
        if self.problem:
            setupmeta.abort(self.problem)

        gv = self.scm.get_version()
        return self.strategy.bumped(what, gv)

    def verify_remote_tags(self):
        """Verify that remote tags are identical to local tags"""
        local_tags = self.scm.local_tags()
        remote_tags = self.scm.remote_tags()
        local_only = local_tags.difference(remote_tags)
        remote_only = remote_tags.difference(local_tags)
        if remote_only:
            message = "Can't bump: not all remote tags are present locally!\n"
            if local_only:
                message += "Tags only seen locally: %s\n" % ", ".join(local_only)

            if remote_only:
                message += "Tags only on remote: %s\n" % ", ".join(remote_only)

            setupmeta.abort(message)

    def bump(self, what, commit=False, push=False, simulate_branch=None):
        if self.problem:
            setupmeta.abort(self.problem)

        branch = simulate_branch or self.scm.get_branch()
        if branch not in self.strategy.branches:
            setupmeta.abort("Can't bump branch '%s', need one of %s" % (branch, self.strategy.branches))

        gv = self.scm.get_version()
        if gv and gv.dirty:
            if commit:
                setupmeta.abort("You have pending changes, can't bump")

            print("Note: you have pending changes, commit (or stash) them before using --commit")

        self.verify_remote_tags()

        next_version = self.strategy.bumped(what, gv)

        if not commit:
            print("Not committing bump, use --commit to commit")

        if not push:
            print("Not pushing bump, use --push to push")

        vdefs = self.meta.definitions.get("version")
        if vdefs:
            self.update_sources(next_version, commit, push, vdefs)

        self.scm.apply_tag(commit, push, next_version, branch)

        if not self.strategy.hook:
            return

        hook = setupmeta.project_path(self.strategy.hook)
        if setupmeta.is_executable(hook):
            setupmeta.run_program(hook, self.meta.name, branch, next_version, fatal=True, dryrun=not commit, cwd=setupmeta.project_path())

    def update_sources(self, next_version, commit, push, vdefs):
        modified = []
        for vdef in vdefs.sources:
            if ".py:" not in vdef.source:
                continue

            relative_path, _, target_line = vdef.source.partition(":")
            full_path = setupmeta.project_path(relative_path)
            target_line = setupmeta.to_int(target_line, default=0)

            lines = []
            changed = 0
            line_number = 0
            revised = None
            with io.open(full_path, "rt") as fh:
                for line in fh.readlines():
                    line_number += 1
                    if line_number == target_line:
                        revised = updated_line(line, next_version, vdef)
                        if revised and revised != line:
                            changed += 1
                            line = revised

                    lines.append(line)

            if not changed:
                print("%s already has the right version" % vdef.source)

            else:
                modified.append(relative_path)
                if commit:
                    with io.open(full_path, "wt") as fh:
                        fh.writelines(lines)

                else:
                    print("Would update %s with: %s" % (vdef.source, revised.strip()))

        if not modified:
            return

        self.scm.commit_files(commit, push, modified, next_version)


def updated_line(line, next_version, vdef):
    line = line.strip()
    sep = "=" if "=" in line else ":"
    space = ""
    quote = ""
    key, _, value = line.partition(sep)
    if value and value[0] == " ":
        space = " "

    value = value.strip()
    if value and value[0] == "'":
        quote = "'"

    elif value and value[0] == '"':
        quote = '"'

    comment = ""
    if "#" in value:
        i = value.index("#")
        comment = "  #%s" % value[i + 1:]

    return "%s%s%s%s%s%s%s\n" % (key, sep, space, quote, next_version, quote, comment)
