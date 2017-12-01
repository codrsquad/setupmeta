"""
Verify that all modules tests/scenarios/*/setup.py behave as expected
"""

import imp
import os
import re
import sys
import pytest

from conftest import capture_output, file_contents, resouce, PROJECT


def scenario_names():
    """ Available scenario names """
    names = []
    for name in os.listdir(resouce('scenarios')):
        if os.path.isdir(resouce('scenarios', name)):
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


def run(setup_py, command):
    """ Run 'setup_py' with 'command' """
    with capture_output() as logged:
        os.environ['COLUMNS'] = '160'
        old_argv = sys.argv
        sys.argv = [setup_py, 'explain']
        load_module(setup_py)
        sys.argv = old_argv
        return logged.to_string()


def verify_contains(expected, output):
    expected = expected.split('\n')
    remaining = output.split('\n')
    missing = []
    for line in expected:
        if line in remaining:
            remaining.remove(line)
            continue
        missing.append(line)
    if missing:
        missing = '\n'.join(missing)
        remaining = '\n'.join(remaining)
        msg = "Missing lines:\n%s\n\nfrom remaining output:\n%s" % (
            missing,
            remaining
        )
        assert False, msg


def test_scenario(scenario):
    """ Check that 'scenario' yields expected explain output """
    output = run(resouce('scenarios', scenario, 'setup.py'), 'explain')
    expected = file_contents('scenarios', scenario, 'explain.txt')
    verify_contains(expected, output)


def chk(output, message):
    assert re.search(message, output)


def test_self():
    """ Test setupmeta's own setup.py """
    path = os.path.join(PROJECT, 'setup.py')
    out = run(path, 'explain')
    chk(out, "author:.+ Zoran Simic")
    chk(out, "description:.+ Stop copy-paste technology in setup.py")
    chk(out, "version:.+ [0-9]+\.[0-9]")
    chk(out, "url:.+ https://github.com/zsimic/setupmeta")
