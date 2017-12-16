"""
Commands contributed by setupmeta
"""

import os
import setuptools
import sys

import setupmeta
from setupmeta.content import MetaCommand, project_path


def which(program):
    if not program:
        return None
    if os.path.isabs(program):
        return program
    for p in os.environ.get('PATH', '').split(':'):
        fp = os.path.join(p, program)
        if os.path.isfile(fp):
            return fp
    return None


def run_program(program, *commands):
    """ Run shell program 'commands' """
    import subprocess                                   # nosec
    full_path = which(program)
    if not full_path:
        sys.exit("'%s' is not installed" % program)
    p = subprocess.Popen([full_path] + list(commands))  # nosec
    p.wait()
    if p.returncode:
        sys.exit(p.returncode)


@MetaCommand
class ExplainCommand(setuptools.Command):
    """ Show a report of where key/values setup(attr) come from """

    user_options = [
        ('title=', 't', "title to use as header")
    ]

    def initialize_options(self):
        self.title = "setupmeta v%s" % setupmeta.__version__

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
