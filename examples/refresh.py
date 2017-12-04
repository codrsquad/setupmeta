#!/usr/bin/env python

import argparse
import logging
import os
import subprocess
import sys


EXAMPLES = os.path.abspath(os.path.dirname(__file__))
PPATH = os.path.dirname(EXAMPLES)
COMMANDS = 'explain entrypoints'.split()


sys.path.insert(0, PPATH)
from setupmeta.content import to_str    # noqa


def run_command(path, command):
    os.chdir(path)
    cmd = [sys.executable, 'setup.py', command]
    logging.debug("Running: %s", cmd)
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(PYTHONPATH=PPATH)
    )
    output, error = p.communicate()
    if p.returncode:
        print("examples/%s exited with code %s, output:" % (
            os.path.basename(path),
            p.returncode
        ))
        print(output)
        print(error)
        sys.exit(p.returncode)
    return to_str(output) + to_str(error)


def refresh_example(path, dryrun):
    logging.info("Refreshing %s" % (os.path.basename(path)))
    setup_py = os.path.join(path, 'setup.py')
    if not os.path.isfile(setup_py):
        return
    expected = os.path.join(path, 'expected.txt')
    output = ''
    for command in COMMANDS:
        output += "Replay: %s\n" % command
        output += "%s\n" % run_command(path, command)
    if dryrun:
        print(output)
        return
    with open(expected, 'w') as fh:
        fh.write(output)


def main():
    """
    Refresh examples/*/expected.txt
    """
    parser = argparse.ArgumentParser(description=main.__doc__.strip())
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Show debug info"
    )
    parser.add_argument(
        '-n', '--dryrun',
        action='store_true',
        help="Print output rather, don't update expected.txt"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=level
    )
    logging.root.setLevel(level)

    examples = os.listdir(EXAMPLES)
    for name in examples:
        path = os.path.join(EXAMPLES, name)
        if not os.path.isdir(path):
            continue
        refresh_example(path, dryrun=args.dryrun)


if __name__ == "__main__":
    main()
