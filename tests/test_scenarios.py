"""
Verify that ../examples/*/setup.py behave as expected
"""

import sys

import pytest

import setupmeta

from . import scenarios


@pytest.fixture(params=scenarios.scenario_paths())
def scenario_folder(request):
    """Yield one test per scenario"""
    with setupmeta.temp_resource():
        yield request.param


@pytest.mark.skipif(sys.version_info.major < 3, reason="Sunsetting py2, minor diffs in warnings coming from old setuptools checks")
def test_scenario(scenario_folder):
    """Check that 'scenario' yields expected explain output"""
    py = ".".join(str(s) for s in sys.version_info[:2])
    if py < "3.7" and "via-cfg" in scenario_folder:
        # For some reason, older pythons don't all seem to handle setup.cfg well... maybe min version of setuptools needed?
        pytest.skip("via-cfg scenario useful only in 3.7+")

    scenario = scenarios.Scenario(scenario_folder)
    expected = scenario.expected_contents()
    output = scenario.replay()
    assert output == expected
