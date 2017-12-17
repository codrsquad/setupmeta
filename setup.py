#!/usr/bin/env python
#  -*- encoding: utf-8 -*-
"""
keywords: convenient, setup.py
"""

# This setup.py is self-using and auto-bootstraps itself

import os
import setuptools
import subprocess       # nosec
import sys


__title__ = 'setupmeta'

HERE = os.path.dirname(os.path.abspath(__file__))
EGG = os.path.join(HERE, '%s.egg-info' % __title__)

ENTRY_POINTS = """
[distutils.commands]
explain = {t}.commands:ExplainCommand
entrypoints = {t}.commands:EntryPointsCommand

[distutils.setup_keywords]
setup_requires = {t}.hook:register
""".format(t=__title__)


def to_str(text):
    if isinstance(text, bytes):
        return text.decode('utf-8')
    return text


def run_bootstrap(message):
    sys.stderr.write("--- Bootstrapping %s\n" % message)
    p = subprocess.Popen(                           # nosec
        [sys.executable, 'setup.py', 'egg_info'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, error = p.communicate()
    if p.returncode:
        print(output)
        sys.stderr.write("%s\n" % to_str(error))
        sys.exit(p.returncode)
    if not os.path.isdir(EGG):
        sys.exit("Could not bootstrap egg-info")


if __name__ == "__main__":
    os.chdir(HERE)
    have_egg = os.path.isdir(EGG)

    args = dict(
        # Explicit on entry points due to bootstrap
        entry_points=ENTRY_POINTS,
        zip_safe=True,
    )

    if have_egg:
        # We're bootstrapped, we can self-refer
        args['setup_requires'] = [__title__]

    if len(sys.argv) == 2 and sys.argv[1] == 'egg_info':
        # egg_info as lone command is bootstrap mode
        if not have_egg:
            # Very first bootstrap needs some help
            # We do want all subsequent runs to guess name, packages etc
            args['name'] = __title__
            args['packages'] = [__title__]

        setuptools.setup(**args)
        sys.exit(0)

    if not have_egg:
        # No egg yet, not running egg_info -> must bootstrap
        run_bootstrap("first pass")

        # Rerun one more time to get the right VERSION filled-in etc
        run_bootstrap("second pass")

        # We're bootstrapped now, we can self-refer
        args['setup_requires'] = [__title__]

    setuptools.setup(**args)
