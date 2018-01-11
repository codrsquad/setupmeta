import os
import platform
import re
import shutil
import tempfile

from mock import patch
from six import StringIO

import setupmeta
from . import conftest


def run_setup_py(args, expected, folder=conftest.PROJECT_DIR):
    expected = expected.splitlines()
    output = conftest.run_setup_py(folder, *args)
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


def test_version():
    run_setup_py(['version', '--bump', 'major', '--simulate-branch=HEAD'], "Can't bump branch 'HEAD'")

    run_setup_py(
        ['version', '--bump', 'major', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m "Version [\d.]+"
            Would run: git push --tags origin
        """
    )

    run_setup_py(
        ['version', '--bump', 'minor', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m "Version [\d.]+"
            Would run: git push --tags origin
        """
    )

    run_setup_py(
        ['version', '-b', 'patch', '--simulate-branch=master'],
        """
            Not committing bump, use --commit to commit
            Would run: git tag -a v[\d.]+ -m "Version [\d.]+"
            Would run: git push --tags origin
        """
    )


@patch('sys.stdout.isatty', return_value=True)
@patch('os.popen', return_value=StringIO('60'))
@patch.dict(os.environ, {'TERM': 'testing'})
def test_console(*_):
    setupmeta.Console._columns = None
    assert setupmeta.Console.columns() == 60


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


def copy_to(src, dest, basename=None):
    basename = basename or os.path.basename(src)
    d = os.path.join(dest, basename)
    if os.path.isdir(src):
        shutil.copytree(src, d)
        return
    shutil.copy2(src, d)


def test_twine():
    temp = tempfile.mkdtemp()

    try:
        copy_to(setupmeta.project_path('examples', 'single', 'setup.py'), temp)
        copy_to(setupmeta.project_path('examples', 'single', 'single.py'), temp)

        if platform.python_implementation() != "CPython":
            run_setup_py(['twine'], "twine command not supported on ", folder=temp)
            return

        run_setup_py(['twine'], "Specify at least one of: --egg, --dist or --wheel", folder=temp)
        run_setup_py(['twine', '--egg=all'], "twine is not installed", folder=temp)

        copy_to(setupmeta.project_path('tests', 'mock-twine'), temp, basename='twine')

        run_setup_py(
            ['twine', '--egg=all'],
            """
                Dryrun, use --commit to effectively build/publish
                Would build egg distribution: .*python.* setup.py bdist_egg
                Would upload to PyPi via twine
            """,
            folder=temp
        )

        run_setup_py(
            ['twine', '--commit', '--egg=all', '--wheel=1.0'],
            """
                python.* setup.py bdist_egg
                Uploading to PyPi via twine
                Running: <target>/twine upload <target>/dist/single-0.1.0-.+.egg
                Deleting <target>/build
            """,
            folder=temp
        )

        run_setup_py(
            ['twine', '--egg=all'],
            """
                Would delete .*/dist
                Would build egg distribution: .*python.* setup.py bdist_egg
                Would upload to PyPi via twine
            """,
            folder=temp
        )

        run_setup_py(
            ['twine', '--commit', '--rebuild', '--egg=all', '--sdist=all', '--wheel=all'],
            """
                Deleting <target>/dist
                python.* setup.py bdist_egg
                python.* setup.py sdist
                python.* setup.py bdist_wheel
                Uploading to PyPi via twine
                Running: <target>/twine upload <target>/dist
                Deleting <target>/build
            """,
            folder=temp
        )

        run_setup_py(
            ['twine', '--commit', '--rebuild', '--egg=1.0'],
            """
                Deleting <target>/dist
                No files found in <target>/dist
            """,
            folder=temp
        )

    finally:
        shutil.rmtree(temp)
