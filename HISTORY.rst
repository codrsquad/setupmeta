=======
History
=======

0.0.8 (2017-12-04)
------------------

* Inlined pipfile, removed old hacky toml/pipfile implementation

* Refactored as a proper package (now that the one-file mode is not needed anymore)

.. [[end long_description]]


0.0.4 (2017-12-03)
------------------

* Should work with any version of setuptools now

* Removed old way, no more "drop setupmeta.py next to your setup.py" mode

* Fixed a few bugs



0.0.3 (2017-12-03)
------------------

* Fixed bootstrap, so that ``PKG-INFO`` gets the right metadata (bootstrapping in 2 passes)

* setupmeta can now be used via ``setup_requires='setupmeta'``

* Allow to use portion of README via ``.. [[end long_description]]``

* Allow to use include other files in long description via something like ``.. [[include HISTORY.rst]]``


0.0.2 (2017-12-02)
------------------

* Fixed how ``keywords`` get parsed.

* Added ``test`` command


0.0.1 (2017-12-02)
------------------

* First release to PyPI.
