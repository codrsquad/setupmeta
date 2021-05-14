=============
Release notes
=============

3.2.0 (2021-05-17)
------------------

* Do not abstract ``requirements.in`` files any more, use them as-is (since they're intended to
  be a spec for pip-compile_)

* Next minor version of setupmeta will not auto-fill ``tests_require`` any more.


3.1.0 (2021-04-15)
------------------

* Don't try and modify any git url from ``requirements.txt``, it is too much of a moving target
  and the whole thing is debated: https://github.com/pypa/pip/issues/5898

* Do not auto-fill any ``dependency_links`` at all


3.0.0 (2021-03-22)
------------------

* Yield PEP-440_ compliant versions

* Versions yielded by ``setupmeta`` 3.0 will differ from pre-3.0 versions:

  * Character ``"+"`` is used exclusively to demarcate the local part of the version

  * Character ``"."`` is used exclusively to demarcate local segments
    (this is not configurable yet, and won't be unless by popular request)

  * The "main" part remains intact, except for ``devcommit``, furthermore only known PEP-440
    "main version part" bits can ever be in the main part (anything that is mistakenly
    specified to be in the main part gets automatically shifted to the local part)

  * "local" part is always shown now, no need to use ``"!"`` character (now deprecated),
    except for ``{devcommit}`` and ``{dirty}`` markers, which will not lead to a local part
    being shown when exactly on git tag.

  * See [pep-440.rst](./docs/pep-440.rst) for more details


2.9.0 (2021-03-15)
------------------

* Don't auto-complete ``classifiers`` from ``classifiers.txt`` any more,
  the added value of that is negligible (and potentially confusing)


2.8.3 (2021-01-07)
------------------

* Don't warn when bumping for the first time (with no git tags yet)

* Use the most common ``setuptools.find_packages()`` call (without arguments)

* Moved repo to https://github.com/codrsquad


2.8.2 (2020-11-19)
------------------

* Respect ``requirements.in`` when present


2.8.1 (2020-11-02)
------------------

* Explicitly state ``python_requires`` in ``setup.py`` to satisfy conda-forge linter

* Bundled tests in sdist, to allow for users wanting to rerun the tests to be able to do so from sdist

* Using https://pypi.org/project/check-manifest/


2.8.0 (2020-10-29)
------------------

* Removed commands ``twine`` and ``uber_egg``, turns out they're not useful


2.7.16 (2020-10-26)
-------------------

* Corrected egg publication for python 2.7


2.7.15 (2020-10-26)
-------------------

* Publish egg for python 3.9, not publishing for 3.5 any more

* Corrected support for inlined versions (``__version__ = "..."`` in user's code)

* Stop using deprecated ``imp`` module with python3

* Moved to github actions


2.7.14 (2020-08-26)
-------------------

* Corrected edge case to support git submodules


2.7.13 (2020-07-27)
-------------------

* Verify that HEAD is up-to-date when bumping (#57)


2.7.12 (2020-07-16)
-------------------

* Further refine hooks (#56)

  * Add legacy hook to ease transition in rare cases.

  * Ensure our dist finalization runs first.


2.7.11 (2020-06-30)
-------------------

* Simplify hooks, and fix preprocessing not triggering when not already installed in environment. (#54)


2.7.10 (2020-06-26)
-------------------

* Auto-populate requirements attrs using ``@<filepath>`` syntax. (#53)


2.7.9 (2020-06-17)
------------------

* Always ensure a number is added to version parts such as ``rc``, as per PEP-440_


2.7.8 (2020-05-21)
------------------

* Don't issue warnings related to versioning on fresh new (still empty) repos


2.7.7 (2020-05-14)
------------------

* Don't do full auto-fill when invoked with ``--name``

* Added tests, do not try to follow relative paths in ``requirements.txt`` (pip doesn't accept them anyway)


2.7.6 (2020-05-14)
------------------

* Avoid infinite recursion with ``setup.py --name``


2.7.5 (2020-05-14)
------------------

* Report package name in ``setup_requires`` when possible,
  for local projects referred to via ``-e /some/folder`` in a requirements file


2.7.4 (2020-05-06)
------------------

* Corrected auto-abstract for non-standard version pins such as ``foo==1.0-rc1+local-part``

* Added more debug tracing to help troubleshoot future issues (``SETUPMETA_DEBUG=1 setup.py ...``)

* Warn if no ``packages`` or ``py_modules`` are defined (empty package)


2.7.3 (2020-05-03)
------------------

* Added support for nested requirements: ``-r foo.txt`` will be now followed


2.7.2 (2020-04-30)
------------------

* Corrected bug: parsing ``PKG-INFO`` files properly


2.7.1 (2020-04-30)
-------------------

* Added ``requirements_from_text()`` and ``requirements_from_file()``

* Use a regex to determine simple pins of the form ``foo==1.0``

* Consistently apply auto-abstraction to ``tests_require`` as well

* Internally use consistent names for ``install_requires``, ``tests_require`` and ``extras_require``


2.7.0 (2020-04-29)
-------------------

* Do not use ``pip`` anymore to parse ``requirements.txt`` (#49)


2.6.24 (2020-03-31)
-------------------

* Added command ``uber_egg``, to support creating spark_-like "uber eggs"


2.6.20 (2020-03-03)
-------------------

* Corrected warning when hardcoded version found does not match git tag


2.6.19 (2020-03-02)
-------------------

* Auto-fill ``include_package_data`` when ``MANIFEST.in`` is present


2.6.18 (2020-02-03)
-------------------

* Try and import latest pip first


2.6.17 (2020-01-24)
-------------------

* Adapted ``get_pip()`` call to pip 20.0 API change

* Removed support for python 3.4 (not accepted by pypi anymore)


2.6.15 (2020-01-14)
-------------------

* Corrected handling of version tags such as ``v0.1.9-rc.1``


2.6.14 (2020-01-13)
-------------------

* Corrected ``packages`` auto-fill for projects using a direct layout

* Fix version pinning when ``setup_requires`` is a list


2.6.13 (2020-01-09)
-------------------

* Support project layout similar to pytest's

* Warn when ``git describe`` exits with code != 0

* Corrected tests for Windows

* Removed auto-added ``License :: OSI Approved`` classifier

* Corrected ``check --deptree`` edge cases

* RFC: include distance with "{devcommit}"

* Correctly mock absence of twine in tests

* Bug fix: Correctly initialize .links field in ``model.py``

* version: git: use --first-parent with git-describe

* Let pip expand req files when not abstracting

* Allow to override git describe command via env var GIT_DESCRIBE_COMMAND (just in case)

* Fixed incorrect tag mismatch warning with ``post`` versioning strategy

* Publish .egg for python 3.4 and 3.8

* Ignore unparseable ``requirements.txt``

* Changed default dirty marker to ``.dirty`` (instead of ``+{commitid}``)


2.5.4 (2019-05-08)
------------------

* Run only if explicitly required via ``setup_requires=["setupmeta"]``

* Properly handle package name (possible dashes) vs top-level module name (no dashes)

* Verify that all remote tags are present locally before allowing version bump

* Show top level deps in ``check --deptree``'s "other" section

* Added ``check --deptree``, to show dependency tree of package


2.4.3 (2019-02-12)
------------------

* Report version as dirty if there staged (but uncommitted changes)

* Show pending changes (if there are any) in ``setup.py check`` command

* Added a test exercising ``pip wheel`` to expose recent ``dirty`` determination issue

* Rolled back ``dirty`` checkout determination, repo with staged files is considered clean again,
  will have to find another fix for that edge case

* Push version bumps only when ``--push`` is explicitly specified


2.3.4 (2019-02-11)
------------------

* Always listify ``setup_requires``

* Better warnings message, should show proper origination

* Corrected ``dirty`` determination: repo with staged files is considered dirty until effective commit

* Extract all relevant info from ``PKG-INFO`` (not just version)

* Auto-fill ``bugtrack_url``

* Added support for version determination from PKG-INFO


2.2.1 (2018-10-23)
------------------

* Added ``version --show-next``

* Added ``{devcommit}`` versioning strategy token

* Added ``--expand`` to command ``explain``

* Better handling of unicode in ``README``-s and ``setup.py``-s

* Fixed setupmeta's own download_url


2.0.6 (2018-09-11)
------------------

* Show how many requirements_ were abstracted/skipped (if any) in ``setup.py check``

* Warn if current version tag mention patch while versioning strategy doesn't

* Make sure local tags match remote before pushing a new bumped version tag

* Auto-fill dependencies accordingly to recommendations in https://packaging.python.org/discussions/install-requires-vs-requirements/

* Added support for ``.dev`` versioning

* Added ``--dependencies`` to ``explain`` command


1.6.2 (2018-07-16)
------------------

* Auto-fill long_description_content_type when applicable


1.5.1 (2018-07-13)
------------------

* Test against python 3.7, dropped support for 3.4 as it's not available on travis Xenial

* Don't pass redundant ``bump`` cli arg to bump hook


1.4.5 (2018-04-17)
------------------

* Accept git version tags of the form ``M.m.p`` (don't require git tags to start with a ``v`` prefix)

* Support pip 10.0

* Use ``g0000000`` as commit-id instead of ``initial`` when no commit took place yet

* Hook earlier, into ``parse_command_line`` instead of ``get_option_dict`` in order for ``setup.py --version`` (and similar) to work

* Added pre-defined versioning strategy ``post``

* Renamed pre-defined versioning strategies, to better convey their intent: ``changes`` -> ``distance`` and ``tag`` -> ``post``


1.3.6 (2018-01-14)
------------------

* Env var ``SCM_DESCRIBE`` used if available and no SCM checkout folder (like ``.git``) detected

* Better support cases where project is in a subfolder of a git checkout

* Don't consider lack of version tag as dirty checkout (it's confusing otherwise)

* Parse correctly complex requirements.txt files

* Support setup.py in a subfolder of a git checkout

* Renamed command ``bump`` to ``version``, optional bump hook in ``./hooks/bump``

* Added commands: 'twine', 'cleanall'

* Added ``explain --recommend``

* Added pre-defined versioning strategy ``build-id``

* Test coverage at 100%, added debug info via env var ``SETUPMETA_DEBUG=1``


0.8.0 (2017-12-31)
------------------

* Versioning is more easily customizable, using post-release marker by default (instead of beta)

* Better defined versioning strategies

* Fully using setupmeta's own versioning scheme (no more "backup" version stated in ``__init__.py``)

* Versioning compatible with PEP-440

* Using ``versioning`` on setupmeta, which can now bump itself

* Added support for ``versioning`` key in setup.py, setupmeta can now compute version from git tags, and bump that version

* Removed support for Pipfile

* Testing with pypy as well, produce eggs for 2.7, 3.4, 3.5, 3.6


0.2.8 (2017-12-09)
------------------

* Always listify ``keywords``

* Auto-publishing via travis, publish wheels as well

* Look only at 1st paragraph of docstring for key/value definitions

* Auto-determine most common license, and associated classifier string

* Should work with any version of setuptools now, via ``setup_requires='setupmeta'``

* Removed old way, no more "drop setupmeta.py next to your setup.py" mode

* Fixed bootstrap, so that ``PKG-INFO`` gets the right metadata (bootstrapping in 2 passes)

* Use 1st line of README file as short description if no docstrings are found, accept description in project docstrings (not only setup.py)

* Allow to use portion of README via ``.. [[end long_description]]``

* Allow to use include other files in long description via something like ``.. [[include HISTORY.rst]]``


.. _requirements: https://github.com/codrsquad/setupmeta/blob/master/docs/requirements.rst

.. _spark: https://spark.apache.org/docs/latest/index.html

.. _PEP-440: https://www.python.org/dev/peps/pep-0440/#public-version-identifiers

.. _PEP-508: https://www.python.org/dev/peps/pep-0508/

.. _report: https://github.com/codrsquad/setupmeta/issues

.. _pip-compile: https://pypi.org/project/pip-tools/
