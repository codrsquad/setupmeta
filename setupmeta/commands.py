"""
Commands contributed by setupmeta
"""

import collections
import os
import platform
import shutil
import sys
from distutils.command.check import check

import setuptools

import setupmeta


def abort(message):
    from distutils.errors import DistutilsSetupError

    raise DistutilsSetupError(message)


def MetaCommand(cls):
    """Decorator allowing for less boilerplate in our commands"""
    return setupmeta.MetaDefs.register_command(cls)


@MetaCommand
class CheckCommand(check):
    """Perform checks on the package"""

    def _show_requirements_synopsis(self):
        """Show how many requirements were auto-abstracted or ignored, if any"""
        install_requires = self.setupmeta and self.setupmeta.requirements and self.setupmeta.requirements.install
        if not install_requires or not (install_requires.abstracted or install_requires.ignored):
            return
        print("[setupmeta] install_requires: %s abstracted, %s ignored, %s untouched" % (
            len(install_requires.abstracted),
            len(install_requires.ignored),
            len(install_requires.untouched),
        ))

    def run(self):
        check.run(self)
        self._show_requirements_synopsis()


@MetaCommand
class VersionCommand(setuptools.Command):
    """show/bump version managed by setupmeta"""

    user_options = [
        ("bump=", "b", "bump specified part of version"),
        ("commit", "c", "commit bump"),
        ("simulate-branch=", "s", "simulate branch name (useful for testing)"),
    ]

    def initialize_options(self):
        self.bump = None
        self.commit = 0
        self.simulate_branch = None

    def run(self):
        try:
            if self.bump:
                self.setupmeta.versioning.bump(self.bump, self.commit, self.simulate_branch)
            else:
                print(self.setupmeta.version)

        except setupmeta.UsageError as e:
            abort(e)


@MetaCommand
class ExplainCommand(setuptools.Command):
    """Show a report of where key/values setup(attr) come from"""

    user_options = [
        ("dependencies", "d", "show auto-filled dependencies"),
        ("recommend", "r", "show more recommendations"),
        ("chars=", "c", "max chars to show"),
    ]

    def initialize_options(self):
        self.dependencies = False
        self.recommend = False
        self.chars = setupmeta.Console.columns()

    def check_recommend(self, key, hint=None):
        if key not in self.setupmeta.definitions:
            hint = ", %s" % hint if hint else ""
            self.setupmeta.auto_fill(key, "- Consider specifying '%s'%s" % (key, hint), "missing")

    def represented_req(self, name, note=None, align=None):
        name = '"%s",' % name
        if note:
            fmt = "%%-%ss# %%s" % align
            name = fmt % (name, note)
        return name

    def show_requirements(self, setup_key, requirements):
        """
        :param str setup_key: Name of corresponding key in 'setup()'
        :param RequirementsEntry requirements:
        """
        content = "None,   # no auto-fill"
        if requirements and requirements.reqs:
            names = []
            notes = []
            for req in requirements.reqs:
                names.append(req)
                notes.append(requirements.notes.get(req) or "")
            if any(len(note) for note in notes):
                longest_name = max(len(name) for name in names) + 5
                content = []
                for i in range(len(names)):
                    content.append(self.represented_req(names[i], notes[i], longest_name))
            else:
                content = [self.represented_req(name) for name in names]
            content = "[\n        %s\n    ]," % "\n        ".join(content).strip()
        print("    %s=%s" % (setup_key, content))

    def run(self):
        if self.dependencies:
            print("    # This reflects only auto-fill, doesn't look at explicit settings from your setup.py")
            install = None
            test = None
            if self.setupmeta.requirements:
                install = self.setupmeta.requirements.install
                test = self.setupmeta.requirements.test
            self.show_requirements("install_requires", install)
            self.show_requirements("tests_require", test)
            return

        self.chars = setupmeta.to_int(self.chars, default=setupmeta.Console.columns())

        definitions = self.setupmeta.definitions
        self.check_recommend("name")
        self.check_recommend("version", "you can use setupmeta's versioning='...'")
        self.check_recommend("description", "add a README or a docstring to your module")
        self.check_recommend("long_description", "add a README file")
        if self.recommend:
            self.check_recommend("author")
            self.check_recommend("classifiers")
            self.check_recommend("download_url")
            self.check_recommend("license")
            self.check_recommend("url")
        if definitions:
            longest_key = min(30, max(len(key) for key in definitions))
            sources = sum((d.sources for d in definitions.values()), [])
            longest_source = min(32, max(len(s.source) for s in sources))
            form = "%%%ss: (%%%ss) %%s" % (longest_key, -longest_source)
            max_chars = max(60, self.chars - longest_key - longest_source - 5)

            for definition in sorted(definitions.values()):
                count = 0
                for source in definition.sources:
                    if count:
                        prefix = "\_"
                    elif source.key not in setupmeta.MetaDefs.all_fields:
                        prefix = "%s*" % source.key
                    else:
                        prefix = source.key

                    preview = setupmeta.short(source.value, c=max_chars)
                    print(form % (prefix, source.source, preview))
                    count += 1


@MetaCommand
class EntryPointsCommand(setuptools.Command):
    """List entry points for pygradle consumption"""

    def run(self):
        entry_points = self.setupmeta.value("entry_points")
        console_scripts = get_console_scripts(entry_points)
        if not console_scripts:
            return
        if isinstance(console_scripts, list):
            for ep in console_scripts:
                print(ep)
            return
        for line in console_scripts.splitlines():
            line = line.strip()
            if line:
                print(line)


def get_console_scripts(entry_points):
    """pygradle's 'entrypoints' are misnamed: they really mean 'consolescripts'"""
    if not entry_points:
        return None
    if isinstance(entry_points, dict):
        return entry_points.get("console_scripts")
    if isinstance(entry_points, list):
        result = []
        in_console_scripts = False
        for line in entry_points:
            line = line.strip()
            if line and line.startswith("["):
                in_console_scripts = "console_scripts" in line
                continue
            if in_console_scripts:
                result.append(line)
        return result
    return get_console_scripts(entry_points.split("\n"))


@MetaCommand
class CleanCommand(setuptools.Command):
    """Clean build artifacts and virtual envs"""

    direct = set(".cache .tox build dist venv".split())
    ignored = set(".git .gradle .idea .venv".split())
    dirs = set("__pycache__".split())
    extensions = set("egg-info pyc pyo pyd".split())

    deleted = 0
    by_ext = None

    def delete(self, full_path):
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
            print("deleted %s" % setupmeta.relative_path(full_path))
        else:
            os.unlink(full_path)
            self.by_ext[full_path.rpartition(".")[2]] += 1
        self.deleted += 1

    def clean_direct(self):
        for target in self.direct:
            full_path = setupmeta.project_path(target)
            if os.path.exists(full_path):
                self.delete(full_path)

    def run(self):
        self.deleted = 0
        self.by_ext = collections.defaultdict(int)
        self.clean_direct()
        for dirpath, dirnames, filenames in os.walk(setupmeta.MetaDefs.project_dir):
            remove = []
            for dname in dirnames:
                if dname in self.ignored:
                    remove.append(dname)
                elif dname in self.dirs:
                    remove.append(dname)
                    self.delete(os.path.join(dirpath, dname))
                else:
                    ext = dname.rpartition(".")[2]
                    if ext in self.extensions:
                        remove.append(dname)
                        self.delete(os.path.join(dirpath, dname))
            for dname in remove:
                dirnames.remove(dname)
            for fname in filenames:
                ext = fname.rpartition(".")[2]
                if ext in self.extensions:
                    self.delete(os.path.join(dirpath, fname))
        if self.by_ext:
            info = ["%s .%s files" % (v, k) for k, v in sorted(self.by_ext.items())]
            print("deleted %s" % ", ".join(info))
        if self.deleted == 0:
            print("all clean, no deletable files found")


@MetaCommand
class TwineCommand(setuptools.Command):
    """upload binary package to PyPI using twine"""

    user_options = [
        ("commit", "c", "commit publishing (dryrun by default)"),
        ("rebuild", "r", "clean and rebuild before publishing"),
        ("egg=", "e", "build/publish egg"),
        ("sdist=", "s", "build/publish source distribution"),
        ("wheel=", "w", "build/publish wheel"),
    ]

    def initialize_options(self):
        major, minor = (sys.version_info.major, sys.version_info.minor)
        self.current_python = ["%s.%s" % (major, minor), "%s%s" % (major, minor)]
        self.commit = 0
        self.rebuild = 0
        self.egg = None
        self.sdist = None
        self.wheel = None

    def clean(self, *relative_paths):
        for relative_path in relative_paths:
            path = setupmeta.project_path(relative_path)
            if not os.path.exists(path):
                continue
            if self.commit:
                print("Deleting %s..." % path)
                shutil.rmtree(path)
            else:
                print("Would delete %s" % path)

    def should_run(self, value):
        return value == "all" or value in self.current_python

    def run_command(self, message, *args):
        if not self.commit:
            print("Would %s: %s" % (message, setupmeta.represented_args(args)))
            return

        first, _, rest = message.partition(" ")
        first = "%s%s" % (first[0].upper(), first[1:])
        message = "%sing %s..." % (first, rest)
        print(message)
        setupmeta.run_program(*args, fatal=True)

    def run(self):
        if platform.python_implementation() != "CPython":
            abort("twine command not supported on %s" % platform.python_implementation())

        if not self.egg and not self.sdist and not self.wheel:
            abort("Specify at least one of: --egg, --dist or --wheel")

        twine = setupmeta.which("twine")
        if not twine:
            abort("twine is not installed")

        if not self.commit:
            print("Dryrun, use --commit to effectively build/publish")

        dist = setupmeta.project_path("dist")
        self.clean("dist", "build")

        try:
            if self.should_run(self.egg):
                self.run_command("build egg distribution", sys.executable, "setup.py", "bdist_egg")

            if self.should_run(self.sdist):
                self.run_command("build source distribution", sys.executable, "setup.py", "sdist")

            if self.should_run(self.wheel):
                self.run_command("build wheel distribution", sys.executable, "setup.py", "bdist_wheel", "--universal")

            if self.commit and not os.path.exists(dist):
                abort("No files found in %s" % dist)

            files = [os.path.join(dist, name) for name in sorted(os.listdir(dist))] if self.commit else ["dist/*"]
            self.run_command("upload to PyPi via twine", twine, "upload", *files)

        finally:
            self.clean("build")
