"""
Commands contributed by setupmeta
"""

import os
import setuptools
import setuptools.command.test
import shutil
import sys

from setupmeta.content import MetaCommand, project_path
from setupmeta.toml import parsed_toml


def run_program(*commands):
    """ Run shell program 'commands' """
    import subprocess
    p = subprocess.Popen(commands)
    if p.returncode:
        sys.exit(p.returncode)


@MetaCommand
class ExplainCommand(setuptools.Command):
    """ Show a report of where key/values setup(attr) come from """

    def run(self):
        print("Definitions:")
        print("------------")
        print(self.setupmeta.explain())


@MetaCommand
class EntryPointsCommand(setuptools.Command):
    """ List entry points for pygradle consumption """

    def run(self):
        entry_points = self.setupmeta.value('entry_points')
        entry_points = parsed_toml(entry_points)
        if not entry_points:
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


@MetaCommand
class TestCommand(setuptools.command.test.test):
    """ Run all tests via py.test """

    def run_tests(self):
        try:
            import pytest

        except ImportError:
            print('pytest is not installed, falling back to default')
            return setuptools.command.test.test.run_tests(self)

        suite = self.setupmeta.value('test_suite') or 'tests'
        args = ['-vvv'] + suite.split()
        errno = pytest.main(args)
        sys.exit(errno)


@MetaCommand
class UploadCommand(setuptools.Command):
    """ Build and publish the package """

    def run(self):
        try:
            print('Cleaning up dist...')
            dist = project_path('dist')
            shutil.rmtree(dist)
        except OSError:
            pass

        print('Building Source and Wheel (universal) distribution...')
        run_program(
            sys.executable,
            project_path('setup.py'),
            'sdist',
            'bdist_wheel',
            '--universal'
        )

        print('Uploading the package to pypi via twine...')
        os.system('twine upload dist/*')
        sys.exit()
