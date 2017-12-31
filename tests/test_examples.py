"""
Verify that ../examples/*/setup.py behave as expected
"""

import imp
import os
import sys

import pytest
from . import conftest

from setupmeta.content import extract_list, load_list

SCENARIOS = conftest.resouce('scenarios')
EXAMPLES = os.path.join(conftest.PROJECT, 'examples')
COMMANDS = ['explain -c161', 'entrypoints']


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


@pytest.fixture(params=scenario_paths())
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


def run(setup_py):
    """ Run 'setup_py' with 'command' """
    old_argv = sys.argv
    try:
        with conftest.capture_output() as logged:
            for command in COMMANDS:
                sys.argv = [setup_py] + command.split()
                load_module(setup_py)
            return logged.to_string()
    finally:
        sys.argv = old_argv


def test_scenario(scenario):
    """ Check that 'scenario' yields expected explain output """
    setup_py = os.path.join(scenario, 'setup.py')
    output = extract_list(run(setup_py))
    path = os.path.join(scenario, 'expected.txt')
    expected = load_list(path)
    assert expected == output
