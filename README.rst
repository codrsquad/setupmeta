Simplify your ``setup.py``
==========================

Writing a ``setup.py`` typically involves lots of boilerplate and copy-pasting from project to project.

This package aims to simplify that, here's what your setup.py could look like with setupmeta_::

    """
    Short description of the project
    """

    from setuptools import setup

    __version__ = '1.0.0'               # This can come from your __about__.py

    setup(
        name='myproject',
        setup_requires='setupmeta'      # This is where setupmeta comes in
    )

And that should be it - setupmeta_ will take it from there, extracting everything else from your project, following the typical conventions commonly used.

You can use the explain_ command to see what setupmeta deduced from your project, for the above it would look like so
(you can see which file, and which line each setting came from)::

    Definitions:
    ------------
         description: (setup.py:2 ) Short description of the project
    long_description: (README.rst ) Long description would be your inlined README.rst
                name: (setup.py:10) myproject
          py_modules: (auto-fill  ) ['myproject']
          test_suite: (auto-fill  ) tests
       tests_require: (Pipfile    ) ['coverage', 'flake8', 'pytest']
             version: (setup.py:7 ) 1.0.0

The above would be what you get with just those few lines in your ``setup.py``, plus a ``README.rst`` file, a ``tests/`` folder, and a pipfile_
(assumed here for auto-fill illustration purposes - you don't have to have those, they just get automatically picked up if you do)

See examples_ for more.


How it works?
=============

- Everything that you explicitly provide in your original ``setup.py`` -> ``setup()`` call is taken as-is (never changed), and internally labelled as ``explicit`` (see the explain_ command below).
  So if you don't like something that setupmeta deduces, you can always explicitly state it.

- ``name`` is auto-filled from your setup.py's ``__title__``, if there is one (sometimes having a constant is quite handy...)

- ``description`` will be the 1st line of the docstring of your ``setup.py``

- ``packages`` and ``package_dir`` is auto-filled accordingly if you have a ``<name>/__init__.py`` or ``src/<name>/__init__.py`` file

- ``py_modules`` is auto-filled if you have a ``<name>.py`` file

- ``version``, ``url``, ``download_url``, ``license``, ``keywords``, ``author``, ``contact``, ``maintainer``, and ``platforms`` will be auto-filled from:

    - Lines of the form ``__version__ = "1.0.0"`` in your modules (simple constants only, expressions are ignored - the modules are not imported but scanned using regexes)

    - Lines of the form ``version: 1.0.0`` in your docstring

    - Files are examined in this order (first find wins):

        - ``setup.py``

        - ``<package>.py`` (mccabe_ for example)

        - ``<package>/__about__.py`` (cryptography_, pipfile_ for example do this)

        - ``<package>/__version__.py`` (requests_ for example)

        - ``<package>/__init__.py`` (changes_, arrow_ for example)

        - ``src/`` is also examined (for those who like to have their packages under ``src``)

    - URLs can be simplified:

        - ``url`` may use ``{name}``, it will be expanded appropriately

        - if ``url`` points to your general github repo (like: https://github.com/zsimic), the ``name`` of your project is auto-appended to it

        - if ``download_url`` is a relative path, it is auto-filled by prefixing it with ``url``

        - ``download_url`` may use ``{name}`` and/or ``{version}``, those will be expanded appropriately

    - ``author``, ``maintainer`` and ``contact`` names and emails can be combined into one line (setupmeta will figure out the email part and auto-fill it properly)

        - i.e.: ``author: Bob D bob@d.com`` will yield the proper ``author`` and ``author_email`` settings

- ``long_description`` is auto-filled from your README file (looking for ``README.rst``, ``README.md``, then ``README*``, first one found wins).
  Special tokens can be used (notation aimed at them easily being `rst comments`_):

    - ``.. [[end long_description]]`` as end marker, so you don't have to use the entire file as long description

    - ``.. [[include <relative-path>]]`` if you want another file included as well (for example, people like to add ``HISTORY.txt`` as well)

    - these tokens must appear either at beginning/end of line, or be after/before at least one space character

- ``classifiers`` is auto-filled from file ``classifiers.txt`` (one classification per line, ignoring empty lines and python style comments)

- ``entry_points`` is auto-filled from file ``entry_points.ini`` (bonus: tools like PyCharm have a nice syntax highlighter for those)

- ``install_requires`` is auto-filled if you have a pipfile_ (or the old school ``requirements.txt`` or ``pinned.txt`` file)

- ``tests_require`` is auto-filled if you have a pipfile_ (or ``requirements-dev.txt`` file)

- ``test_suite`` is auto-filled to ``tests`` folder if you have one (no other places are examined, stick to the standard)

- ``py.test`` is automatically used for ``setup.py test`` if you have it in your pipfile_ (or reqs).

This should hopefully work nicely for the vast majority of python projects out there.
If you need advanced stuff, you can still leverage ``setupmeta`` for all the usual stuff above, and go explicit wherever needed.


Commands
========

``setupmeta`` also introduces a few commands to make your life easier (more to come in the future).


explain
-------

``python setup.py explain`` will show you what ``setupmeta`` found out about your project, what definitions came from where, example::

    ~/dev/setupmeta: python setup.py explain
    Definitions:
    ------------
              author: (auto-adjust    ) Zoran Simic
                  \_: (setupmeta.py:27) Zoran Simic zoran@simicweb.com
        author_email: (auto-adjust    ) zoran@simicweb.com
         classifiers: (classifiers.txt) 247 chars [Development Status :: 4 - Beta ...]
         description: (setup.py:2     ) Simplify your setup.py
            keywords: (setup.py:4     ) convenient, setup.py
             license: (setupmeta.py:25) MIT
    long_description: (README.rst     ) 7754 chars [Simplify your setup.py ======= ...]
                name: (explicit       ) setupmeta
          py_modules: (auto-fill      ) ['setupmeta']
         script_args: (explicit       ) ['explain']
         script_name: (explicit       ) setup.py
       tests_require: (Pipfile        ) ['coverage', 'flake8', 'mock', 'pytest']
                 url: (setupmeta.py:26) https://github.com/zsimic/setupmeta
             version: (setupmeta.py:24) 0.0.1

In the above output:

- The ``author`` key was seen in ``setupmeta.py`` line 27, and the value was name + email,
  that got "auto-adjusted" and filled in as ``author`` + ``author_email`` properly as shown.

- Note that the ``\_`` indication tries to convey the fact that ``author`` in this example had a value that came from 2 different sources,
  final value showing at top, while all the other values seen showing below with the ``\_`` indicator.

- ``classifiers`` came from file ``classifiers.txt``, ``description`` came from ``setup.py`` line 2, etc

- ``name`` was ``explicit`` (ie: explicitly given to the original ``setup()`` call in ``setup.py``)

- ``py_modules`` was auto-filled to ``['setupmeta']``

- Note that ``script_args`` and ``script_name`` are injected by setuptools
  (they appear as "explicit" from setupmeta's point of view - you get some insight as to what setuptools is doing here as well)


entrypoints
-----------

This will simply show you your ``entry_points/console_scripts``. I added it because pygradle_ requires it (if you use pygradle_, it'll come in handy...).


test
----


The ``test`` command is customized to run ``pytest``, if you have it as a test/dev dependency.
If you don't, then setupmeta falls back to the regulars setuptools implementation for the test command...

Note that **all** tests are ran via ``py.tests -vvv <test_suite>``, you can't customize that (no options supported).
Just use something like ``pipenv run py.test ...`` if you want to run a subset of tests, ``setup.py``'s CLI interface is wonky anyway.


upload
------

Upload was customized to use ``twine upload``, if you don't have twine_ installed, the ``upload`` command will fail (I hear the default one is not good, so not falling back to it...)


.. _setupmeta: https://github.com/zsimic/setupmeta

.. _examples: https://github.com/zsimic/setupmeta/tree/master/examples

.. _setuptools: https://github.com/pypa/setuptools

.. _twine: https://github.com/pypa/twine

.. _rst comments: http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#comments

.. _pipfile: https://github.com/pypa/pipfile

.. _requests: https://github.com/requests/requests/tree/master/requests

.. _cryptography: https://github.com/pyca/cryptography/tree/master/src/cryptography

.. _changes: https://github.com/michaeljoseph/changes/blob/master/changes/__init__.py

.. _arrow: https://github.com/crsmithdev/arrow/blob/master/arrow/__init__.py

.. _mccabe: https://github.com/PyCQA/mccabe/blob/master/mccabe.py

.. _pygradle: https://github.com/linkedin/pygradle/

----

.. [[include HISTORY.rst]]
.. [[end long_description]]


Motivation
==========

My motivation was to:

- stop having to boilerplate my setup.py's

- learn how to publish to pypi (and do it right)

- have a nice workflow for when I want to publish to pypi:

    - ``setup.py explain`` to see what's up at a glance

    - ``setup.py test`` to verify my stuff works from setup.py's point of view

    - ``setup.py upload`` to publish in one go

I noticed that most open-source projects out there do the same thing over and over, like:

- Read the entire contents of their README file and use it as ``long_description``
  (copy-pasting the few lines of code to read the contents of said file)

- Reading, grepping, sometimes importing a small ``__version__.py`` or ``__about__.py`` file to get values like ``__version__`` out of it,
  and then dutifully doing ``version=__version__`` or ``version=about['__version__']`` in their ``setup.py``

- All kinds of creative things to get the ``description``

- Very few ``setup.py`` specimens out there even have a docstring

- etc.

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


Roadmap
=======

- Support git-versioning, like ``setuptools_scm`` - but auto-apply tag on ``upload``
