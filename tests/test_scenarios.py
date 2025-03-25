"""
Verify that ../examples/*/setup.py behave as expected
"""

import pytest

import setupmeta

from . import scenarios


@pytest.fixture(params=scenarios.scenario_paths())
def scenario_folder(request):
    """Yield one test per scenario"""
    with setupmeta.temp_resource():
        yield request.param


def test_scenario(scenario_folder):
    """Check that 'scenario' yields expected explain output"""
    scenario = scenarios.Scenario(scenario_folder)
    expected = scenario.expected_contents()
    output = scenario.replay()
    assert output == expected
