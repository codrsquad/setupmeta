Support for versioning
======================

setupmeta can use git tags to automatically **version** and **bump** the version of your project.

The functionality is optional and has to be explicitly enabled, note that:

* SCM tags are used for versioning

* only git is supported currently (contributions for other SCMs welcome and should be easy, see `Scm class`_)

* It can be a drop-in replacement for setuptools_scm_

* 2 strategies are pre-configured: Tag_ and Changes_, they both yield versions that play well with PEP-440_ (while remaining very simple).

* See Advanced_ for more info

In order to use setupmeta as a bridge to your git tags as versions, activate the feature by specifying one of the strategies in your ``setup.py`` like so::

    setup(
        versioning='tag',
        ...
    )

You can use then ``python setup.py bump`` to bump major/minor/patch (no need to assign tags manually).

Note that if you still explicitly mention a ``__version__ = '...'``` in your ``__init__.py`` or ``__about__.py`` etc, setupmeta will find it and also bump it accordingly.
This is done for convenience only, you don't need ``__version__`` anywhere if you use setupmeta versioning.


How does it work?
=================

setupmeta declares a keyword to setuptools called ``versioning``, if you specify that keyword (and it is valid), setupmeta versioning will be enabled.

You can specify ``versioning``:

* explicitly in your ``setup()`` call

* implicitly in your ``__init__.py``, ``__about__.py``, docstrings etc (setupmeta will show where ``versioning`` was defined, like any other value it handles)

Tag-based versioning will take precedence on any other ``version`` specification you may have, and ``setup.py bump`` will modify those over values for ``version`` that you have (if any) accordingly.

For example, if you have this:

* ``setup(versioning='tag')`` in your ``setup.py``

* ``__version__ = '1.0.0'`` in your ``__init__.py`` line 7

* ``git describe`` yields ``v1.0.0-2-g123`` (ie: latest tag is "v1.0.0", there are 2 commits since that tag, and current commit id is "123")

Now, running ``setup.py explain`` will show you something like this::

    version: (git          ) 1.0.0.post2+g123
         \_: (__init__.py:7) 1.0.0

Which means that determined version of your project (from git tag) is ``1.0.0.post2+g123``, while ``__init)_.py`` line 7 states it is "1.0.0".

If you commit your changes, your checkout won't be dirty anymore, and the number of commits since latest tag will be 3, so ``setup.py explain`` will now show::

    version: (git          ) 1.0.0.post3
         \_: (__init__.py:7) 1.0.0

Ie:

* deduced version is 1.0.0, with 3 commits since latest tag

* there are no local pending changes, so the "extra" part is not shown (by default)

* ``__init__.py`` being static, it does not reflect this yet (but will if/when you ``setup.py bump``)

* note that this versioning scheme should play well with PEP-440_

If you now run ``setup.py bump --patch --commit``, the following would happen:

* your ``__init__.py`` line 7 is modified to state ``__version__ = '1.0.1'``, and committed with description "Version 1.0.1"

* tag ``v1.0.1`` is applied at that new commit

* now ``setup.py explain`` says::

    version: (git          ) 1.0.1
         \_: (__init__.py:7) 1.0.1

Note that you do NOT need any ``__version__ = ...`` stated anywhere, we're showing this only here for illustration purposes.
In general, you should simply use ``versioning='tag'`` (or any other format you like).

You could leverage this ``__version__`` possibility if you have specific use case for that
(like: you'd like to show which version your code is at without using something like ``import pkg_resources``)


Preconfigured formats
=====================

Tag
---

This is well suited if you don't plan to publish often, and have a tag for each release.

``tag`` corresponds to this format: ``tag(master):{major}.{minor}.{patch}{post}+{commitid}``

State this in your ``setup.py``::

    setup(
        versioning='tag',
        ...
    )

Now, every time you commit a change, setupmeta will use the number of commits since last git tag to determine the 'post' part of your version.


Example:

======  ======  ================  =============================================================================
Commit  Tag     Version           Note (command ran to add tag)
======  ======  ================  =============================================================================
none            0.0.0+initial     No commit yet
g1              0.0.0.post1+g1    Initial commit, no tag yet defaults to 0.0.0 but is considered dirty (no tag)
g2              0.0.0.post2+g2
g3              0.0.0.post3+g3
g4      v0.1.0  0.1.0             ``bump --minor --commit``
g5              0.1.0.post1       (1 commit since tag)
g6              0.1.0.post2
g7      v0.1.1  0.1.1             ``bump --patch --commit``
g8              0.1.1.post1
g9      v1.0.0  1.0.0             ``bump --major --commit``
g10             1.0.0.post1
======  ======  ================  =============================================================================

* Without any tag, version defaults to ``0.0.0`` and is always considered "dirty"

* First tag here is ``v0.1.0``, ``git describe`` will yield ``v0.1.0`` (no changes since last tag), and setupmeta will consider version to be ``0.1.0`` (tag as-is)

* A commit occurs and doesn't add a git tag, version for that commit will be ``0.1.0.post1`` (tag 0.1.0 with 1 change since tag)

* A 2nd commit occurs and doesn't add a git tag, version for that commit will be ``0.1.0.post2`` etc

* Dirty checkouts (with changes pending) will get a version of the form ``0.1.0.post2+g123``

* Use ``python setup.py bump --[major|minor|patch]`` whenever you want to bump major, minor or patch revision (this will assign a git tag accordingly)

    * ``python setup.py bump --patch --commit`` -> tag "v0.1.1" is added, version is now ``0.1.1``

    * Next commit after that will be version ``0.1.1.post1`` etc


Changes
-------

This is well suited if you want to publish a new version at every commit (but don't want to keep bumping version in code for every commit).

``changes`` corresponds to this format: ``{major}.{minor}.{changes}+{commitid}``

State this in your ``setup.py``::

    setup(
        versioning='changes',
        ...
    )


Now, every time you commit a change, setupmeta will use the number of commits since last git tag to determine the 'patch' part of your version.


Example:

======  ======  ================  =============================================================================
Commit  Tag     Version           Note (command ran to add tag)
======  ======  ================  =============================================================================
none            0.0.0+initial     No commit yet
g1              0.0.1+g1          Initial commit, no tag yet defaults to 0.0.0 but is considered dirty (no tag)
g2              0.0.2+g2
g3              0.0.3+g3
g4      v0.1    0.1.0             ``bump --minor --commit``
g5              0.1.1             (1 commit since tag)
g6              0.1.2
g7      v0.2    0.2.0             ``bump --minor --commit`` (note: can't bump "patch" with this format)
g8              0.2.1
g9      v1.0    1.0.0             ``bump --major --commit``
g10             1.0.1
======  ======  ================  =============================================================================

* Without any tag, version defaults to ``0.0.0`` and is always considered "dirty"

* First tag here is ``v0.1``, ``git describe`` will yield ``v0.1`` (no changes since last tag), and setupmeta will consider version to be ``0.1.0`` (tag 0.1 with 0 changes)

* A commit occurs and doesn't add a git tag, version for that commit will be ``0.1.1`` (tag 0.1 with 1 change since tag)

* A 2nd commit occurs and doesn't add a git tag, version for that commit will be ``0.1.2`` etc

* Dirty checkouts (with changes pending) will get a version of the form ``0.1.2+g123``

* Use ``python setup.py bump --[major|minor]`` whenever you want to bump major or minor version (this will assign a git tag accordingly)

    * ``python setup.py bump --minor --commit`` -> tag "v0.2" is added, version is now ``0.2.0``

    * Next commit after that will be version ``0.2.1`` etc


Advanced
========

``versioning`` can be customized beyond the 2 pre-defined strategies described above, it can be passed as a **string** describing the version format, or a **dict** for even more customization:

* a **string** can be of the form:

    * ``tag`` or ``changes`` for pre-configured version formats (see Tag_ or Changes_ above)

    * a version format specified of the form ``tag(<branches>):<main><separator><extra>``

    * ``tag(<branches>):`` is optional, and you would use this full form only if you wanted version bumps to be possible on branches other than master,
      if you want bumps to be possible on both ``master`` and ``test`` branches for example, you would use ``tag(master,test):...``

    * See Formatting_ below to see what's usable for ``<main>`` and ``<extra>``

    * the ``<main>`` part (before the ``<separator>`` sign) specifies the format of the "main version" part (ie: when no local changes are present)

    * the ``<extra>`` part (after the ``<separator>`` sign indicates) what format to use when there are local changes (aka checkout is "dirty")

    * you can add an exclamation point ``!`` after separator to force the extra part to always be shown (even when checkout is not dirty)

    * characters that can be used as separators are: `` +@#%^;/,`` (space can be used as a demarcation, but will not be rendered in the version per se)

* a **dict** with the following keys:

    * ``main``: a **string** (see Formatting_) or callable (if callable given, **bump** command becomes unusable)

    * ``extra``: a **string** (see Formatting_) or callable (custom function yielding a string from a given ``Version``, see `Scm class`_)

    * ``separator``: character to use as separator between ``main`` and ``extra``

    * ``branches``: list of branch names (or csv) where to allow **bump**


This is what ``versioning='tag'`` is a shortcut for::

    setup(
        versioning={
            'main': '{major}.{minor}.{patch}{post}',
            'extra': '{commitid}',
            'branches': ['master'],
            'separator': '+'
        },
        ...
    )


Formatting
----------

The following can be used as format specifiers:

* ``{major}``: Major part of version

* ``{minor}``: Minor part of version

* ``{patch}``: Patch part of version

* ``{changes}``: Number of changes since last version tag from current commit (0 if current commit is tagged)

* ``{post}``: Designates a "post" release (PEP-440_ friendly), empty when current commit is version-tagged, otherwise ``.postN`` (wehre ``N`` is ``{changes}``)

* ``{commitid}}``: short string identifying commit, like ``g3bf9221``

* ``foo``: constant ``foo`` (used as-is if specified)

* ``{$FOO}``: value of environment variable ``FOO`` (string ``None`` if not defined)

* ``{$BUILD_ID:local}``: value of environment variable ``BUILD_ID`` if defined, constant ``local`` otherwise

* generalized env var spec is: ``{prefix$*FOO*:default}``:

    * ``prefix`` is shown only if any env var containing ``FOO`` in this case is defined

    * ``$FOO`` will look for env var ``FOO`` exactly

    * ``$*FOO`` will use the first (alphabetically sorted) env var that ends with ``FOO``

    * ``$FOO*`` will use the first (alphabetically sorted) env var that starts with ``FOO``

    * ``$*FOO*`` will use the first (alphabetically sorted) env var that contains ``FOO``

    * ``default`` will be shown if no corresponding env var is defined


Examples
========

* ``{major}.{minor}.{patch}{post}+h{$BUILD_ID:local}.{commitid}`` will yield versions like:

    * ``1.0.0`` (clean, on tag)

    * ``1.0.0.post1`` (clean, one commit since tag)

    * ``1.0.0.post1+hlocal.g123`` (dirty, no $BUILD_ID)

    * ``1.0.0.post1+h123.g123`` (dirty, with $BUILD_ID)


* ``{major}.{minor}.{patch}{post}+!h{$BUILD_ID:local}.{commitid}`` would be the same as above, but ``extra`` part **always** shown:

    * ``1.0.0+hlocal.g123`` (clean, on tag, no $BUILD_ID)

    * ``1.0.0.post1+h123.g123`` (clean, one commit since tag, with $BUILD_ID)

    * ``1.0.0.post1+hlocal.g123`` (dirty, no $BUILD_ID)

    * ``1.0.0.post1+h123.g123`` (dirty, with $BUILD_ID)


* ``{major}.{minor}.{changes} .{commitid}``: space demarcates ``main`` vs ``extra``, but is not added in the final version render

    * ``1.0.0`` (clean, on tag)

    * ``1.0.1`` (clean, one commit since tag)

    * ``1.0.1.g123`` (dirty, note: no space between ``1.0.1`` ("main" part) and ``.g123`` ("extra" part))


* ``{major}.{minor}.{changes}.{commitid}``: similar to above, except here there is no separator, and hence no ``extra`` part
  (the ``.{commitid}`` is part of **main** part and will be always rendered, so equivalent to above with explamation point, like: ``{major}.{minor}.{changes} !.{commitid}``)


.. _PEP-440: https://www.python.org/dev/peps/pep-0440/

.. _setuptools_scm: https://github.com/pypa/setuptools_scm

.. _Scm class: https://github.com/zsimic/setupmeta/blob/master/setupmeta/scm.py
