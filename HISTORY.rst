=======
History
=======

0.2.0 (2017-12-07)
------------------

* Taking short description from 1st line of README file


0.1.3 (2017-12-06)
------------------

* Look only at 1st paragraph of docstring for key/value definitions

* Auto-determine most common license, and their classifier string

* Accept description in project docstrings (not only setup.py)

* Refactored as a proper package (now that the one-file mode is not needed anymore)

.. [[end long_description]]


0.0.4 (2017-12-03)
------------------

* Should work with any version of setuptools now, via ``setup_requires='setupmeta'``

* Removed old way, no more "drop setupmeta.py next to your setup.py" mode

* Fixed bootstrap, so that ``PKG-INFO`` gets the right metadata (bootstrapping in 2 passes)

* Allow to use portion of README via ``.. [[end long_description]]``

* Allow to use include other files in long description via something like ``.. [[include HISTORY.rst]]``
