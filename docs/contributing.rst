Contributions are welcome!

``setupmeta`` has no dependencies, it should work as-is
(standard libs only + obviously setuptools_).

tox_ is used for building and testing.

Development
===========

To get going locally, simply do this::

    git clone https://github.com/codrsquad/setupmeta.git
    cd setupmeta

    tox -e venv

    # You have a venv now in ./.venv, use it, open it with pycharm etc
    source .venv/bin/activate
    which python
    python setup.py explain
    python setup.py version

    # You can use this local setupmeta now on another project's setup.py
    # (provided it has setup_requires='setupmeta')
    python .../path/to/some/project/setup.py explain

    deactivate



Running the tests
=================

To run the tests, simply run ``tox``, this will run tests against all python versions you have
locally installed. You can use pyenv_ for example to get python installations.

Run:

* ``tox -e py27`` (for example) to limit test run to only one python version.

* ``tox -e style`` to run style checks only

* ``tox -e docs`` to verify that the main README.rst renders properly

* ``tox -e security`` to run the security checks


Test coverage
=============

A coverage report is generated on all ``tox`` runs
(coverage is combined across all the exercised python versions),

Run this to  see the generated html report::

    open .tox/coverage/index.html


Refreshing the test scenarios
=============================

If you've modified the code, and the tests don't pass anymore because you added/removed/changed
something, you can refresh the test scenario replays by running::

    tox -e refreshscenarios


Inspect the diff (``git diff``), verify that the changes to
``tests/scenarios/*/expected.txt`` look good before committing

Note that the tests replay ``tests/scenarios/*`` as well as ``examples/*``


.. _pyenv: https://github.com/pyenv/pyenv

.. _setuptools: https://github.com/pypa/setuptools

.. _tox: https://github.com/tox-dev/tox
