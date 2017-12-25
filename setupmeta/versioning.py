import io
import os
import warnings

import setupmeta
from setupmeta.scm import Git, Version


BUMPABLE = 'major minor patch'.split()


def abort(msg):
    raise setupmeta.UsageError(msg)


class Strategy:
    def __init__(self, main_fmt, local_fmt=None, branches=None):
        self.main_format = main_fmt
        self.local_format = local_fmt or '{devmarker}'
        self.branches = setupmeta.listify(branches or 'master')
        self.problem = None
        self.main_components = self.parsed_components(main_fmt)
        self.local_components = self.parsed_components(self.local_format)
        if self.problem:
            return
        if not main_fmt:
            self.problem = "No format specified"
        elif not self.main_components:
            self.problem = self.invalid_msg()

    def parsed_components(self, fmt):
        if not fmt:
            return None
        parts = fmt.split('{')
        if not parts:
            return None
        if parts[0]:
            self.problem = self.invalid_msg("must begin with '{'")
            return None
        parts.pop(0)
        if not parts:
            return None
        result = []
        for part in parts:
            p = part.partition('}')
            if not p[0] or p[2] and p[2] not in '.+':
                return None
            result.append(p[0])
        sample = Version('1.0.0')
        for part in result:
            if not hasattr(sample, part):
                self.problem = self.invalid_msg("unknown part '%s'" % part)
                return None
        return result

    def __repr__(self):
        return self.main_format + self.local_format

    def invalid_msg(self, msg=None):
        if msg:
            msg = ': %s' % msg
        return "Invalid format '%s'%s" % (self, msg or '')

    def rendered(self, version):
        """
        :param Version version: Version to render
        :return str: Rendered version
        """
        if not version:
            return None
        fmt = "%s%s" % (self.main_format, self.local_format)
        parts = version.to_dict()
        return fmt.format(**parts)

    def bumped(self, what, current_version):
        """
        :param str what: Which component to bump
        :param Version current_version: Current version
        :return str: Represented next version, with 'what' bumped
        """
        bumpable = [s for s in self.main_components if s in BUMPABLE]
        if what not in bumpable:
            msg = "Can't bump '%s', it's out of scope" % what
            msg += " of main format '%s'" % self.main_format
            abort(msg)

        major, minor, rev = current_version.bump_triplet()
        if what == 'major':
            major, minor, rev = (major + 1, 0, 0)
        elif what == 'minor':
            major, minor, rev = (major, minor + 1, 0)
        elif what == 'patch':
            major, minor, rev = (major, minor, rev + 1)

        next_version = Version("%s.%s.%s" % (major, minor, rev))
        parts = next_version.to_dict(bumpable)
        next_version = self.main_format.format(**parts)
        return next_version.strip('.').strip('+')

    @classmethod
    def from_meta(cls, given):
        if not given:
            return None
        if isinstance(given, dict):
            vfmt = given.get('format')
            lfmt = given.get('local')
            branches = given.get('branches')

            if not vfmt:
                warnings.warn(
                    "No 'format' in given strategy '%s'" % given
                )
                return None

            return cls(vfmt, lfmt, branches=branches)

        if given == 'changes':
            return cls('{major}.{minor}.{changes}')

        if given == 'tag':
            return cls('{major}.{minor}.{patch}{beta}')

        warnings.warn("Unknown versioning strategy '%s'" % given)
        return None


class Versioning:
    def __init__(self, meta):
        """
        :param setupmeta.model.SetupMeta meta: Parent meta object
        :param Scm scm: Backend SCM
        """
        self.meta = meta
        self.scm = None
        given = meta.value('versioning')
        self.enabled = bool(given)
        self.strategy = Strategy.from_meta(given)
        self.root = setupmeta.project_path()
        if os.path.isdir(os.path.join(self.root, '.git')):
            self.scm = Git(self.root)
        if not self.strategy:
            self.problem = "setupmeta versioning not enabled"
        elif not self.scm:
            self.problem = "Unknown SCM (supported: git)"
        else:
            self.problem = None

    def auto_fill_version(self):
        """
        Auto-fill version as defined by self.strategy
        :param setupmeta.model.SetupMeta meta: Parent meta object
        """
        if not self.enabled:
            return
        vdef = self.meta.definitions.get('version')
        cv = vdef.sources[0].value if vdef and vdef.sources else None
        if cv and vdef and vdef.source == 'pygradle':
            return
        if self.problem:
            if not cv:
                self.meta.auto_fill('version', '0.0.0', 'missing')
            if self.strategy:
                warnings.warn(self.problem)
            return

        gv = self.scm.get_version()
        if not gv:
            return
        rendered = self.strategy.rendered(gv)
        if not rendered:
            warnings.warn("Couldn't render version '%s'" % gv.text)
            return
        if cv and not rendered.startswith(cv):
            source = vdef.sources[0].source
            expected = rendered[:len(cv)]
            msg = "In %s version should be %s, not %s" % (source, expected, cv)
            warnings.warn(msg)
        self.meta.auto_fill('version', rendered, 'git', override=True)

    def bump(self, what, commit, commit_all):
        if self.problem:
            abort(self.problem)

        branch = self.scm.get_branch()
        if branch not in self.strategy.branches:
            abort("Can't bump branch '%s', need one of %s" % (
                branch,
                self.strategy.branches
            ))

        gv = self.scm.get_version()
        if not gv:
            abort("Could not determine version from git tags")
        if commit and gv.dirty and not commit_all:
            abort("You have pending git changes, can't bump")

        next_version = self.strategy.bumped(what, gv)

        if not commit:
            print("Not committing bump, use --commit to commit")

        self.update_sources(next_version, commit, commit_all)
        self.scm.apply_tag(commit, branch, next_version)

        hook = setupmeta.project_path('bump-hook')
        if not setupmeta.is_executable(hook):
            return

        setupmeta.run_program(
            hook,
            fatal=True,
            dryrun=not commit,
            cwd=self.root
        )

    def update_sources(self, next_version, commit, commit_all):
        vdefs = self.meta.definitions.get('version')
        if not vdefs:
            return None

        modified = []
        for vdef in vdefs.sources:
            if '.py:' not in vdef.source:
                continue

            relative_path, _, target_line_number = vdef.source.partition(':')
            full_path = setupmeta.project_path(relative_path)
            target_line_number = int(target_line_number)

            lines = []
            line_number = 0
            revised = None
            with io.open(full_path, 'rt', encoding='utf-8') as fh:
                for line in fh.readlines():
                    line_number += 1
                    if line_number == target_line_number:
                        revised = updated_line(line, next_version, vdef)
                        if revised is None or revised == line:
                            lines = None
                            break
                        line = revised
                    lines.append(line)

            if not lines:
                print("%s already has the right version" % vdef.source)

            else:
                modified.append(relative_path)
                if commit:
                    with io.open(full_path, 'wt', encoding='utf-8') as fh:
                        fh.writelines(lines)
                else:
                    print("Would update %s with '%s'" % (
                        vdef.source,
                        revised.strip()
                    ))

        if not modified:
            return

        if commit_all:
            modified = ['.']
        self.scm.commit_files(commit, modified, next_version)


def updated_line(line, next_version, vdef):
    if '=' in line:
        sep = '='
        next_version = "'%s'" % next_version
        if not line.strip().startswith('_'):
            next_version += ","
    else:
        sep = ':'

    key, _, value = line.partition(sep)
    if not key or not value:
        warnings.warn("Unknown line format %s: %s" % (vdef.source, line))
        return None

    space = ' ' if value[0] == ' ' else ''
    return "%s%s%s%s\n" % (key, sep, space, next_version)
