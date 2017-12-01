#!/usr/bin/env python

import argparse
import io
import logging
import os
import subprocess
import sys


EXAMPLES = os.path.abspath(os.path.dirname(__file__))
PPATH = os.path.dirname(EXAMPLES)
COMMANDS = 'explain entrypoints'.split()


sys.path.insert(0, PPATH)


import setupmeta


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
    return setupmeta.to_str(output) + setupmeta.to_str(error)


def refresh_example(path):
    logging.info("Refreshing %s" % (os.path.basename(path)))
    setup_py = os.path.join(path, 'setup.py')
    if not os.path.isfile(setup_py):
        return
    expected = os.path.join(path, 'expected.txt')
    with open(expected, 'w') as fh:
        for command in COMMANDS:
            fh.write("Replay: %s\n" % command)
            fh.write("%s\n" % run_command(path, command))


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
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)
    logging.root.setLevel(level)

    examples = os.listdir(EXAMPLES)
    for name in examples:
        path = os.path.join(EXAMPLES, name)
        if not os.path.isdir(path):
            continue
        refresh_example(path)


if __name__ == "__main__":
    main()
