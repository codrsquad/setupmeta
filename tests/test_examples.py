"""
Verify that ../examples/*/setup.py behave as expected
"""

import imp
import os
import re
import sys
import pytest

from setupmeta import to_str
from setupmeta.content import extract_list, load_list, short
from . import conftest


EXAMPLES = os.path.join(conftest.PROJECT, 'examples')
COMMANDS = ['explain -t replay', 'entrypoints']


def scenario_names():
    """ Available scenario names """
    names = []
    for name in os.listdir(EXAMPLES):
        if os.path.isdir(os.path.join(EXAMPLES, name)):
            names.append(name)
    return names


@pytest.fixture(params=scenario_names())
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


def run_shell(*command):
    import subprocess
    p = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, error = p.communicate()
    assert p.returncode == 0
    return to_str(output) + to_str(error)


def test_scenario(scenario):
    """ Check that 'scenario' yields expected explain output """
    setup_py = os.path.join(EXAMPLES, scenario, 'setup.py')
    output = extract_list(run(setup_py))
    path = os.path.join(EXAMPLES, scenario, 'expected.txt')
    expected = load_list(path)
    assert expected == output


def chk(output, message):
    assert re.search(message, output), "'%s' not present in '%s'" % (message, short(output)) # noqa


def test_self():
    """ Test setupmeta's own setup.py """
    out = run_shell(
        sys.executable,
        os.path.join(conftest.PROJECT, 'setup.py'),
        'explain'
    )
    chk(out, "author:.+ Zoran Simic")
    chk(out, "description:.+ Simplify your setup.py")
    chk(out, "license:.+ MIT")
    chk(out, "url:.+ https://github.com/zsimic/setupmeta")
    chk(out, "version:.+ [0-9]+\.[0-9]")
