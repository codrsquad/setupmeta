=======
History
=======

1.5.0 (2018-06-08)
------------------

* Don't pass redundant ``bump`` cli arg to bump hook


1.4.5 (2017-04-17)
------------------

* Accept git version tags of the form ``M.m.p`` (don't require git tags to start with a ``v`` prefix)

* Support pip 10.0

* Use ``g0000000`` as commit-id instead of ``initial`` when no commit took place yet

* Hook earlier, into ``parse_command_line`` instead of ``get_option_dict`` in order for ``setup.py --version`` (and similar) to work

* Added pre-defined versioning strategy ``post``

* Renamed pre-defined versioning strategies, to better convey their intent: ``changes`` -> ``distance`` and ``tag`` -> ``post``


1.3.6 (2017-01-14)
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
