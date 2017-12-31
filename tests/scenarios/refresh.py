#!/usr/bin/env python

import argparse
from io import open
import logging
import os
import subprocess           # nosec
import sys

from setupmeta import decode

SCENARIOS = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCENARIOS))
EXAMPLES = os.path.join(PROJECT_DIR, 'examples')
COMMANDS = ['explain -c161', 'entrypoints']


def relative_path(full_path):
    return full_path[len(PROJECT_DIR) + 1:]


def run_command(path, command):
    os.chdir(path)
    cmd = [sys.executable, 'setup.py'] + command.split()
    logging.debug("Running: %s", cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)   # nosec
    output, error = p.communicate()
    output = decode(output)
    error = decode(error)
    if p.returncode:
        print("examples/%s exited with code %s, output:" % (os.path.basename(path), p.returncode))
        print(output)
        print(error)
        sys.exit(p.returncode)
    return output


def refresh_example(path, dryrun):
    logging.info("Refreshing %s" % relative_path(path))
    setup_py = os.path.join(path, 'setup.py')
    if not os.path.isfile(setup_py):
        return
    expected = os.path.join(path, 'expected.txt')
    output = ''
    for command in COMMANDS:
        output += "%s\n" % run_command(path, command)
    if dryrun:
        print(output)
        return
    with open(expected, 'wt', encoding='utf-8') as fh:
        fh.write(output)


def run(folder, dryrun=False):
    files = os.listdir(folder)
    for name in files:
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            refresh_example(full_path, dryrun=dryrun)


def main():
    """
    Refresh tests/scenarios/*/expected.txt and examples/*/expected.txt
    """
    parser = argparse.ArgumentParser(description=main.__doc__.strip())
    parser.add_argument('--debug', action='store_true', help="Show debug info")
    parser.add_argument('-n', '--dryrun', action='store_true', help="Print output rather, don't update expected.txt")
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)
    logging.root.setLevel(level)

    run(SCENARIOS, dryrun=args.dryrun)
    run(EXAMPLES, dryrun=args.dryrun)


if __name__ == "__main__":
    main()
