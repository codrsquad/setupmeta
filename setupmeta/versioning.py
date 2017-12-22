import io
import os
import warnings

import setupmeta
from setupmeta.content import project_path
from setupmeta.scm import Git


class UsageError(Exception):
    pass


class Versioning:
    def __init__(self, meta):
        """
        :param setupmeta.model.SetupMeta meta: Parent meta object
        :param Scm scm: Backend SCM
        """
        self.meta = meta
        self.scm = None
        self.strategy = self.meta.value('versioning')
        self.root = project_path()
        if os.path.isdir(os.path.join(self.root, '.git')):
            self.scm = Git(self.root)
        if not self.strategy:
            self.problem = "Project not configured to use setupmeta versioning"
        elif not self.strategy.startswith('tag'):
            self.problem = "Unknown versioning strategy %s" % self.strategy
        elif not self.scm:
            self.problem = "%s is not under a supported scm" % self.root
        else:
            self.problem = None

    def auto_fill_version(self):
        """
        Auto-fill version from SCM tag
        :param setupmeta.model.SetupMeta meta: Parent meta object
        """
        if self.problem:
            if self.strategy:
                warnings.warn(self.problem)
            return

        gv = self.scm.get_version()
        if not gv:
            return
        if gv.broken:
            warnings.warn("Invalid version tag: %s" % gv.text)
            return
        vdef = self.meta.definitions.get('version')
        cv = vdef.sources[0].value if vdef and vdef.sources else None
        if cv and not gv.canonical.startswith(cv):
            source = vdef.sources[0].source
            expected = gv.canonical[:len(cv)]
            msg = "In %s version should be %s, not %s" % (source, expected, cv)
            warnings.warn(msg)
        self.meta.auto_fill('version', gv.canonical, 'git', override=True)

    def bump(self, what, commit, commit_all):
        if self.problem:
            raise UsageError(self.problem)

        branch = self.scm.get_branch()
        if branch != 'master':
            raise UsageError("Can't bump branch '%s', need master" % branch)

        gv = self.scm.get_version()
        if not gv:
            raise UsageError("Could not determine version from git tags")
        if gv.broken:
            raise UsageError("Invalid git version tag: %s" % gv.text)
        if commit and gv.dirty and not commit_all:
            raise UsageError("You have pending git changes, can't bump")

        major, minor, rev = gv.version.version[:3]
        if what == 'major':
            major, minor, rev = (major + 1, 0, 0)
        elif what == 'minor':
            major, minor, rev = (major, minor + 1, 0)
        elif what == 'patch':
            if gv.auto_patch:
                raise UsageError("Can't bump patch number, it's auto-filled")
            major, minor, rev = (major, minor, rev + 1)
        else:
            raise UsageError("Unknown bump target '%s'" % what)

        if gv.auto_patch:
            next_version = "%s.%s" % (major, minor)
        else:
            next_version = "%s.%s.%s" % (major, minor, rev)

        if not commit:
            print("Not committing bump, use --commit to commit")

        self.update_sources(next_version, commit, commit_all)

        self.scm.apply_tag(commit, branch, next_version)

        if '+' in self.strategy:
            cmd = self.strategy.partition('+')[2].split()
            if commit:
                setupmeta.run_program(*cmd, fatal=True)
            else:
                setupmeta.run_program(*cmd, dryrun=True)

    def update_sources(self, next_version, commit, commit_all):
        vdefs = self.meta.definitions.get('version')
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
