Support for versioning
======================

setupmeta can use git tags to automatically version and bump the version of your project.

The functionality is completely optional and has to be explicitly enabled, note that:

* SCM tags are used for versioning

* only git is supported currently (contributions for other SCMs welcome)

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

Which simply means that determined version of your project (from git tag) is ``1.0.0.post2+g123``, while ``__init)_.py`` line 7 states it is "1.0.0".

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

``tag`` corresponds to this format: ``tag(master):{major}.{minor}.{patch}+{commitid}``

State this in your ``setup.py``::

    setup(
        versioning='tag',
        ...
    )


Now, your reported version will be (for example):

* ``0.1.0`` when you build against the tag ``v0.1.0`` without any changes

* Any non-tagged commit will get a version of the form ``0.1.0.post2`` (marking pip interpret this as a "post" release, the number following the ".post" is the number of commits since tag "v0.1.0" here)

* Similarly, dirty checkouts (with changes pending) will get a version of the form ``0.1.0.post2+g123``

* Use ``python setup.py bump --[major|minor|patch]`` whenever you want to release (this will modify your ``__init__.py`` and assign a git tag accordingly)


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

* first commit is tagged ``v0.1``, ``git describe`` will yield ``v0.1`` (no changes since last tag), and setupmeta will consider version to be ``0.1.0`` (tag 0.1 with 0 changes)

* a commit occurs, and doesn't add a git tag

    * ``git describe`` will now yield ``v0.1-1-g...`` (latest tag ``v0.1``, 1 commit since that tag)

    * Since only major+minor parts are in the tag, setupmeta will use the "git number of commits since last tag" as patch part

    * setupmeta will hence determine (auto-fill) the version to be ``0.1.1`` (tag 0.1 with 1 change)

    * If you publish from your CI job (or from anywhere), the version reported by your setup.py will be ``0.1.1``

    * If the repo is not clean (a dev checked out repo and modified something), the version will show as ``0.1.1+g123``, which should make it obvious this is a local build

* Version will naturally evolve as ``0.1.2``, ``0.1.3``, etc at every commit

* Once we want to bump minor version, we run ``python setup.py bump --minor``, which will do the following:

    * Assign git tag ``v0.2``

    * Now, we go back to same thing as earlier: we'll get versions ``0.2.0``, ``0.2.1``, etc


Advanced
========

* a **string** that can be either:

    * ``tag`` or ``changes`` for pre-configured version formats (see Tag_ or Changes_) above

    * a version format specified of the form ``tag(<branches>):<main><separator><extra>``

    * ``tag(<branches>):`` is optional, and you would use this full form only if you wanted version bumps to be possible on branches other than master,
      if you wanted bumps to be possible on both ``master`` and ``test`` branches for example, you would use ``tag(master,test):...``

    * the part before the ``<separator>`` sign specifies the format of the "main version" part (ie: when no local changes are present)

    * the part after the ``<separator>`` sign indicates what format to use when there are local changes (aka checkout is "dirty")

    * you can add ``<separator>!`` to force the extra part to always be shown, even when checkout is not dirty

    * characters that can be used as separators are: `` +@#%^;/,``, space can be used as a demarcation, but will not be rendered in the version per se

* a **dict** with the following keys:

    * ``main``

    * ``extra``

    * ``separator``

    * ``branches``


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

* ``{post}``: Designates a "post" release, empty when no changes since latest tag were committed, otherwise ``post{changes}``

* ``{commitid}}``: short string identifying commit, like ``g3bf9221``


.. _PEP-440: https://www.python.org/dev/peps/pep-0440/

.. _setuptools_scm: https://github.com/pypa/setuptools_scm
