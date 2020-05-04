single: A package implemented by a single .py file
==================================================

This example shows:

* `name` is the only thing defined in `setup.py`

*  😊 (unicode in readme)

* Short description comes from this README

* `py_modules` is correctly populated due to existence of `single.py` module

* A couple of things are defined in ``single.py``'s docstring

* ``__version__`` is also defined in ``single.py``

* project layout is::

    |-- README.rst
    |-- setup.py
    |-- single.py           # Python module as single file, definitions are taken from here


* ``setup.py`` contents::

    from setuptools import setup


    setup(
        name='single',
        setup_requires=['setupmeta']
    )


* ``single.py`` contents::

    """
    This is a python package implemented by a single .py file

    license: MIT
    author: Someone someone@example.com
    """

    __version__ = '0.1.0'


* ``explain`` output::

              author: (auto-adjust ) Someone
                  \_: (single.py:5 ) Someone someone@example.com
        author_email: (auto-adjust ) someone@example.com
         description: (README.rst:1) A package implemented by a single .py file
                  \_: (single.py:2 ) This is a python package implemented by a single .py file
             license: (single.py:4 ) MIT
    long_description: (README.rst  ) 1600 chars: single: A package implemented by a single .py file ...
                name: (explicit    ) single
          py_modules: (auto-fill   ) ['single']
      setup_requires: (explicit    ) ['setupmeta']
             version: (single.py:8 ) 0.1.0
