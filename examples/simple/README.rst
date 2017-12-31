simple: Simple setup scenario
=============================

This is your typical small project, with:

* ``name`` is deduced from ``__title__`` in ``setup.py``

* one ``simple/__init__.py`` module (simple module folder) -> ``packages`` is properly set

* ``version``, ``keywords``, etc comes from ``simple/__init__.py`` (``download_url`` in ``simple/__init__.py`` mentions ``{version}``)

* an ``entry_points.ini`` file is used to specify some entry points

* a ``README.rst`` file partially used as ``long_description``


.. [[end long_description]]


This part will be ignored for setup.py ``long_description``, due to ``[[end long_description]]`` hidden token above (see source of this README, line 15)
