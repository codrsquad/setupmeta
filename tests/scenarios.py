#!/usr/bin/env python

import argparse
from io import open
import logging
import os
import subprocess
import sys

import conftest


SCENARIOS = os.path.join(conftest.TESTS, 'scenarios')
EXAMPLES = os.path.join(conftest.PROJECT_DIR, 'examples')

SCENARIO_COMMANDS = ['explain -c161', 'entrypoints']
IGNORED_ERRORS = 'debugger UserWarning warnings.warn'.split()


def valid_scenarios(folder):
    result = []
    for name in os.listdir(folder):
        full_path = os.path.join(folder, name)
        if os.path.isdir(full_path):
            result.append(full_path)
    return result


def scenario_paths():
    """ Available scenario names """
    return valid_scenarios(SCENARIOS) + valid_scenarios(EXAMPLES)


def get_scenario_commands(scenario):
    result = []
    result.extend(SCENARIO_COMMANDS)
    extra_commands = os.path.join(scenario, '.commands')
    if os.path.isfile(extra_commands):
        with open(extra_commands) as fh:
            for line in fh:
                line = conftest.decode(line).strip()
                if line:
                    result.append(line)
    return result


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
    commands = get_scenario_commands(scenario)
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

    for scenario in scenario_paths():
        refresh_example(scenario, dryrun=args.dryrun)


if __name__ == "__main__":
    main()
