#!/usr/bin/env python

import argparse
from io import open
import logging
import os
import subprocess
import sys

import conftest


IGNORED_ERRORS = 'debugger UserWarning warnings.warn'.split()


def cleaned_error(error):
    error = conftest.decode(error)
    result = []
    for line in error.splitlines():
        line = line.strip()
        if line and all(m not in line for m in IGNORED_ERRORS):
            result.append(line)
    return '\n'.join(result)


def run_scenario_command(scenario, command):
    os.chdir(scenario)
    cmd = [sys.executable, 'setup.py'] + command.split()
    logging.debug("Running: %s", cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)   # nosec
    output, error = p.communicate()
    output = conftest.decode(output) or ''
    if p.returncode:
        output = output.strip()
        output += "\n'%s' exited with code %s:\n%s\n" % (command, p.returncode, cleaned_error(error))
    return output


def run_scenario(scenario):
    output = ''
    commands = conftest.get_scenario_commands(scenario)
    for command in commands:
        output += "%s\n\n" % run_scenario_command(scenario, command).strip()
    return "%s\n" % output.strip()


def refresh_example(scenario, dryrun):
    logging.info("Refreshing %s" % conftest.relative_path(scenario))
    setup_py = os.path.join(scenario, 'setup.py')
    if not os.path.isfile(setup_py):
        return
    expected = os.path.join(scenario, 'expected.txt')
    output = run_scenario(scenario)
    if dryrun:
        print(output)
        return
    with open(expected, 'wt', encoding='utf-8') as fh:
        fh.write(output)


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

    for scenario in conftest.scenario_paths():
        refresh_example(scenario, dryrun=args.dryrun)


if __name__ == "__main__":
    main()
