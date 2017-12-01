Stop copy-pasting stuff in ``setup.py``
=======================================

This project aims at disrupting the proliferation of copy-paste tech that's currently affecting all ``setup.py`` writers in this world.


Get started
===========

- Grab ``setupmeta.py`` next to your ``setup.py`` and check it in (it self-installs and self-upgrades as you'll see below).

- ``from setupmeta import setup``, and voila: most of the things you had to have in ``setup.py`` can now go away and be auto-filled.
  Your ``setup.py`` can now be as simple as::

    """
    Short description of my project
    """
    from setupmeta import setup
    setup(name='myproject')

- See what info was gathered by setupmeta, and from where::

    ~/dev/setupmeta: python setup.py explain
    Definitions:
    ------------
              author: (auto-adjust    ) Zoran Simic
                  \_: (setupmeta.py:27) Zoran Simic zoran@simicweb.com
        author_email: (auto-adjust    ) zoran@simicweb.com
         classifiers: (classifiers.txt) 247 chars [Development Status :: 4 - Beta ...]
         description: (setup.py:2     ) Stop copy-paste technology in setup.py
            keywords: (setup.py:4     ) anti copy-paste, convenient, setup.py
             license: (setupmeta.py:25) Apache 2.0
    long_description: (README.rst     ) 7754 chars [Stop copy-pasting stuff in ``setup.py`` ...]
                name: (explicit       ) setupmeta
          py_modules: (auto-fill      ) ['setupmeta']
         script_args: (explicit       ) ['explain']
         script_name: (explicit       ) setup.py
       tests_require: (Pipfile        ) ['coverage', 'flake8', 'mock', 'pytest', 'pytest-runner']
                 url: (setupmeta.py:26) https://github.com/zsimic/setupmeta
             version: (setupmeta.py:24) 0.0.1

In the above output:

- We ran ``python setup.py explain`` - "explain" is a command provided by setupmeta (see Commands_), it's there to help you see what definitions came from where

- The ``author`` key was seen in ``setupmeta.py`` line 27, and the value was name + email,
  that got "auto-adjusted" and filled in as ``author`` + ``author_email`` properly as shown.

- Note that the ``\_`` indication tries to convey the fact that ``author`` in this example had a value that came from 2 different sources,
  final value showing at top, while all the other values seen showing below with the ``\_`` indicator.

- ``classifiers`` came from file ``classifiers.txt``, ``description`` came from ``setup.py`` line 2, etc

- ``name`` was ``explicit`` (ie: explicitly given to the original ``setup()`` call in ``setup.py``)

- ``py_modules`` was auto-filled to ``['setupmeta']``

- Note that ``script_args`` and ``script_name`` are injected by setuptools
  (they appear as "explicit" from setupmeta's point of view - you get some insight as to what setuptools is doing here as well)


How it works?
=============

  [It has to live alongside your ``setup.py`` in order for the ``from setupmeta import setup`` call to work.
  I have plans to make this better (see Roadmap_ below), but for now this is the only way unfortunately]

``setupmeta`` tries to save you some copy-pasting activity in ``setup.py`` by digging information about your project, from your project.

It finds all the info that's usually provided to ``setuptools.setup()`` throughout your project and auto-fills it for you.

See the `quick reference`_ page.

I noticed that most open-source projects out there do the same thing over and over, like:

- Read the entire contents of their README file and use it as ``long_description``
  (copy-pasting the few lines of code to read the contents of said file)

- Reading, grepping, sometimes importing a small ``__version__.py`` or ``__about__.py`` file to get values like ``__version__`` out of it,
  and then dutifully doing ``version=__version__`` or ``version=about['__version__']`` in their ``setup.py``

- All kinds of creative things to get the ``description``

- Very few ``setup.py`` specimens out there even have a docstring

- Etc.

I didn't want to keep doing this anymore myself, so I decided to try and do something about it with this project.

With setupmeta, you can achieve a short and sweet setup.py by proceeding like so:

- Have a docstring in your ``setup.py``, 1st line will be your ``description``

- Add a few lines in that docstring of the form ``key: value`` for this that you don't want to state in your code itself, some examples for that could be::

    """
    Do things concisely

    licence: MIT
    keywords: cool, stuff
    author: Zoran Simic zoran@simicweb.com
    """

- In your ``__init__.py`` (or a dedicated ``__version__.py``, or ``__about__.py`` if you prefer), state things you would like to be importable from your code, example::

    __version__ = "1.0.0"
    __url__ = "https://github.com/me/myproject"

- Your README will end up on pypi automatically as ``long_description``

- If you are using pipenv_, your ``install_requires`` and ``tests_require`` will be auto-filled from your ``Pipfile``

- If you want classifiers, put them in a file ``classifiers.txt``

- If you have entry_points, you can state them in a file ``entry_points.ini`` (bonus: tools like PyCharm have a nice syntax highlighter for those)


Installation
============

Grab the ``setupmeta.py`` script in your project folder, you can do so using one of the following ways::

    wget https://raw.githubusercontent.com/zsimic/setupmeta/setupmeta.py

Or using pip::

    pip install setupmeta
    setupmeta.py .

If you already have the script in some project, you can use it to "seed" another project like so::

    ./setupmeta.py ~/my/other/project/


This will grab the latest version of the script and put it in ``~/my/other/project/``, it's almost equivalent to
(and you could do this also BTW, the only difference from above is that no check for updates is performed)::

    cp ./setupmeta.py ~/my/other/project/setupmeta.py

The script can auto-upgrade itself, once you have a copy, you can get the latest version by running this (default target is current folder)::

    ./setupmeta.py


Commands
========

Only 2 commands for now, more to come in the future.

explain
-------

Use it to double-check on what ``setupmeta`` is doing, where it finds the info it auto-fills.
The command only outputs info, does no changes, can be ran any time.

upload
------

It's a draft, taken from `pipenv setup.py`_

The idea is that this will be a convenient way to upload/publish your project to pypi,
with all sorts of validation etc.


Roadmap
=======

Install via ``setup_requires`` instead of local copy of ``setupmeta.py``
------------------------------------------------------------------------

Due to setuptools limitations, I had to make this work by asking users to put a copy of ``setupmeta.py`` in their projects.
In the future, I plan to make setupmeta be consumed via ``setup_requires=['setupmeta']`` instead of this.

I have a working implementation draft with ``setup_requires=['setupmeta']``,
but it can only work with setuptools 36.7+ and in particular this `setuptools commit`_

When setuptools 36.7+ becomes commonplace, we'll be able to:

- Delete those ``setupmeta.py`` in-project copies

- Use ``setup_requires=['setupmeta']`` in the original ``setup()`` call instead


More commands
-------------

Add more convenience commands such as ``upload`` and a ``test`` that works for most popular cases



.. _setuptools commit: https://github.com/pypa/setuptools/commit/bb71fd1bed9f5e5e239ef99be82ed57e9f9b1dda#diff-6b59155d3acbddf6010c0f20482d4eea

.. _pipenv: https://github.com/kennethreitz/pipenv
.. _pipenv setup.py: https://github.com/kennethreitz/pipenv/blob/master/setup.py

.. _quick reference: ./REFERENCE.rst
