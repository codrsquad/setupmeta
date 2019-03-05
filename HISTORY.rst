=======
History
=======

2.5.0 (2019-03-05)
------------------

* Added ``check --deptree``, to show dependency tree of package


2.4.3 (2019-02-12)
------------------

* Report version as dirty if there staged (but uncommitted changes)


2.4.2 (2019-02-12)
------------------

* Show pending changes (if there are any) in ``setup.py check`` command

* Added a test exercising ``pip wheel`` to expose recent ``dirty`` determination issue


2.4.1 (2019-02-12)
------------------

* Rolled back ``dirty`` checkout determination, repo with staged files is considered clean again,
  will have to find another fix for that edge case


2.4.0 (2019-02-12)
------------------

* Push version bumps only when ``--push`` is explicitly specified


2.3.4 (2019-02-11)
------------------

* Always listify ``setup_requires``


2.3.3 (2019-02-11)
------------------

* Better warnings message, should show proper origination

* Corrected ``dirty`` determination: repo with staged files is considered dirty until effective commit


2.3.2 (2019-01-28)
------------------

* Extract all relevant info from ``PKG-INFO`` (not just version)


2.3.1 (2019-01-04)
------------------

* Auto-fill ``bugtrack_url``


2.3.0 (2018-11-12)
------------------

* Added support for version determination from PKG-INFO


2.2.1 (2018-10-23)
------------------

* Added ``version --show-next``


2.2.0 (2018-10-19)
------------------

* Added ``{devcommit}`` versioning strategy token


2.1.2 (2018-09-19)
------------------

* Added ``--expand`` to command ``explain``

* Better handling of unicode in ``README``-s and ``setup.py``-s

* Fixed setupmeta's own download_url


2.0.6 (2018-09-11)
------------------

* Show how many requirements_ were abstracted/skipped (if any) in ``setup.py check``

* Warn if current version tag mention patch while versioning strategy doesn't


2.0.1 (2018-08-31)
------------------

* Make sure local tags match remote before pushing a new bumped version tag


2.0.0 (2018-08-10)
------------------

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


.. _requirements: https://github.com/zsimic/setupmeta/blob/master/docs/requirements.rst
