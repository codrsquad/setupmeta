"""
Commands contributed by setupmeta
"""

import setuptools
import sys

import setupmeta


def abort(message):
    sys.stderr.write("%s\n" % message)
    sys.exit(1)


def MetaCommand(cls):
    """ Decorator allowing for less boilerplate in our commands """
    return setupmeta.MetaDefs.register_command(cls)


@MetaCommand
class BumpCommand(setuptools.Command):
    """ Bump version managed by setupmeta """

    user_options = [
        ('major', 'M', "bump major part of version"),
        ('minor', 'm', "bump minor part of version"),
        ('patch', 'p', "bump patch part of version"),
        ('commit', 'c', "commit changes"),
        ('all', 'a', "commit all pending (default: restrict to bumps)"),
    ]

    def initialize_options(self):
        self.major = 0
        self.minor = 0
        self.patch = 0
        self.commit = 0
        self.all = 0

    def run(self):
        flags = self.major + self.minor + self.patch
        if flags != 1:
            abort("Specify exactly one of --major, --minor or --patch")

        what = 'major' if self.major else 'minor' if self.minor else 'patch'
        try:
            self.setupmeta.versioning.bump(what, self.commit, self.all)

        except setupmeta.UsageError as e:
            abort(e)


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
                elif source.key not in setupmeta.MetaDefs.all_fields:
                    prefix = "%s*" % source.key
                else:
                    prefix = source.key

                preview = setupmeta.short(source.value, c=max_chars)
                print(form % (prefix, source.source, preview))
                count += 1


@MetaCommand
class EntryPointsCommand(setuptools.Command):
    """ List entry points for pygradle consumption """

    def run(self):
        entry_points = self.setupmeta.value('entry_points')
        console_scripts = get_console_scripts(entry_points)
        if not console_scripts:
            return
        if isinstance(console_scripts, list):
            for ep in console_scripts:
                print(ep)
            return
        for key, value in console_scripts.items():
            print("%s = %s" % (key, value))


def get_console_scripts(entry_points):
    """
    pygradle's 'entrypoints' are misnamed: they really mean 'consolescripts'
    """
    if not entry_points:
        return None
    if isinstance(entry_points, dict):
        return entry_points.get('console_scripts')
    if isinstance(entry_points, list):
        result = []
        in_console_scripts = False
        for line in entry_points:
            line = line.strip()
            if not line:
                continue
            if line.startswith('['):
                in_console_scripts = 'console_scripts' in line
                continue
            if not in_console_scripts:
                continue
            result.append(line)
        return result
    return get_console_scripts(entry_points.split('\n'))
