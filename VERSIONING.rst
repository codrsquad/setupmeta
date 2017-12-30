Support for versioning
======================

setupmeta can use git tags to automatically version and bump the version of your project.

The functionality is completely optional and has to be explicitly enabled, note that:

* only git is supported currently (contributions for other SCMs welcome)

* git tags are used for versioning

* 2 strategies are pre-configured: Changes_ and Tag_, they both yield versions that play well with PEP-440_ (while remaining very simple).

If you find that one of these strategies fits you, you are welcome to use this. Otherwise simply ignore this functionality, or see Advanced_ for tweaking options.

In order to use setupmeta as a bridge to your git tags as versions, activate the feature by specifying one of the strategies in your ``setup.py`` like so::

    setup(
        versioning='tag',
        ...
    )

Once you have this, choose one of the below cases.

You should use then ``python setup.py bump`` to bump major/minor/patch (no need to assign tags manually).

Note that if you still explicitly mention a ``__version__ = '...'``` in your ``__init__.py`` or ``__about__.py`` etc, setupmeta will find it and also bump it accordingly.
This is done for convenience only, you don't need ``__version__`` anywhere if you use this setupmeta feature.

Changes
=======

This is well suited if you want to publish a new version at every commit (but don't want to keep bumping version in code for every commit).

``changes`` corresponds to this format: ``{major}.{minor}.{changes}``

State this in your ``setup.py``::

    setup(
        versioning='changes',
        ...
    )


Now, every time you commit a change, setupmeta will use the number of commits since last git tag to determine the 'patch' part of your version.


Example:

* first commit is tagged ``v0.1``, ``git describe`` will yield ``v0.1`` (no changes since last tag), and setupmeta will consider version to be ``0.1.0`` (tag 0.1 with 0 changes)

* a commit occurs, and doesn't add a git tag

    * ``git describe`` will now yield ``v0.1-1-g...`` (latest tag ``v0.1``, 1 commit since that tag)

    * Since only major+minor parts are in the tag, setupmeta will use the "git number of commits since last tag" as patch part

    * setupmeta will hence determine (auto-fill) the version to be ``0.1.1`` (tag 0.1 with 1 change)

    * If you publish from your CI job (or from anywhere), the version reported by your setup.py will be ``0.1.1``

    * If the repo is not clean (a dev checked out repo and modified something), the version will show as ``0.1.1.dev1``, which should make it obvious this is a local build

* Version will naturally evolve as ``0.1.2``, ``0.1.3``, etc at every commit

* Once we want to bump minor version, we run ``python setup.py bump --minor``, which will do the following:

    * Assign git tag ``v0.2``

    * Now, we go back to same thing as earlier: we'll get versions ``0.2.0``, ``0.2.1``, etc


Tag
===

This is well suited if you don't plan to publish often, and have a tag for each release.

``tag`` corresponds to this format: ``{major}.{minor}.{patch}``

State this in your ``setup.py``::

    setup(
        versioning='tag',
        ...
    )


Now, your reported version will be (for example):

* ``0.1.0`` when you build against the tag ``v0.1.0`` without any changes

* Any non-tagged commit will get a version of the form ``0.1.0b2`` (a "b" is added to get pip to interpret this as a "beta" version, the number following the "b" is the number of commits since tag "v0.1.0" here)

* Similarly, non-clean checkouts will get a version of the form ``0.1.0b2.dev1``

* Use ``python setup.py bump --[major|minor|patch]`` whenever you want to release (this will modify your ``__init__.py`` and assign a git tag accordingly)


Advanced
========

This is what ``versioning='tag'`` is a shortcut for::

    setup(
        versioning={
            'format': '{major}.{minor}.{patch}{beta}',
            'local': '?h{$*BUILD_ID:local}.{commitid}',
            'branches': ['master'],
        },
        ...
    )

* ``format``: what to use for the "main" part of the version

* ``local``: what to use when there are pending local changes

* ``branches``: branches where to accept bumps


Formatting
----------

The following names are available for specifying what ``format`` and ``local`` should carry when setupmeta computes the version number

* ``{major}``: Major part of version found in latest tag

* ``{minor}``: Minor part of version found in latest tag

* ``{patch}``: Patch part of version found in latest tag

* ``{changes}``: Number of changes since latest tag (0 if latest commit is tagged)

* ``{alpha}``: Designates an "alpha" version, empty when no changes since latest tag were committed, otherwise ``a{changes}``

* ``{beta}``: Designates a "beta" version, empty when no changes since latest tag were committed, otherwise ``a{changes}``

* ``{commitid}}``: empty when no changes since latest tag were committed, otherwise is a short string identifying commit, like ``g3bf9221``

* ``{devmarker}``: Extremely simple "uncommitted changes" marker: empty when checkout is clean, ``dev1`` otherwise



.. _PEP-440: https://www.python.org/dev/peps/pep-0440/
