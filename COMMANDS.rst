Commands
========

``setupmeta`` also introduces a few commands to make your life easier (more to come in the future).


explain
=======

``python setup.py explain`` will show you what ``setupmeta`` found out about your project, what definitions came from where.

For example, this is what setupmeta says about itself (it's self-using)::

    ~/dev/setupmeta: python setup.py explain

              author: (auto-adjust            ) Zoran Simic
                  \_: (setupmeta/__init__.py:6) Zoran Simic zoran@simicweb.com
        author_email: (auto-adjust            ) zoran@simicweb.com
         classifiers: (classifiers.txt        ) 22 items: ['Development Status :: 4 - Beta', 'Intended Audience :: Developers'...
         description: (setupmeta/__init__.py:2) Simplify your setup.py
        download_url: (auto-fill              ) https://github.com/zsimic/setupmeta/archive/0.8.0.post1+g816252c.tar.gz
                  \_: (setupmeta/__init__.py:5) archive/{version}.tar.gz
        entry_points: (explicit               ) 260 chars: [distutils.commands] bump = setupmeta.commands:BumpCommand explain ...
            keywords: (setup.py:4             ) ['convenient', 'setup.py']
             license: (auto-fill              ) MIT
    long_description: (README.rst             ) 8933 chars: Simplify your setup.py ======================  .. image:: https://...
                name: (setup.py:15            ) setupmeta
            packages: (auto-fill              ) ['setupmeta']
      setup_requires: (explicit               ) ['setupmeta']
       tests_require: (tests/requirements.txt ) ['mock', 'pytest-cov']
              title*: (setup.py:15            ) setupmeta
                 url: (setupmeta/__init__.py:4) https://github.com/zsimic/setupmeta
             version: (git                    ) 0.8.0.post1+g816252c
          versioning: (explicit               ) tag
            zip_safe: (explicit               ) True

In the above output:

* All the ``explicit`` mentions mean that associated values were seen mentioned explicitly in setup.py, and were left untouched

* The ``author`` key was seen in ``setupmeta/__init__.py`` line 6, and the value was name + email,
  that got "auto-adjusted" and filled-in as ``author`` + ``author_email`` properly as shown.

* Note that the ``\_`` indication tries to convey the fact that ``author`` in this example had a value that came from 2 different sources,
  final value showing at top, while all the other values seen showing below with the ``\_`` indicator.

* ``classifiers`` came from file ``classifiers.txt``

* ``description`` came from ``setup.py`` line 2

* ``download_url`` was defined in ``setupmeta/__init__.py`` line 5, since it was mentioning ``{version}`` (and was a relative path), it got auto-expanded and filled in properly

* ``entry_points`` were explicitly stated (in project's setup.py)

* ``long_description`` came from ``README.rst``

* ``name`` came from line 15 of setup.py, note that ``title`` also came from that line - this simply means the constant ``__title__`` was used as ``name``

* ``tests_require`` was deduced from ``tests/requirements.txt``

* Note that ``title*`` is shown with an asterisk, the asterisk means that setupmeta sees the value and can use it, but doesn't transfer it to setuptools

* ``packages`` was auto-filled to ``['setupmeta']``

* ``version`` was determined from git tag (due to ``versioning='tag'`` in setup.py), in this case ``0.8.0.post1+g816252c`` means:

    * latest tag was 0.8.0

    * there was 1 commit since that tag (``.post1`` means 1 change since tag, ".post" denotes this would be a "post-release" version, and should play nicely with PEP-440_)

    * the ``+g816252c`` suffix means that the checkout wasn't clean when ``explain`` command was ran, local checkout was dirty at short git commit id "816252c"


bump
====

If you're using the ``versioning=...`` feature, you can then use the ``python setup.py bump`` command to bump your git-tag driven version. See ``--help`` for more info.
Typical usage::

    python setup.py bump --help             # What were the options?
    python setup.py bump --minor            # Check everything looks as expected
    python setup.py bump --minor --commit   # Effectively bump


entrypoints
===========

This will simply show you your ``entry_points/console_scripts``. I added it because pygradle_ requires it (if you use pygradle_, it'll come in handy...).



.. _PEP-440: https://www.python.org/dev/peps/pep-0440/

.. _pygradle: https://github.com/linkedin/pygradle/

