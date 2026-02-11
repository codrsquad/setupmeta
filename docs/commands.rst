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
                     bugtrack_url: (auto-fill              ) https://github.com/codrsquad/setupmeta/issues
                      classifiers: (explicit               ) 23 items: ["Development Status :: 5 - Production/Stable", "Intend...
                      description: (setupmeta/__init__.py:2) Simplify your setup.py
                     download_url: (auto-fill              ) https://github.com/codrsquad/setupmeta/archive/v3.9.0.tar.gz
                               \_: (setupmeta/__init__.py:5) archive/v{version}.tar.gz
                     entry_points: (explicit               ) [distutils.commands] check = setupmeta.commands:CheckCommand expla...
             include_package_data: (MANIFEST.in            ) True
                 install_requires: (explicit               ) ["setuptools>=67"]
                          license: (auto-fill              ) MIT
                 long_description: (README.rst             ) Simplify your setup.py ====================== .. image:: https://...
    long_description_content_type: (README.rst             ) text/x-rst
                             name: (explicit               ) setupmeta
                         packages: (explicit               ) ["setupmeta"]
                  python_requires: (explicit               ) >=3.7
                   setup_requires: (explicit               ) ["setupmeta"]
                              url: (setupmeta/__init__.py:4) https://github.com/codrsquad/setupmeta
                          version: (git                    ) 3.9.0
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

* ``classifiers`` came from explicit settings in ``setup.py``

* ``description`` came from ``setupmeta/__init__.py`` line 2

* ``download_url`` was defined in ``setupmeta/__init__.py`` line 5, since it was mentioning
  ``{version}`` (and was a relative path), it got auto-expanded and filled in properly

* ``entry_points`` were explicitly stated (in project's setup.py)

* ``long_description`` came from ``README.rst``

* ``name`` came from an explicit setting in setup.py

* ``packages`` came from explicit settings in setup.py

* ``version`` was determined from git (due to ``versioning="dev"`` in setup.py),
  in this case ``3.9.0`` means current commit is exactly on a version tag


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


.. _PEP-440: https://www.python.org/dev/peps/pep-0440/
