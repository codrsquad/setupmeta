"""
Verify that ../examples/*/setup.py behave as expected
"""

import sys

import pytest

import setupmeta

from . import conftest, scenarios


@pytest.fixture(params=scenarios.scenario_paths())
def scenario_folder(request):
    """Yield one test per scenario"""
    with setupmeta.temp_resource():
        yield request.param


def test_scenario(scenario_folder, monkeypatch):
    """Check that 'scenario' yields expected explain output"""
    monkeypatch.setenv("SETUPMETA_RUNNING_SCENARIOS", "1")
    with conftest.capture_output():
        scenario = scenarios.Scenario(scenario_folder)
        assert str(scenario) == scenario_folder
        expected = scenario.expected_contents()
        output = scenario.replay()
        assert output == expected


def test_adhoc_replay():
    with setupmeta.current_folder(conftest.PROJECT_DIR):
        result = setupmeta.run_program(sys.executable, "tests/scenarios.py", "replay", "tests/scenarios/bogus")
        assert result.returncode == 0
        output = conftest.cleaned_output(result)
        assert "OK, no diffs found" in output
