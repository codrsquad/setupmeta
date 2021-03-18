Simplify your setup.py
======================

.. image:: https://img.shields.io/pypi/v/setupmeta.svg
    :target: https://pypi.org/project/setupmeta/
    :alt: Version on pypi

.. image:: https://github.com/codrsquad/setupmeta/workflows/Tests/badge.svg
    :target: https://github.com/codrsquad/setupmeta/actions
    :alt: Tested with Github Actions

.. image:: https://codecov.io/gh/codrsquad/setupmeta/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/codrsquad/setupmeta
    :alt: Test code codecov

.. image:: https://img.shields.io/pypi/pyversions/setupmeta.svg
    :target: https://github.com/codrsquad/setupmeta
    :alt: Python versions tested (link to github project)

----

Writing a ``setup.py`` typically involves lots of boilerplate and copy-pasting from project to project.

This package aims to simplify that and bring some DRY_ principle to python packaging_.
Here's what your (complete, and ready to ship to pypi) ``setup.py`` could look like with setupmeta_::

    from setuptools import setup

    setup(
        name="myproject",
        versioning="distance",          # Optional, would activate tag-based versioning
        setup_requires="setupmeta"      # This is where setupmeta comes in
    )

And that should be it - setupmeta_ will take it from there, extracting everything else from the rest of your project
(following typical conventions commonly used).

You can use the **explain** command (see commands_) to see what setupmeta_ deduced from your project,
for the above it would look something like this (you can see which file and which line each setting came from,
note that a lot of info is typically extracted from your project, if you follow usual conventions)::

    ~/myproject: python setup.py explain

              author: (auto-adjust     ) Your Name
                  \_: (myproject.py:7  ) Your Name<your@email.com>
        author_email: (auto-adjust     ) your@email.com
         description: (README.rst:1    ) First line of your README
        entry_points: (entry_points.ini) [console_scripts] ...
    install_requires: (requirements.txt) ["click", ...
             license: (auto-fill       ) MIT
    long_description: (README.rst      ) Long description would be your inlined README
                name: (explicit        ) myproject
          py_modules: (auto-fill       ) ["myproject"]
      setup_requires: (explicit        ) ["setupmeta"]
             version: (git             ) 1.2.3.post2
          versioning: (explicit        ) distance

See examples_ for more.

**Note**: ``setupmeta``'s versioning is based on::

    git describe --dirty --tags --long --match *.* --first-parent

you will need **git version >= 1.8.4** if you wish to use ``setupmeta``'s versioning capabilities.


Goal
====

The goal of this project is to:

* Allow to write very short (yet complete) ``setup.py``-s, without boilerplate, and encourage good common packaging_ practices

* Point out missing important info (example: version) in ``setup.py explain``

* Support tag-based versioning_ (like setuptools_scm_, but with super simple configuration/defaults and automated ``bump`` capability)

* Provide useful Commands_ to see the metadata (**explain**), **version** (including support for bumping versions),
  **cleanall**, etc


How it works?
=============

* Everything that you explicitly provide in your original ``setuptools.setup()`` call is taken as-is (never changed),
  and internally labelled as ``explicit``.
  So if you don't like something that setupmeta_ deduces, you can always explicitly state it.

* ``name`` is auto-filled from your setup.py's ``__title__`` (if there is one, sometimes having a constant is quite handy...)

* ``packages`` and ``package_dir`` is auto-filled accordingly if you have a ``<name>/__init__.py`` or ``src/<name>/__init__.py`` file

* ``py_modules`` is auto-filled if you have a ``<name>.py`` file

* ``entry_points`` is auto-filled from file ``entry_points.ini`` (bonus: tools like PyCharm have a nice syntax highlighter for those)

* ``install_requires`` is auto-filled if you have a ``requirements.txt`` (or ``pinned.txt``) file,
  pinning is abstracted away by default as per `community recommendation`_, see requirements_ for more info.

* ``tests_require`` is auto-filled if you have a ``tests/requirements.txt``, or ``requirements-dev.txt``,
  or ``dev-requirements.txt``, or ``test-requirements.txt`` file

* ``description`` will be the 1st line of your README (unless that 1st line is too short, or is just the project's name),
  or the 1st line of the first docstring found in the scanned files (see list below)

* ``long_description`` is auto-filled from your README file (looking for ``README.rst``, ``README.md``,
  then ``README*``, first one found wins).
  Special tokens can be used (notation aimed at them easily being `rst comments`_):

    * ``.. [[end long_description]]`` as end marker, so you don't have to use the entire file as long description

    * ``.. [[include <relative-path>]]`` if you want another file included as well (for example, people like to add ``HISTORY.txt`` as well)

    * these tokens must appear either at beginning/end of line, or be after/before at least one space character

* ``version`` can be stated explicitly, or be computed from git tags using ``versioning=...`` (see versioning_ for more info):

    * With ``versioning="distance"``, your git tags will be of the form ``v{major}.{minor}.0``,
      the number of commits since latest version tag will be used to auto-fill the "patch" part of the version:

        * tag "v1.0.0", no commits since tag -> version is "1.0.0"

        * tag "v1.0.0", 5 commits since tag -> version is "1.0.5"

        * if checkout is dirty, a marker is added -> version would be "1.0.5.post5.dirty"

    * With ``versioning="post"``, your git tags will be of the form ``v{major}.{minor}.{patch}``,
      a "post" addendum will be present if there are commits since latest version tag:

        * tag "v1.0.0", no commits since tag -> version is "1.0.0"

        * tag "v1.0.0", 5 commits since tag -> version is "1.0.0.post5"

        * if checkout is dirty, a marker is added -> version would be "1.0.0.post5.dirty"

    * With ``versioning="build-id"``, your git tags will be of the form ``v{major}.{minor}.0``,
      the number of commits since latest version tag will be used to auto-fill the "patch" part of the version:

        * tag "v1.0.0", no commits since tag, ``BUILD_ID=12`` -> version is "1.0.0+h12.g123"

        * tag "v1.0.0", no commits since tag, ``BUILD_ID`` not defined -> version is "1.0.0+hlocal.g123"

        * tag "v1.0.0", 5 commits since tag, ``BUILD_ID=12`` -> version is "1.0.5+h12.g456"

        * tag "v1.0.0", 5 commits since tag, ``BUILD_ID`` not defined -> version is "1.0.5+hlocal.g456"

        * if checkout is dirty, a marker is added -> version would be "1.0.5+hlocal.g456.dirty"

    * Use the **bump** command (see commands_) to easily bump (ie: increment major, minor or patch + apply git tag)

    * Version format can be customized, see versioning_ for more info

* ``version``, ``versioning``, ``url``, ``download_url``, ``bugtrack_url``, ``license``, ``keywords``, ``author``, ``contact``, ``maintainer``,
  and ``platforms`` will be auto-filled from:

    * Lines of the form ``__key__ = "value"`` in your modules (simple constants only,
      expressions are ignored - the modules are not imported but scanned using regexes)

    * Lines of the form ``key: value`` in your docstring

    * Files are examined in this order (first find wins):

        * ``setup.py``

        * ``<package>.py`` (mccabe_ for example)

        * ``<package>/__about__.py`` (cryptography_ for example)

        * ``<package>/__version__.py`` (requests_ for example)

        * ``<package>/__init__.py`` (changes_, arrow_ for example)

        * ``src/`` is also examined (for those who like to have their packages under ``src``)

    * URLs can be simplified:

        * if ``url`` points to your general github repo (like: https://github.com/codrsquad),
          the ``name`` of your project is auto-appended to it

        * relative urls are auto-filled by prefixing them with ``url``

        * urls may use ``{name}`` and/or ``{version}`` markers, it will be expanded appropriately

    * ``author``, ``maintainer`` and ``contact`` names and emails can be combined into one line
      (setupmeta_ will figure out the email part and auto-fill it properly)

        * i.e.: ``author: Bob D bob@example.com`` will yield the proper ``author`` and ``author_email`` settings


This should hopefully work nicely for the vast majority of python projects out there.
If you need advanced stuff, you can still leverage setupmeta_ for all the usual stuff above, and go explicit wherever needed.


.. _DRY: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself

.. _commands: https://github.com/codrsquad/setupmeta/blob/master/docs/commands.rst

.. _requirements: https://github.com/codrsquad/setupmeta/blob/master/docs/requirements.rst

.. _versioning: https://github.com/codrsquad/setupmeta/blob/master/docs/versioning.rst

.. _community recommendation: https://packaging.python.org/discussions/install-requires-vs-requirements/

.. _packaging: https://python-packaging.readthedocs.io/en/latest/

.. _setuptools_scm: https://github.com/pypa/setuptools_scm

.. _setupmeta: https://github.com/codrsquad/setupmeta

.. _examples: https://github.com/codrsquad/setupmeta/tree/master/examples

.. _rst comments: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#comments

.. _requests: https://github.com/requests/requests/tree/master/requests

.. _cryptography: https://github.com/pyca/cryptography/tree/master/src/cryptography

.. _changes: https://github.com/michaeljoseph/changes/blob/master/changes/__init__.py

.. _arrow: https://github.com/crsmithdev/arrow/blob/master/arrow/__init__.py

.. _mccabe: https://github.com/PyCQA/mccabe/blob/master/mccabe.py

.. [[end long_description]]


Motivation
==========

My motivation was to:

* stop having to boilerplate my setup.py's

* learn how to publish to pypi (and do it right, once and for all)

* have a nice workflow for when I want to publish to pypi (``setup.py explain`` to see what's up at a glance)

I noticed that most open-source projects out there do the same thing over and over, like:

* Read the entire contents of their README file and use it as ``long_description``
  (copy-pasting the few lines of code to read the contents of said file)

* Reading, grepping, sometimes importing a small ``__version__.py`` or ``__about__.py`` file to get values like ``__version__`` out of it,
  and then dutifully doing ``version=__version__`` or ``version=about["__version__"]`` in their ``setup.py``

* All kinds of creative things to get the ``description``

* etc.

I didn't want to keep doing this anymore myself, so I decided to try and do something about it with this project.


Roadmap
=======

* Support more SCMs, like ``hg``


Test coverage
=============

Since setupmeta is designed to be used as ``setup_requires``, it is important it doesn't break in any edge case,
as that would be disruptive to all clients.

Test coverage is at 100%, and should remain at that at all times. If you are contributing, please craft test cases
that exercise all possible edge cases.
