=======
History
=======

0.4.1 (2017-12-18)
------------------

* Seeding support for ``versioning`` key in setup.py, setupmeta will allow for some simple git-tag based versioning


0.3.1 (2017-12-15)
------------------

* Removed support for Pipfile

* Testing with pypy as well, produce eggs for 2.7, 3.4, 3.5, 3.6

.. [[end long_description]]


0.2.8 (2017-12-09)
------------------

* Publish wheels as well

* Always listify ``keywords``

* Auto-publishing via travis

* Use 1st line of README file as short description if no docstrings are found


0.1.3 (2017-12-06)
------------------

* Look only at 1st paragraph of docstring for key/value definitions

* Auto-determine most common license, and their classifier string

* Accept description in project docstrings (not only setup.py)

* Refactored as a proper package (now that the one-file mode is not needed anymore)


0.0.4 (2017-12-03)
------------------

* Should work with any version of setuptools now, via ``setup_requires='setupmeta'``

* Removed old way, no more "drop setupmeta.py next to your setup.py" mode

* Fixed bootstrap, so that ``PKG-INFO`` gets the right metadata (bootstrapping in 2 passes)

* Allow to use portion of README via ``.. [[end long_description]]``

* Allow to use include other files in long description via something like ``.. [[include HISTORY.rst]]``
