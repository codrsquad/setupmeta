"""
Simplify your setup.py

This setup.py is self-using and auto-bootstraps itself

keywords: convenient, setup.py
"""

import os
import setuptools
import subprocess
import sys


__title__ = 'setupmeta'

HERE = os.path.dirname(os.path.abspath(__file__))
EGG = os.path.join(HERE, '%s.egg-info' % __title__)

ENTRY_POINTS = """
[distutils.commands]
explain = {t}:ExplainCommand
entrypoints = {t}:EntryPointsCommand
test = {t}:TestCommand
upload = {t}:UploadCommand

[distutils.setup_keywords]
setup_requires = {t}:register
""".format(t=__title__)


def run_bootstrap(message):
    print("--- Bootstrapping %s" % message)
    p = subprocess.Popen(
        [sys.executable, 'setup.py', 'egg_info'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, error = p.communicate()
    if p.returncode:
        sys.stdout.write(output)
        sys.stderr.write(error)
        sys.exit(p.returncode)
    if not os.path.isdir(EGG):
        sys.exit("Could not bootstrap egg-info")


if __name__ == "__main__":
    os.chdir(HERE)
    args = dict(
        name=__title__,
        py_modules=[__title__],
        zip_safe=True,
        entry_points=ENTRY_POINTS
    )

    if os.path.isdir(EGG):
        # We're bootstrapped, we can self-refer
        args['setup_requires'] = [__title__]

    if len(sys.argv) == 2 and sys.argv[1] == 'egg_info':
        # egg_info as lone command is bootstrap mode
        setuptools.setup(**args)
        sys.exit(0)

    if not os.path.isdir(EGG):
        # No egg yet, not running egg_info -> must bootstrap
        run_bootstrap("first pass")
        # Rerun one more time to get the right VERSION filled-in etc
        run_bootstrap("second pass")

        # We're bootstrapped now, we can self-refer
        args['setup_requires'] = [__title__]
        import setupmeta
        setupmeta.register()

    setuptools.setup(**args)
