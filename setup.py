#!/usr/bin/env python
#  -*- encoding: utf-8 -*-
"""
keywords: simple, DRY, setup.py
"""

# This library is self-using and auto-bootstraps itself

import os
import subprocess  # nosec
import sys

import setuptools


__title__ = "setupmeta"

HERE = os.path.dirname(os.path.abspath(__file__))
EGG = os.path.join(HERE, "%s.egg-info" % __title__)

ENTRY_POINTS = """
[distutils.commands]
check = {t}.commands:CheckCommand
cleanall = {t}.commands:CleanCommand
entrypoints = {t}.commands:EntryPointsCommand
explain = {t}.commands:ExplainCommand
twine = {t}.commands:TwineCommand
version = {t}.commands:VersionCommand

[distutils.setup_keywords]
setup_requires = {t}.hook:register
versioning = {t}.hook:register
""".format(
    t=__title__
)


def decode(text):
    if isinstance(text, bytes):
        return text.decode("utf-8")
    return text


def run_bootstrap(message):
    sys.stderr.write("--- Bootstrapping %s\n" % message)
    p = subprocess.Popen([sys.executable, "setup.py", "egg_info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # nosec
    output, error = p.communicate()
    if p.returncode:
        print(output)
        sys.stderr.write("%s\n" % decode(error))
        sys.exit(p.returncode)
    if not os.path.isdir(EGG):
        sys.exit("Could not bootstrap egg-info")


def complete_args(args):
    args["setup_requires"] = [__title__]
    args["versioning"] = "dev"


if __name__ == "__main__":
    os.chdir(HERE)
    have_egg = os.path.isdir(EGG)

    # Explicit on entry points due to bootstrap
    args = dict(entry_points=ENTRY_POINTS, zip_safe=True)

    if have_egg:
        # We're bootstrapped, we can self-refer
        complete_args(args)

    if len(sys.argv) == 2 and sys.argv[1] == "egg_info":
        # egg_info as lone command is bootstrap mode
        if not have_egg:
            # Very first bootstrap needs some help
            # We do want all subsequent runs to guess name, packages etc
            args["name"] = __title__
            args["packages"] = [__title__]

        setuptools.setup(**args)
        sys.exit(0)

    if not have_egg:
        # No egg yet, not running egg_info -> must bootstrap
        run_bootstrap("first pass")

        # Rerun one more time to get the right VERSION filled-in etc
        run_bootstrap("second pass")

        # We're bootstrapped now, we can self-refer
        complete_args(args)

    setuptools.setup(**args)
