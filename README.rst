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
         classifiers: (classifiers.txt) 276 chars [[u'Development Status :: 4 - Beta', ...]
         description: (setup.py:2     ) Stop copy-paste technology in setup.py
            keywords: (setup.py:4     ) anti copy-paste, convenient, setup.py
             license: (setupmeta.py:25) Apache 2.0
    long_description: (README.rst     ) 2267 chars [Stop copy-pasting stuff in ``setup.py`` ...]
                name: (explicit       ) setupmeta
          py_modules: (auto-fill      ) ['setupmeta']
         script_args: (explicit       ) ['explain']
         script_name: (explicit       ) setup.py
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

``setupmeta`` finds all the info that's usually provided to ``setuptools.setup()`` throughout your project and auto-fills it for you.

It does so by following these rules (which come from observing what many open-source projects usually do):

- Everything that you explicitly provided in the ``setup()`` call is taken as-is (never changed), and internally labelled as ``explicit``.

- It doesn't try to guess the ``name`` of your project, so you should at the minimum state the ``name`` of your project in ``setup.py``.
  Everything else can be deduced from other parts of your project.

- ``packages`` and ``package_dir`` is auto-filled accordingly if you have a ``<name>/__init__.py`` or ``src/<name>/__init__.py`` file

- ``py_modules`` is auto-filled if you have a ``<name>.py`` file

- ``description`` is auto-filled with the 1st line of your ``setup.py`` docstring

- ``long_description`` is auto-filled from your README file (looking for ``README.rst``, ``README.md``, then ``README*``, first one found wins)

- All the other usual keys are looked up (and used if present) in the following files:
    - ``<package>/__about__.py`` (cryptography_ for example does this)
    - ``<package>/__version__.py`` (requests_ for example)
    - ``<package>/__init__.py`` (changes_, arrow_ for example)
    - ``<package>.py`` (mccabe_ for example)
    - ``setup.py``

- ``author``, ``maintainer`` and ``contact`` names and emails can be combined into one line (setupmeta will figure out the email part and auto-fill it properly)

- Only simple key/value definitions are considered for auto-fill
  (this stems from the observation of many open-source projects (this is how they tend to do it anyway):

    - of the form ``__<key>__ = "<some-constant>"`` in python modules

    - of the form ``<key>: <value>`` in docstrings


Here's an example providing ``autor=..., author_email=..., url=..., version=...`` in say ``__init__.py``::

    """
    This is my cool module

    author: Zoran Simic zoran@simicweb.com
    """

    __url__ = "http://my-url"   # Comments are OK
    __version__ = "1.0.0"
    __foo__ = "foo" + "bar"
    __bar___ = """ some multi-line """

Note that:

- ``author`` is defined in the docstring (it could be also done via ``__author__ = ...``, would have the same outcome)

- ``__foo__`` is not considered as a simple key/value (it's not a pure constant), and would not be looked at

- ``__bar__`` is not considered as a simple key/value (not parsing multi-lines), and would not be looked at


Installation
------------

Grab the ``setupmeta.py`` script in your project folder, you can do so using one of the following ways::

    wget https://raw.githubusercontent.com/zsimic/setupmeta/setupmeta.py

Or using pip::

    pip install setupmeta
    setupmeta.py .

If you already have setupmeta in another project of yours, you can also do::

    setupmeta.py ~/path/to/my/other/project

If you already have the script in some project, you can use it to "seed" other projects like so::

    ~/my-project/setupmeta.py ~/my-other-project/

This will grab the latest version of the script and put it ``~/my-other-project/``, it's almost equivalent to (and you could do this also BTW)::

    cp ~/my-project/setupmeta.py ~/my-other-project/setupmeta.py

The script can auto-upgrade itself, once you have a copy, you can get the latest version via::

    ./setupmeta.py .


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

Due to setuptools limitations, I had to make this work by asking users to put a copy of ``setupmeta.py`` in their projects.
In the future, I plan to make setupmeta be consumed via ``setup_requires=['setupmeta']`` instead of this.

I have a working implementation draft with ``setup_requires=['setupmeta']``,
but it can only work with setuptools 36.7+ and in particular this `setuptools commit`_

When setuptools 36.7+ becomes commonplace, we'll be able to:

- Delete those ``setupmeta.py`` in-project copies

- Use ``setup_requires=['setupmeta']`` in the original ``setup()`` call instead


.. _setuptools commit: https://github.com/pypa/setuptools/commit/bb71fd1bed9f5e5e239ef99be82ed57e9f9b1dda#diff-6b59155d3acbddf6010c0f20482d4eea

.. _requests: https://github.com/requests/requests/tree/master/requests

.. _pipenv setup.py: https://github.com/kennethreitz/pipenv/blob/master/setup.py

.. _cryptography: https://github.com/pyca/cryptography/tree/master/src/cryptography

.. _changes: https://github.com/michaeljoseph/changes/blob/master/changes/__init__.py

.. _arrow: https://github.com/crsmithdev/arrow/blob/master/arrow/__init__.py

.. _mccabe: https://github.com/PyCQA/mccabe/blob/master/mccabe.py
