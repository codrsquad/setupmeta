"""
Verify that ../examples/*/setup.py behave as expected
"""

import imp
import os
import sys

import pytest
from . import conftest
from . import scenarios

from setupmeta.content import load_contents


@pytest.fixture(params=scenarios.scenario_paths())
def scenario(request):
    """ Yield one test per scenario """
    yield request.param


def load_module(full_path):
    """ Load module pointed to by 'full_path' """
    fp = None
    try:
        folder = os.path.dirname(full_path)
        basename = os.path.basename(full_path).replace('.py', '')
        fp, pathname, description = imp.find_module(basename, [folder])
        imp.load_module(basename, fp, pathname, description)
    finally:
        if fp:
            fp.close()


def run_scenario(folder):
    """ Run 'setup_py' with 'command' """
    setup_py = os.path.join(folder, 'setup.py')
    old_argv = sys.argv
    try:
        result = []
        for command in scenarios.get_scenario_commands(folder):
            with conftest.capture_output() as logged:
                sys.argv = [setup_py] + command.split()
                run_output = ''
                try:
                    load_module(setup_py)

                except SystemExit as e:
                    run_output += "'%s' exited with code 1:\n" % command
                    run_output += "%s\n" % e

                run_output = "%s\n%s" % (logged.to_string().strip(), run_output.strip())
                result.append(run_output.strip())

        return "\n\n".join(result)

    finally:
        sys.argv = old_argv


def test_scenario(scenario):
    """ Check that 'scenario' yields expected explain output """
    expected = os.path.join(scenario, 'expected.txt')
    expected = load_contents(expected).strip()
    output = run_scenario(scenario)
    assert output == expected
