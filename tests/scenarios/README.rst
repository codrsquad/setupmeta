Test scenarios
==============

This folder contains test case scenarios. The tests consist of:

* one scenario folder with a ``setup.py`` and other typical files found in a python project

* examples_ subfolders are also used as test case scenarios (the cases there are more "vanilla", while the cases here are edge-case oriented)

* commands ``explain`` and ``entrypoints`` are ran on each example, and their output is compared to ``expected.txt`` (has to match)

* `scenarios.py`_ (or ``tox -e refreshscenarios``) can be used to regenerate ``expected.txt`` (see ``git diff`` to verify changes look good)

* `test_scenarios.py`_ replays all scenarios and verifies that output matches ``expected.txt``



.. _examples: https://github.com/codrsquad/setupmeta/tree/master/examples

.. _test_scenarios.py: https://github.com/codrsquad/setupmeta/blob/master/tests/test_scenarios.py

.. _scenarios.py: https://github.com/codrsquad/setupmeta/blob/master/tests/scenarios.py
