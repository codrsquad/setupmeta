import os
import re

from mock import patch
from six import StringIO
from . import conftest

import setupmeta
from setupmeta.commands import Console


def run_setup_py(args, expected):
    expected = expected.splitlines()
    setup_py = os.path.join(conftest.PROJECT_DIR, 'setup.py')
    with conftest.capture_output() as out:
        setupmeta.DEBUG = True
        setupmeta.run_program(setup_py, *args, capture=True)
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
            Would run: git tag -a v[\d.]+ -m Version [\d.]+
            Would run: git push --tags origin
        """
    )

    run_setup_py(
        ['bump', '--minor', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m Version [\d.]+
            Would run: git push --tags origin
        """
    )

    run_setup_py(
        ['bump', '-p', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m Version [\d.]+
            Would run: git push --tags origin
        """
    )


@patch('sys.stdout.isatty', return_value=True)
@patch('os.popen', return_value=StringIO('60'))
def test_console(*_):
    Console._columns = None
    assert Console.columns() == 60
