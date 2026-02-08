"""
Verify that ../examples/*/setup.py behave as expected
"""

import subprocess
import sys

import pytest

import setupmeta

from . import conftest, scenarios


@pytest.fixture(params=scenarios.scenario_paths())
def scenario_folder(request):
    """Yield one test per scenario"""
    with setupmeta.temp_resource():
        yield request.param


def test_scenario(scenario_folder):
    """Check that 'scenario' yields expected explain output"""
    with conftest.capture_output():
        scenario = scenarios.Scenario(scenario_folder)
        assert str(scenario) == scenario_folder
        expected = scenario.expected_contents()
        output = scenario.replay()
        assert output == expected


def test_adhoc_replay():
    with setupmeta.current_folder(conftest.PROJECT_DIR):
        result = subprocess.run([sys.executable, "tests/scenarios.py", "replay", "examples/single"], capture_output=True)  # noqa: S603
        assert result.returncode == 0
        output = setupmeta.decode(result.stdout)
        assert "OK, no diffs found" in output
