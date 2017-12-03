Alternative way of using ``setupmeta``
======================================

It is recommended to use setupmeta_ via the ``setup_requires`` method as described in the `main readme`_.

If for some reason you can't have setuptools_ **version 38+** however (this commit_ in particular is needed), you can still use the approach described here.


Installation
============

Grab the ``setupmeta.py`` script in your project folder, you can do so using one of the following ways::

    wget https://raw.githubusercontent.com/zsimic/setupmeta/setupmeta.py

Or using pip::

    pip install setupmeta
    setupmeta.py upgrade .

If you already have the script in some project, you can use it to "seed" another project like so::

    ./setupmeta.py upgrade ~/my/other/project/


This will grab the latest version of the script and put it in ``~/my/other/project/``, it's almost equivalent to
(and you could do this also BTW, the only difference from above is that no check for updates is performed)::

    cp ./setupmeta.py ~/my/other/project/setupmeta.py

The script can auto-upgrade itself, once you have a copy, you can get the latest version by running this (default target is current folder)::

    ./setupmeta.py upgrade


- Once you have a local copy of ``setupmeta.py`` next to your ``setup.py``, check it in: you can now import it from your ``setup.py`` (as it has no extra dependency requirements)

- Then, write your ``setup.py`` like so::

    """
    Short description of the project
    """

    from setupmeta import setup             # This is where setupmeta comes in

    __version__ = '1.0.0'                   # This can come from your __about__.py etc
    __title__ = 'myproject'                 # Some project like to have this as a reusable constant

    setup()                                 # You could also do the usual stuff like name='...' here

And that's it.

All you need is that local copy of ``setupmeta.py``, keep it up-to-date and move to the new style when you can.

.. _setupmeta: https://github.com/zsimic/setupmeta

.. _main readme: https://github.com/zsimic/setupmeta/blob/master/README.rst

.. _setuptools: https://github.com/pypa/setuptools

.. _commit: https://github.com/pypa/setuptools/commit/bb71fd1bed9f5e5e239ef99be82ed57e9f9b1dda#diff-6b59155d3acbddf6010c0f20482d4eea
