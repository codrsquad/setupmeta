Support for versioning
======================

setupmeta can use git tags to automatically **version** and **bump** the version of your project.

The functionality is optional and has to be explicitly enabled, note that:

* SCM tags are used for versioning

* only git is supported currently
  (contributions for other SCMs welcome and should be easy, see `Scm class`_)

* It can be a drop-in replacement for setuptools_scm_

* 5 strategies are pre-configured: post_, dev_, distance_, devcommit_ and build-id_,
  they yield versions that play well with PEP-440_ (while remaining very simple).

* See Advanced_ section for more info

In order to use setupmeta as a bridge to your git tags as versions,
activate the feature by specifying one of the strategies in your ``setup.py`` like so::

    setup(
        versioning="post",
        ...
    )

You can use then ``python setup.py version --bump`` to bump major/minor/patch
(no need to assign tags manually).

Note that if you still explicitly mention a ``__version__ = "..."``` in your ``__init__.py``
or ``__about__.py`` etc, setupmeta will find it and also bump it accordingly.
This is done for convenience only, you don't need ``__version__`` anywhere if you use
setupmeta versioning.


How does it work?
=================

**Note**: ``setupmeta``'s versioning is based on (by default)::

    git describe --dirty --tags --long --match *.* --first-parent

you will need **git version >= 1.8.4** if you wish to use ``setupmeta``'s versioning capabilities.

You can modify the above command via environment variable ``SETUPMETA_GIT_DESCRIBE_COMMAND``
(give full git command if you do).

----

setupmeta declares a keyword to setuptools called ``versioning``, if you specify that keyword
(and it is valid), setupmeta versioning will be enabled.

You can specify ``versioning``:

* explicitly in your ``setup()`` call

* implicitly in your ``__init__.py``, ``__about__.py``, docstrings etc
  (setupmeta will show where ``versioning`` was defined, like any other value it handles)

Tag-based versioning will take precedence on any other ``version`` specification you may have,
and ``setup.py version --bump`` will modify those over values for ``version``
that you have (if any) accordingly.

For example, if you have this:

* ``setup(versioning="post")`` in your ``setup.py``

* ``__version__ = "1.0.0"`` in your ``__init__.py`` line 7

* ``git describe`` yields ``v1.0.0-2-g123``
  (ie: latest tag is "v1.0.0", there are 2 commits since that tag, and current commit id is "123")

Now, running ``setup.py explain`` will show you something like this::

    version: (git          ) 1.0.0.post2+dirty
         \_: (__init__.py:7) 1.0.0

Which means that determined version of your project (from git tag) is ``1.0.0.post2+dirty``,
while ``__init_.py`` line 7 states it is "1.0.0".

If you commit your changes, your checkout won't be dirty anymore,
and the number of commits since latest tag will be 3, so ``setup.py explain`` will now show::

    version: (git          ) 1.0.0.post3
         \_: (__init__.py:7) 1.0.0

Ie:

* deduced version is 1.0.0, with 3 commits since latest tag

* checkout is clean, so the "extra" part is not shown (by default)

* ``__init__.py`` being static, it does not reflect this yet
  (but will if/when you ``setup.py version --bump``)

* note that this versioning scheme should play well with PEP-440_

If you now run ``setup.py version --bump patch --commit``, the following would happen:

* your ``__init__.py`` line 7 is modified to state ``__version__ = "1.0.1"``,
  and committed with description ``"Version 1.0.1"``

* tag ``v1.0.1`` is applied at that new commit

* now ``setup.py explain`` says::

    version: (git          ) 1.0.1
         \_: (__init__.py:7) 1.0.1

Note that you do NOT need any ``__version__ = ...`` stated anywhere, we're showing this only
here for illustration purposes. In general, you should simply use ``versioning="post"``
(or any other format you like).

You could leverage this ``__version__`` possibility if you have specific use case for that
(like: you'd like to show which version your code is at without using something like
``import pkg_resources``)


Preconfigured formats
=====================

post
----

This is well suited if you don't plan to publish often, and have a tag for each release.

``post`` corresponds to this format: ``branch(main,master):{major}.{minor}.{patch}{post}+{dirty}``

State this in your ``setup.py``::

    setup(
        versioning="post",
        ...
    )

Now, every time you commit a change, setupmeta will use the number of commits since last git
tag to determine the ``post`` part of your version.


Example:

=======  ======  =================  ==============================================================
Commit   Tag     Version            Note (command ran to add tag)
=======  ======  =================  ==============================================================
no .git          0.0.0              Version defaults to 0.0.0 (when no tag yet)
none             0.0.0.dirty        No commit yet (but ``git init`` was ran)
g1               0.0.0.post1        Initial commit
g1               0.0.0.post1+dirty  Same as above, only checkout was not clean anymore
g2               0.0.0.post2
g3               0.0.0.post3
g4       v0.1.0  0.1.0              ``version --bump minor --commit``
g5               0.1.0.post1        (1 commit since tag)
g6               0.1.0.post2
g7       v0.1.1  0.1.1              ``version --bump patch --commit``
g8               0.1.1.post1
g9       v1.0.0  1.0.0              ``version --bump major --commit``
g10              1.0.0.post1
=======  ======  =================  ==============================================================

* Without any tag, version defaults to ``0.0.0``

* First tag here is ``v0.1.0``, ``git describe`` will yield ``v0.1.0``
  (no commits since last tag), and setupmeta will consider version to be ``0.1.0`` (tag as-is)

* A commit occurs and doesn't add a git tag, version for that commit will be ``0.1.0.post1``
  (tag 0.1.0 with 1 change since tag)

* A 2nd commit doesn't add a git tag, version for that commit will be ``0.1.0.post2`` etc

* Dirty checkouts will get a version of the form ``0.1.0.post2+dirty``

* Use ``python setup.py version --bump [major|minor|patch]`` whenever you want to bump major,
  minor or patch revision (this will assign a git tag accordingly)

  * ``python setup.py version --bump patch --commit`` -> tag "v0.1.1" is added,
    version is now ``0.1.1``

  * Next commit after that will be version ``0.1.1.post1`` etc


dev
---

Similar to post_, with the following differences:

* ``.dev`` prefix is used instead of ``.post``, this makes untagged versions considered
  pre-release (have to use ``pip install --pre`` to get them)

* Right-most bumpable component (typically **patch**) is assumed to be the next one
  that is going to be bumped... (this just means that if your current version is ``0.8.1``,
  you would get a ``0.8.2.dev1`` etc; even though you may be planning your next tag to be
  ``0.9.0``, and not ``0.8.2``)

Example:

=======  ======  ================  ===============================================================
Commit   Tag     Version           Note (command ran to add tag)
=======  ======  ================  ===============================================================
no .git          0.0.0.dev0        Version defaults to 0.0.0 (when no tag yet)
none             0.0.0.dev0+dirty  No commit yet (but ``git init`` was ran)
g1               0.0.0.dev1        Initial commit
g1               0.0.0.dev1+dirty  Same as above, only checkout was not clean anymore
g2               0.0.0.dev2
g3               0.0.0.dev3
g4       v0.1.0  0.1.0             ``version --bump minor --commit``
g5               0.1.1.dev1        (1 commit since tag)
g6               0.1.1.dev2
g7       v0.1.1  0.1.1             ``version --bump patch --commit``
g8               0.1.2.dev1
g9       v1.0.0  1.0.0             ``version --bump major --commit``
g10              1.0.0.dev1
=======  ======  ================  ===============================================================

devcommit
---------

Same as dev_, with commit id added in ``local`` part when not exactly on a version tag.

Example:

=======  ======  ===================  ============================================================
Commit   Tag     Version              Note (command ran to add tag)
=======  ======  ===================  ============================================================
g1               0.0.0.dev1+g1        Initial commit
g1               0.0.0.dev1+g1.dirty  Same as above, only checkout was not clean anymore
g2               0.0.0.dev2+g2
g3               0.0.0.dev3+g3
g4       v0.1.0  0.1.0                ``version --bump minor --commit``
g5               0.1.1.dev1+g5        (1 commit since tag)
g6               0.1.1.dev2+g6
g7       v0.1.1  0.1.1                ``version --bump patch --commit``
g8               0.1.2.dev1+g7
g9       v1.0.0  1.0.0                ``version --bump major --commit``
g10              1.0.0.dev1+g10
=======  ======  ===================  ============================================================


distance
--------

This is well suited if you want to publish a new version at every commit (but don't want to keep
bumping version in code for every commit).

``distance`` corresponds to this format: ``branch(main,master):{major}.{minor}.{distance}{dirty}``

State this in your ``setup.py``::

    setup(
        versioning="distance",
        ...
    )


Now, every time you commit a change, setupmeta will use the number of commits since last git tag
to determine the 'patch' part of your version.


Example:

=======  ======  ================  ===============================================================
Commit   Tag     Version           Note (command ran to add tag)
=======  ======  ================  ===============================================================
no .git          0.0.0             Version defaults to 0.0 (when no tag yet)
none             0.0.0+dirty       No commit yet (but ``git init`` was ran)
g1               0.0.1             Initial commit, 0.0.1 means default v0.0 + 1 change
g1               0.0.1+dirty       Same as above, only checkout was not clean anymore
g2               0.0.2
g3               0.0.3
g4       v0.1.0  0.1.0             ``setup.py version --bump minor --commit``
g5               0.1.1             (1 commit since tag)
g6               0.1.2
g7               0.1.3
g8       v0.2.0  0.2.0             ``setup.py version --bump minor --commit``
                                   (note: can't bump "patch part" with this format)
g9               0.2.1
g10      v1.0.0  1.0.0             ``setup.py version --bump major --commit``
g11              1.0.1
=======  ======  ================  ===============================================================

* Without any tag, version defaults to ``0.0.*``

* First tag here is ``v0.1``, ``git describe`` will yield ``v0.1.0`` (no commits since last tag),
  and setupmeta will consider version to be ``0.1.0`` (tag 0.1 with 0 commits)

* A commit occurs and doesn't add a git tag, version for that commit will be ``0.1.1``
  (tag 0.1 with 1 change since tag)

* A 2nd commit occurs and doesn't add a git tag, version for that commit will be ``0.1.2`` etc

* Dirty checkouts will get a version of the form ``0.1.2+dirty``

* Use ``python setup.py version --bump [major|minor]`` whenever you want to bump major
  or minor version (this will assign a git tag accordingly)

  * ``python setup.py version --bump minor --commit`` -> tag "v0.2" is added,
    version is now ``0.2.0``

  * Next commit after that will be version ``0.2.1`` etc


build-id
--------

This is similar to distance_ (described above), so well suited if you want to publish a new
version at every commit, but also want maximum info in the version identifier.

``build-id`` corresponds to this format:
``branch(main,master):{major}.{minor}.{distance}+h{$*BUILD_ID:local}.{commitid}{dirty}``

State this in your ``setup.py``::

    setup(
        versioning="build-id",
        ...
    )


Example:

=======  ======  ===========================  ====================================================
Commit   Tag     Version                      Note (command ran to add tag)
=======  ======  ===========================  ====================================================
no .git          0.0.0+hlocal.g0000000        Version defaults to 0.0 (when no tag yet)
none             0.0.0+hlocal.g0000000.dirty  No commit yet (but ``git init`` was ran)
g1               0.0.1+hlocal.g1              Initial commit, built locally
                                              (``$BUILD_ID`` not defined), checkout was clean
g1               0.0.1+hlocal.g1.dirty        Same as above, only checkout was not clean anymore
g1               0.0.1+h123.g1                ``$BUILD_ID`` was "123"
                                              (so presumably built on a CI server)
g2               0.0.2+h124.g2
g3               0.0.3+h125.g3
g4       v0.1.0  0.1.0+hlocal.g4              ``version --bump minor --commit``, clean,
                                              built locally
g5               0.1.1+h130.g3                (1 commit since tag)
g6               0.1.2+h140.g3
g7       v0.2.0  0.2.0+h150.g3                ``version --bump minor --commit``
                                              (note: can't bump "patch" with this format)
g8               0.2.1+h160.g3
g9       v1.0.0  1.0.0+h200.g3                ``version --bump major --commit``
g10              1.0.1+h300.g3
=======  ======  ===========================  ====================================================

* Similar to distance_, except that the ``extra`` part is always shown and will reflect whether
  build took locally or on a CI server (which will define an env var ending with ``BUILD_ID``)


Advanced
========

``versioning`` can be customized beyond the above pre-defined strategies described above,
it can be passed as a **string** describing the version format,
or a **dict** for even more customization:

* a **string** can be of the form:

  * a version format specified of the form ``branch(<branches>):<main>+<extra>``

  * ``branch(<branches>):`` is optional, and you would use this full form only if you wanted
    version bumps to be possible on branches other than ``main`` or ``master``,
    if you want bumps to be possible on both ``prod`` and ``test`` branches for example,
    you would use ``branch(prod,test):...``

  * See Formatting_ below to see what's usable for ``<main>`` and ``<extra>``

  * the ``<main>`` part (before the ``"+"`` character) specifies the format of the
    "main version" part (when checkout is clean)

  * the ``<extra>`` part (after the ``"+"`` character) indicates the ``local`` part of
    your version, as per PEP-440_

* a **dict** with the following keys:

  * ``main``: a **string** (see Formatting_) or callable
    (if callable given, **version --bump** functionality becomes unusable)

  * ``extra``: a **string** (see Formatting_) or callable (custom function yielding
    a string from a given ``Version``, see `Scm class`_)

  * ``branches``: list of branch names (or csv) where to allow **bump**


This is what ``versioning="post"`` is a shortcut for::

    setup(
        versioning={
            "main": "{major}.{minor}.{patch}{post}",
            "extra": "{dirty}",
            "branches": ["main"],
        },
        ...
    )


Formatting
----------

The following can be used as format specifiers:

* ``{major}``: Major part of version

* ``{minor}``: Minor part of version

* ``{patch}``: Patch part of version

* ``{distance}``: Number of commits since last version tag from current commit
  (0 if current commit is tagged)

* ``{post}``: Designates a "post" release, empty when current commit
  is version-tagged, otherwise ``.postN`` (where ``"N"`` is ``{distance}``)

* ``{dev}``: Designates a "dev" release, empty when current commit is
  version-tagged, otherwise ``[+1].devN`` (where ``"N"`` is ``{distance}``, a ``[+1]`` is
  the next revision of the right-most bumpable, usually ``patch``).
  Example: ``1.2.dev3``.

* ``{devcommit}``: Same as ``{dev}``, with commit id added in ``local`` version part
  when not exactly on version tag.
  Example: ``1.2.dev3+g12345``.

* ``{commitid}``: short string identifying commit, like ``g3bf9221``

* ``{dirty}``: Expands to ``.dirty`` when checkout is dirty (has pending changes),
  empty string otherwise

* Convenience notations: the following shortcuts can be used for the local part of the
  version:

  * ``+devcommit``: Use the stated strategy, but add ``{devcommit}`` to the local part

  * ``+build-id``: Use the stated strategy, but add the same info from build-id_ strategy
      to the local part

  * Example: ``dev+devcommit``, or ``post+build-id`` etc


* ``foo``: constant ``foo`` (used as-is if specified)

* ``{$FOO}``: value of environment variable ``FOO`` (string ``None`` if not defined)

* ``{$BUILD_ID:local}``: value of environment variable ``BUILD_ID`` if defined,
  constant ``local`` otherwise

* generalized env var spec is: ``{$*FOO*:default}``:

  * ``$FOO`` will look for env var ``FOO`` exactly

  * ``$*FOO`` will use the first (alphabetically sorted) env var that ends with ``FOO``

  * ``$FOO*`` will use the first (alphabetically sorted) env var that starts with ``FOO``

  * ``$*FOO*`` will use the first (alphabetically sorted) env var that contains ``FOO``

  * ``default`` will be shown if no env var could be found


.. _PEP-440: https://www.python.org/dev/peps/pep-0440/

.. _setuptools_scm: https://github.com/pypa/setuptools_scm

.. _Scm class: https://github.com/codrsquad/setupmeta/blob/master/setupmeta/scm.py
