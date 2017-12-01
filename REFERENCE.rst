setupmeta quick reference
=========================

``setupmeta`` finds all the info that's usually provided to ``setuptools.setup()`` throughout your project and auto-fills it for you.

Use ``python setup.py explain`` to get a recap for your project at any time.

This is the exhaustive list of what it looks for (which come from observing what many open-source projects usually do):

- Everything that you explicitly provided in the ``setup()`` call is taken as-is (never changed), and internally labelled as ``explicit``.
  So if you don't like something that setupmeta deduces, you can always explicitly state it.

- You must provide ``name`` in your ``setup()`` call, ``name`` will NOT be guessed.
  Everything else can be deduced from other parts of your project.

- ``packages`` and ``package_dir`` is auto-filled accordingly if you have a ``<name>/__init__.py`` or ``src/<name>/__init__.py`` file

- ``py_modules`` is auto-filled if you have a ``<name>.py`` file

- ``description`` is auto-filled with the 1st line of your ``setup.py`` docstring

- ``long_description`` is auto-filled from your README file (looking for ``README.rst``, ``README.md``, then ``README*``, first one found wins)

- ``classifiers`` is auto-filled from file ``classifiers.txt``

- ``entry_points`` is auto-filled from file ``entry_points.ini`` (bonus: tools like PyCharm have a nice syntax highlighter for those)

- All the other usual keys are looked up (and used if present) in the following files (in this order, first find wins):

    - ``<package>/__about__.py`` (cryptography_ for example does this)

    - ``<package>/__version__.py`` (requests_ for example)

    - ``<package>/__init__.py`` (changes_, arrow_ for example)

    - ``<package>.py`` (mccabe_ for example)

    - ``setup.py``

- Possibly simplified urls:

    - if ``url`` points to your general github repo (like: https://github.com/zsimic), the ``name`` of your project is auto-appended to it

    - if ``download_url`` is a relative path, it is auto-filled by prefixing it with ``url``

    - ``download_url`` may use ``{name}`` and/or ``{version}``, those will be expanded appropriately

- ``author``, ``maintainer`` and ``contact`` names and emails can be combined into one line (setupmeta will figure out the email part and auto-fill it properly)

- Only simple key/value definitions are considered for auto-fill
  (the modules are not imported, their content is scanned using regexes):

    - of the form ``__<key>__ = "<some-constant>"`` in python modules

    - of the form ``<key>: <value>`` in docstrings


Example
=======

Here's an example providing ``autor=..., author_email=..., url=..., version=...`` in say ``__init__.py``::

    """
    This is my cool module

    author: Zoran Simic zoran@simicweb.com
    """

    __url__ = "http://my-url"   # Comments are OK
    __author__ = "Foo Bar"
    __version__ = "1.0.0"
    __foo__ = "foo" + "bar"
    __bar___ = """ some multi-line """

Note that:

- ``author`` is defined twice: in the docstring, and as ``__author__``, the first definition found wins (here: docstring)

- ``__foo__`` is not considered as a simple key/value (it's not a pure constant), and would not be looked at

- ``__bar__`` is not considered as a simple key/value (not parsing multi-lines), and would not be looked at
