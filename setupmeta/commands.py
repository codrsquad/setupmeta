"""
Commands contributed by setupmeta
"""

import setuptools
import sys

from setupmeta.content import MetaCommand, MetaDefs, short
from setupmeta.versioning import bump


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
        self.major = 0
        self.minor = 0
        self.patch = 0
        self.commit = 0

    def run(self):
        bump(
            self.setupmeta,
            self.major,
            self.minor,
            self.patch,
            self.commit
        )


@MetaCommand
class ExplainCommand(setuptools.Command):
    """ Show a report of where key/values setup(attr) come from """

    user_options = [
        ('chars=', 'c', "max chars to show"),
    ]

    def initialize_options(self):
        self.chars = 200

    def run(self):
        try:
            self.chars = int(self.chars)
        except ValueError:
            self.chars = 200

        definitions = self.setupmeta.definitions
        if not definitions:
            return

        longest_key = min(24, max(len(key) for key in definitions))
        sources = sum((d.sources for d in definitions.values()), [])
        longest_source = min(32, max(len(s.source) for s in sources))
        form = "%%%ss: (%%%ss) %%s" % (longest_key, -longest_source)
        max_chars = max(60, self.chars - longest_key - longest_source - 4)

        for definition in sorted(definitions.values()):
            count = 0
            for source in definition.sources:
                if count:
                    prefix = "\_"
                elif source.key not in MetaDefs.all_fields:
                    prefix = "%s*" % source.key
                else:
                    prefix = source.key

                preview = short(source.value, c=max_chars)
                print(form % (prefix, source.source, preview))
                count += 1


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
