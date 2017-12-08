"""
Commands contributed by setupmeta
"""

import os
import setuptools
import setuptools.command.test
import shutil
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


def run_setup_py(*commands):
    print("Running: setup.py %s" % ' '.join(commands))
    return run_program(sys.executable, project_path('setup.py'), *commands)


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
        dist_folder = project_path('dist')
        try:
            print('Cleaning up dist...')
            dist = project_path(dist_folder)
            shutil.rmtree(dist)
        except OSError:
            pass

        # if docutils installed:
        # run_setup_py('check', '--strict', '--restructuredtext')
        run_setup_py('sdist')

        if not os.path.isdir(dist_folder):
            sys.exit("'dist' dir was not created")

        print('Uploading the package to pypi via twine...')
        files = []
        for name in os.listdir(dist_folder):
            if name.endswith('.tar.gz'):
                files.append(os.path.join(dist_folder, name))
        run_program('twine', 'upload', *files)
        sys.exit()
