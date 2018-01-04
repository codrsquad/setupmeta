=======
History
=======

1.0.5 (2017-01-03)
-------------------

* Added pre-defined versioning strategy ``build-id``

* Test coverage at 100%, added debug info via env var ``SETUPMETA_DEBUG=1``


0.8.1 (2017-12-31)
-------------------

* Versioning is more easily customizable, using post-release marker by default (instead of beta)


0.7.11 (2017-12-27)
-------------------

* Better defined versioning strategies


0.6.3 (2017-12-21)
------------------

* Fully using setupmeta's own versioning scheme (no more "backup" version stated in ``__init__.py``)

* Versioning compatible with PEP-440


0.5.2 (2017-12-20)
------------------

* Using ``versioning`` on setupmeta, which can now bump itself


0.4.8 (2017-12-18)
------------------

* Added support for ``versioning`` key in setup.py, setupmeta can now compute version from git tags, and bump that version


0.3.1 (2017-12-15)
------------------

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
