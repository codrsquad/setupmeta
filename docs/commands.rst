Commands
========

``setupmeta`` also introduces a few commands to make your life easier
(more to come in the future).


explain
=======

``python setup.py explain`` will show you what ``setupmeta`` found out about your project,
what definitions came from where.

For example, this is what setupmeta says about itself (it's self-using)::

    ~/dev/setupmeta: python setup.py explain

                           author: (auto-adjust            ) Zoran Simic
                               \_: (setupmeta/__init__.py:6) Zoran Simic zoran@simicweb.com
                     author_email: (auto-adjust            ) zoran@simicweb.com
                      classifiers: (classifiers.txt        ) 21 items: ["Development Status :: 5 - Production/Stable", "Intend...
                      description: (setupmeta/__init__.py:2) Simplify your setup.py
                     download_url: (auto-fill              ) https://github.com/codrsquad/setupmeta/archive/v2.1.1.tar.gz
                               \_: (setupmeta/__init__.py:5) archive/v{version}.tar.gz
                     entry_points: (explicit               ) [distutils.commands] check = setupmeta.commands:CheckCommand clea...
                         keywords: (setup.py:4             ) ["simple", "DRY", "setup.py"]
                          license: (auto-fill              ) MIT
                 long_description: (README.rst             ) Simplify your setup.py ====================== .. image:: https://...
    long_description_content_type: (README.rst             ) text/x-rst
                             name: (setup.py:16            ) setupmeta
                         packages: (auto-fill              ) ["setupmeta"]
                   setup_requires: (explicit               ) ["setupmeta"]
                    tests_require: (tests/requirements.txt ) ["mock", "pytest-cov"]
                           title*: (setup.py:16            ) setupmeta
                              url: (setupmeta/__init__.py:4) https://github.com/codrsquad/setupmeta
                          version: (git                    ) 2.1.1
                       versioning: (explicit               ) dev
                         zip_safe: (explicit               ) True

In the above output:

* All the ``explicit`` mentions mean that associated values were seen mentioned explicitly
  in setup.py, and were left untouched

* The ``author`` key was seen in ``setupmeta/__init__.py`` line 6, and the value was name + email,
  that got "auto-adjusted" and filled-in as ``author`` + ``author_email`` properly as shown.

* Note that the ``\_`` indication tries to convey the fact that ``author`` in this example
  had a value that came from 2 different sources, final value showing at top,
  while all the other values seen showing below with the ``\_`` indicator.

* ``classifiers`` came from file ``classifiers.txt``

* ``description`` came from ``setup.py`` line 2

* ``download_url`` was defined in ``setupmeta/__init__.py`` line 5, since it was mentioning
  ``{version}`` (and was a relative path), it got auto-expanded and filled in properly

* ``entry_points`` were explicitly stated (in project's setup.py)

* ``long_description`` came from ``README.rst``

* ``name`` came from line 16 of setup.py, note that ``title`` also came from that line -
  this simply means the constant ``__title__`` was used as ``name``

* ``tests_require`` was deduced from ``tests/requirements.txt``

* Note that ``title*`` is shown with an asterisk, the asterisk means that setupmeta sees
  the value and can use it, but doesn't transfer it to setuptools

* ``packages`` was auto-filled to ``["setupmeta"]``

* ``version`` was determined from git tag (due to ``versioning="post"`` in setup.py),
  in this case ``1.1.2.post1+g816252c`` means:

    * latest tag was 1.1.2

    * there was 1 commit since that tag (``.post1`` means 1 change since tag,
      ``".post"`` denotes this would be a "post-release" version,
      and should play nicely with PEP-440_)

    * the ``+g816252c`` suffix means that the checkout wasn't clean when ``explain`` command
      was ran, local checkout was dirty at short git commit id "816252c"


If you'd like to see what your ``setup.py`` would look like without setupmeta
(and/or if you wish to get rid of setupmeta), you can run::

    python setup.py explain --expand


This will show you a copy-pastable ``setup.py`` that is the equivalent of not having setupmeta
at all (obviously without support for versioning etc).


version
=======

If you're using the ``versioning=...`` feature, you can then use the
``python setup.py version --bump=<what>`` command to bump your git-tag driven version.
See ``--help`` for more info.

Typical usage::

    python setup.py version --help              # What were the options?
    python setup.py version                     # Show current version and exit
    python setup.py version --show-next minor   # Show next minor version and exit
    python setup.py version --bump minor        # Dryrun bump: see what would be done
    python setup.py version --b minor --commit  # Effectively bump


cleanall
========

Handily clean build artifacts. Cleans the usual suspects:
``.cache/ .tox/ build/ dist/ venv/ __pycache__/ *.egg-info *.py[cod]``.

Example::

    🦎 3.9 ~/dev/github/setupmeta: ./setup.py cleanall
    running cleanall
    deleted .tox
    deleted setupmeta.egg-info
    deleted examples/direct/__pycache__
    deleted examples/hierarchical/__pycache__
    deleted examples/single/__pycache__
    deleted setupmeta/__pycache__
    deleted tests/__pycache__
    deleted tests/scenarios/complex/tests/__pycache__
    deleted tests/scenarios/readmes/__pycache__
    deleted 14 .pyc files


entrypoints
===========

This will simply show you your ``entry_points/console_scripts``.
Can be handy for pygradle_ users.

Example::

    🦎 3.9 ~/github/pickley: python setup.py entrypoints

    pickley = pickley.cli:protected_main

.. _PEP-440: https://www.python.org/dev/peps/pep-0440/

.. _pygradle: https://github.com/linkedin/pygradle/
