"""
Commands contributed by setupmeta
"""

import setuptools
import sys

import setupmeta
from setupmeta.content import MetaCommand
from setupmeta.versioning import git_version


def abort(message):
    sys.stderr.write("%s\n" % message)
    sys.exit(1)


@MetaCommand
class BumpCommand(setuptools.Command):
    """ Bump version """

    user_options = [
        ('major', 'M', "bump major part of version"),
        ('minor', 'm', "bump minor part of version"),
        ('patch', 'p', "bump patch part of version"),
        ('commit', 'c', "commit changes"),
    ]

    def initialize_options(self):
        self.major = None
        self.minor = None
        self.patch = None
        self.commit = None

    def run(self):
        gv = git_version()
        if not gv:
            abort("Could not determine version from git tags")
        print("Not yet implemented, stay tuned (%s %s %s)" % (self.major, self.minor, self.patch))


@MetaCommand
class ExplainCommand(setuptools.Command):
    """ Show a report of where key/values setup(attr) come from """

    user_options = [
        ('title=', 't', "title to use as header")
    ]

    def initialize_options(self):
        self.title = "setupmeta v%s" % getattr(setupmeta, '__version__', None)

    def run(self):
        print(self.title)
        print("-" * len(self.title))
        print(self.setupmeta.explain())


@MetaCommand
class EntryPointsCommand(setuptools.Command):
    """ List entry points for pygradle consumption """

    def run(self):
        entry_points = self.setupmeta.value('entry_points')
        if not entry_points:
            return
        if not isinstance(entry_points, dict):
            print(entry_points)
            return
        console_scripts = entry_points.get('console_scripts')
        if not console_scripts:
            return
        if isinstance(console_scripts, list):
            for ep in console_scripts:
                print(ep)
            return
        for key, value in console_scripts.items():
            print("%s = %s" % (key, value))
