Simplify your setup.py
======================

.. image:: https://img.shields.io/pypi/v/setupmeta.svg
    :target: https://pypi.org/project/setupmeta/
    :alt: Version on pypi

.. image:: https://github.com/codrsquad/setupmeta/workflows/Tests/badge.svg
    :target: https://github.com/codrsquad/setupmeta/actions
    :alt: Tested with Github Actions

.. image:: https://coveralls.io/repos/github/codrsquad/setupmeta/badge.svg?branch=main
    :target: https://coveralls.io/github/codrsquad/setupmeta?branch=main
    :alt: Code coverage with coveralls

.. image:: https://img.shields.io/pypi/pyversions/setupmeta.svg
    :target: https://github.com/codrsquad/setupmeta
    :alt: Python versions tested (link to github project)

.. image:: https://img.shields.io/conda/vn/conda-forge/setupmeta
    :target: https://anaconda.org/conda-forge/setupmeta
    :alt: Version on conda-forge

----

setupmeta_ derives your project's version from git tags, bumps it for you, and fills in the
rest of your ``setup.py`` metadata from the files your project already has.
A complete, ready to publish ``setup.py`` can look like this::

    from setuptools import setup

    setup(
        name="myproject",
        versioning="distance",      # Optional: activates git-tag-based versioning
        setup_requires="setupmeta",  # This is what activates setupmeta
    )

Run ``python setup.py explain`` to see every setting setupmeta determined, along with the
file and line each value came from. Anything you pass explicitly to ``setup()`` (or state in
``setup.cfg``) is used as-is, so you can always override what setupmeta deduces.


Versioning
==========

Versioning is opt-in: pass a ``versioning=`` strategy to ``setup()`` (or state it like any
other auto-filled value, see below). The version then comes from::

    git describe --dirty --tags --long --first-parent --match 'v*.*'

which requires git 1.8.4 or later. Only tags starting with ``v`` count (configurable with
``version_tag``, see below). Without any version tag, the version starts from ``0.0.0``.

The preconfigured strategies yield PEP-440_ compliant versions:

=========================  =====================  ====================  ===============
State of the checkout      ``post``               ``dev``               ``distance``
=========================  =====================  ====================  ===============
No commit yet              ``0.0.0``              ``0.0.0``             ``0.0.0``
1 commit, no tag yet       ``0.0.0.post1``        ``0.0.1.dev1``        ``0.0.1``
Same, with pending change  ``0.0.0.post1+dirty``  ``0.0.1.dev1+dirty``  ``0.0.1+dirty``
Exactly on tag ``v0.1.0``  ``0.1.0``              ``0.1.0``             ``0.1.0``
Same, with pending change  ``0.1.0+dirty``        ``0.1.1.dev0+dirty``  ``0.1.0+dirty``
2 commits after the tag    ``0.1.0.post2``        ``0.1.1.dev2``        ``0.1.2``
=========================  =====================  ====================  ===============

- ``post`` suits projects that tag each release and publish occasionally.

- ``dev`` makes untagged versions pre-releases (``pip install --pre`` to get them),
  assuming the next bump will be a ``patch``.

- ``distance`` suits publishing at every commit: the patch number is the count of commits
  since the latest ``v{major}.{minor}.0`` tag, so only ``major`` and ``minor`` can be bumped.

- ``devcommit`` is ``dev`` plus the commit id when not exactly on a tag:
  ``0.1.1.dev2+g2cff0a6``.

- ``build-id`` is ``distance`` plus a local part that is always shown, made of the first env
  var whose name ends with ``BUILD_ID`` (or ``local``) and the commit id:
  ``0.1.2+h12.g2cff0a6`` on a CI server, ``0.1.2+hlocal.g2cff0a6`` locally.


Bumping
-------

``python setup.py version`` shows the current version, ``--show-next minor`` the next one.
``--bump major|minor|patch`` does a dry run of a bump; add ``--commit`` to apply the
``v<version>`` git tag, and ``--push`` to also push it. A bump is refused when:

- the current branch isn't allowed (``main`` or ``master`` by default),
- ``--commit`` is given while the checkout has pending changes,
- the remote has tags missing locally, or the local branch is behind its remote.

You don't need a ``__version__`` anywhere, but if one is stated in your ``.py`` files,
setupmeta warns when it disagrees with the git tag, and a bump rewrites and commits it first.


Custom formats
--------------

``versioning`` also accepts a format string of the form ``branch(<branches>):<main>+<local>``,
for example ``branch(main,release):{major}.{minor}.{patch}{post}+{commitid}{dirty}``.
The ``branch(...):`` prefix lists the branches where bumps are allowed, and is optional.
These can be used:

- ``{major}``, ``{minor}``, ``{patch}``: components of the latest version tag

- ``{distance}``: number of commits since that tag

- ``{post}``, ``{dev}``: ``.postN`` or ``.devN`` when not exactly on a tag (``N`` being
  ``{distance}``, and ``{dev}`` also bumping ``patch``)

- ``{devcommit}``, ``{commitid}``, ``{dirty}``: ``.g<sha>`` when not exactly on a tag,
  ``g<sha>`` always, and ``.dirty`` when there are pending changes

- ``{$FOO}``: value of env var ``FOO``; ``{$FOO:default}`` gives a default for when it's
  undefined (otherwise ``None`` is shown); ``$*FOO``, ``$FOO*`` and ``$*FOO*`` match the first
  (alphabetically) env var whose name ends with, starts with or contains ``FOO``

- anything else is used as-is

Markers other than ``{major}``, ``{minor}``, ``{patch}``, ``{distance}``, ``{post}`` and ``{dev}``
are moved to the local part if placed in the main part, as PEP-440 requires.
``post+build-id`` and ``dev+devcommit`` are shortcuts for adding the local part of the
``build-id`` or ``devcommit`` strategies to another one.

For full control, pass a dict: ``main`` and ``extra`` (format strings, or callables receiving a
``setupmeta.scm.Version``; a callable ``main`` disables bumps), ``branches`` (list or
comma-separated string), and ``version_tag`` (glob of git tags to consider, default ``v*.*``).


Environment
-----------

- ``SETUPMETA_GIT_DESCRIBE_COMMAND`` replaces the ``git describe`` command above (give the
  full command, without the leading ``git``).

- ``SCM_DESCRIBE`` takes a ``git describe``-like output (eg: ``v1.2.0-3-g1234567``) and uses it
  instead of asking git, for builds where no git checkout is available.

- When ``setup.py`` lives in a subfolder of a git checkout, setupmeta writes the version to a
  ``.setupmeta.version`` file next to it, and uses that file when the project is later built
  from a copy that has no ``.git``.


Auto-filled metadata
====================

setupmeta fills in what you didn't state explicitly, following the usual conventions:

- ``name``: from a ``__title__`` stated in ``setup.py``.

- ``packages`` / ``py_modules``: when neither is given, all packages found under ``src/``
  (setting ``package_dir`` accordingly), or else the packages whose name starts with your
  project's name, or a ``<name>.py`` module.

- Simple settings like ``version``, ``versioning``, ``url``, ``download_url``,
  ``bugtrack_url``, ``license``, ``keywords``, ``author``, ``maintainer``, ``contact``, or
  ``platforms``, from lines like ``__author__ = "..."`` (modules are scanned, never imported),
  or ``author: ...`` lines in the first paragraph of a docstring. First found wins, looking in
  ``setup.py``, then ``<name>.py``, then ``__about__.py``, ``__version__.py`` and
  ``__init__.py`` of your top level packages (also under ``src/``).

- ``author``, ``maintainer``, ``contact``: a value like ``Bob D bob@example.com`` is split
  into name and ``*_email``.

- ``url``: when pointing to a github org (like ``https://github.com/codrsquad``), your
  project's name is appended, and ``bugtrack_url`` defaults to its ``issues`` page.
  Relative ``download_url`` and ``bugtrack_url`` are prefixed with ``url``, and all of them can
  use ``{name}`` and ``{version}`` markers.

- ``description``: the first line of your README, unless it's too short or just your
  project's name, in which case the first line of the docstring of a scanned module is used.

- ``long_description`` (and its content type): your README (``README.rst``, ``README.md``,
  then ``README*``). A line ``.. [[end long_description]]`` ends it early, and
  ``.. [[include <relative-path>]]`` includes another file; both must stand alone on their line.

- ``entry_points``: contents of an ``entry_points.ini`` file.

- ``license``: recognized from the text of a ``LICENSE*`` file.

- ``include_package_data``: ``True`` when there's a ``MANIFEST.in``.

- ``install_requires``: see below.

When building from an sdist, values recorded in its ``PKG-INFO`` are used.


Requirements
------------

When ``install_requires`` isn't given, it comes from ``requirements.in`` (used as-is), else
``requirements.txt``, where simple ``name==version`` pins are abstracted down to ``name``, as per
this `community recommendation`_ (a library shouldn't impose pins on its users). ``-r other.txt`` references are followed. ``install_requires="@path/to/reqs.txt"`` uses a
given file, and works for ``extras_require`` values too.

A comment can mark a line, or start a section applying to all lines below it, with one of:

- ``# abstract`` (the default): ``name==version`` pins become ``name``
- ``# pinned``: kept as-is
- ``# indirect``: left out of ``install_requires`` altogether

Only plain ``==`` pins are abstracted: ``click>=7.0`` is always kept as-is. For example::

    click==8.1.7
    requests==2.31.0  # pinned
    retry>=0.9

    # indirect
    urllib3==2.2.1

yields ``install_requires=["click", "requests==2.31.0", "retry>=0.9"]``.


Commands
========

setupmeta adds these ``setup.py`` commands, see ``python setup.py <command> --help``:

- ``explain``: show all settings and where each came from; ``--dependencies`` shows how
  requirements were auto-filled, ``--expand`` prints the equivalent ``setup.py`` without
  setupmeta (handy if you ever want to stop using it).

- ``version``: show or bump the version, see Bumping_.

- ``check``: setuptools' ``check``, also reporting how many requirements were abstracted or
  ignored, and the pending changes (useful to tell why a CI build saw a dirty checkout).

Set ``SETUPMETA_DEBUG=1`` to trace what setupmeta does.


.. _setupmeta: https://github.com/codrsquad/setupmeta

.. _PEP-440: https://peps.python.org/pep-0440/

.. _community recommendation: https://packaging.python.org/discussions/install-requires-vs-requirements/

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

See examples_ for sample projects, and docs_ for how setupmeta works inside.

.. _examples: https://github.com/codrsquad/setupmeta/tree/main/examples

.. _docs: https://github.com/codrsquad/setupmeta/blob/main/docs/index.md
