import os
import re
import shutil
import sys
import tempfile

from mock import patch
from six import StringIO

import setupmeta
from setupmeta.commands import Console
from . import conftest


def run_setup_py(args, expected, folder=conftest.PROJECT_DIR):
    expected = expected.splitlines()
    setup_py = os.path.join(folder, 'setup.py')
    with conftest.capture_output() as out:
        setupmeta.DEBUG = True
        setupmeta.run_program(sys.executable, setup_py, *args, capture=True, fatal=True)
        setupmeta.DEBUG = False
        output = out.to_string()
        for line in expected:
            line = line.strip()
            if not line:
                continue
            m = re.search(line, output)
            assert m, "'%s' not present in output of '%s': %s" % (line, ' '.join(args), output)


def test_explain():
    """ Test setupmeta's own setup.py """
    run_setup_py(
        ['explain'],
        """
            author:.+ Zoran Simic
            description:.+ Simplify your setup.py
            license:.+ MIT
            url:.+ https://github.com/zsimic/setupmeta
            version:.+ [0-9]+\.[0-9]
        """
    )


def test_bump():
    run_setup_py(['bump'], "Specify exactly one of --major, --minor or --patch")
    run_setup_py(['bump', '--major', '--simulate-branch=HEAD'], "Can't bump branch 'HEAD'")

    run_setup_py(
        ['bump', '--major', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m "Version [\d.]+"
            Would run: git push --tags origin
        """
    )

    run_setup_py(
        ['bump', '--minor', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m "Version [\d.]+"
            Would run: git push --tags origin
        """
    )

    run_setup_py(
        ['bump', '-p', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m "Version [\d.]+"
            Would run: git push --tags origin
        """
    )


@patch('sys.stdout.isatty', return_value=True)
@patch('os.popen', return_value=StringIO('60'))
def test_console(*_):
    Console._columns = None
    assert Console.columns() == 60


def touch(folder, isdir, *paths):
    for path in paths:
        full_path = os.path.join(folder, path)
        if isdir:
            os.mkdir(full_path)
        else:
            with open(full_path, 'w') as fh:
                fh.write("from setuptools import setup\nsetup(setup_requires='setupmeta')\n")


def test_clean():
    temp = tempfile.mkdtemp()
    touch(temp, True, '.idea', 'build', 'dd', 'dd/__pycache__', 'foo.egg-info')
    touch(temp, False, 'foo', 'a.pyc', '.pyo', 'bar.pyc', 'setup.py', 'dd/__pycache__/a.pyc')
    run_setup_py(
        ['cleanall'],
        """
        deleted build
        deleted foo.egg-info
        deleted dd/__pycache__
        deleted 2 .pyc files, 1 .pyo files
        """,
        folder=temp
    )
    # Run a 2nd time: nothing to be cleaned anymore
    run_setup_py(['cleanall'], "all clean, no deletable files found", folder=temp)
    shutil.rmtree(temp)
