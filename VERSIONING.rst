Support for versioning
======================

setupmeta can use git tags to automatically version and bump the version of your project.

Rhe functionality is intentionally limited to 2 specific use cases (to avoid edge case hell):

* only git is supported

* git tags are used for versioning

* if you tag using ``major.minor``, the patch will be automatically computed from the number of commits since last tag

* if you tag using ``major.minor.patch``, reported version will be the tag itself, with possibly a ``bN`` added (for "beta") with N being the number of commits since last tag

This was done intentionally to play well with ``StrictVersion``, and because there's no real point in getting any more complicated with versioning...

If you find that one of these versioning schemes described here fits you, you are welcome to use this. Otherwise simply ignore this functionality.

First, in order to use setupmeta as a bridge to your git tags as versions, activate the feature by specifying this in your ``setup.py``::

    setup(
        versioning='tag',
        ...
    )

Once you have this, choose one of the below cases.

You should use then ``python setup.py bump`` to bump major/minor/patch (no need to assign tags manually).

Note that if you still explicitly mention a ``__version__ = '...'``` in your ``__init__.py`` or ``__about__.py`` etc, setupmeta will find it and bump it accordingly.
This is done for convenience only, you don't need ``__version__`` anywhere if you use this setupmeta feature.

You have to do the first tag manually, setupmeta will take it from there.

Major + minor rythm
===================

This is well suited if you want to publish a new version at every commit (but don't want to keep bumping version in code for every commit).

Assign a tag of the form ``major.minor``, we recommend you prefix the tag with "v", for example::

    git tag -a v0.1 -m "Version 0.1"
    git push --tags origin master

Now, every time you commit a change, setupmeta will use the number of commits since last git tag to determine the 'patch' part of your version.


Example:

* your latest tag is ``v1.0`` in git, ``git describe`` will yield ``v1.0`` (no changes since last tag), and setupmeta will consider version to be ``1.0.0`` (tag 1.0 with 0 changes)

* a commit occurs, and doesn't add a git tag

    * ``git describe`` will now yield ``v1.0-1-g...`` (latest tag ``v1.0``, 1 commit since that tag)

    * Since only major+minor parts are in the tag, setupmeta will use the "git number of commits since last tag" as patch part

    * setupmeta will hence determine (auto-fill) the version to be ``1.0.1`` (tag 1.0 with 1 change)

    * If you publish from your CI job (or from anywhere), the version reported by your setup.py will be ``1.0.1``

    * If the repo is not clean (a dev checked out repo and modified something), the version will show as ``1.0.1dev-g...``, which should make it obvious this is a local build

* Version will naturally evolve as ``1.0.2``, ``1.0.3``, etc at every commit

* Once we want to bump minor version, we run ``python setup.py bump --minor``, which will do the following:

    * (Modify your ``__init__.py`` to state ``__version__ = '1.1'`` if you still have ``__version__`` in there)

    * Assign git tag ``v1.1``

    * Now, we go back to same thing as earlier: we'll get versions ``1.1.0``, ``1.1.1``, etc


Tag-only rythm
==============

This is well suited if you don't plan to publish often, and have a tag for each release. In that case:

* Assign a tag of the for ``major.minor.patch``, for example::

    git tag -a v0.1.0 -m "Version 0.1.0"
    git push --tags origin master

* Use ``python setup.py bump --[major|minor|path]`` whenever you want to release (this will modify your ``__init__.py`` and assign git tag accordingly)

* Any non-tagged commit will get a version of the form ``1.0.1b2`` (a "b" is added to get pip to interpret this as a "beta" version, the number following the "b" is the number of commits since tag "v1.0.0" here)

* Similarly, non-clean checkouts will still get a version of the form ``1.0.1b2dev-g...``
