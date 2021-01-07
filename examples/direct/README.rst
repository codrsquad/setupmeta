direct: A package implemented by one direct (not under src/) module folder
==========================================================================

This is your typical small project, with:

* ``name`` is given explicitly in ``setup.py``

* one ``direct/__init__.py`` module (simple module folder) -> ``packages`` is properly set

* ``version``, ``keywords``, etc comes from ``direct/__init__.py`` (``download_url`` in ``direct/__init__.py`` mentions ``{version}``)

* an ``entry_points.ini`` file is used to specify some entry points

* a ``README.rst`` file partially used as ``long_description``


.. [[end long_description]]


This part will be ignored for setup.py ``long_description``, due to ``[[end long_description]]`` hidden token above (see source of this README, line 15)

* project layout is::

    |-- LICENSE.txt
    |-- README.rst
    |-- classifiers.txt
    |-- direct/                     # Python module as subfolder
    |   |-- __init__.py             # Definitions are taken from here
    |-- entry_points.ini
    |-- requirements.txt
    |-- setup.py


* ``setup.py`` contents::

    from setuptools import setup


    setup(
        name="direct",
        setup_requires=['setupmeta']
    )


* ``direct/__init__.py`` contents::

    """
    A package implemented by one direct ((not under src/)) module folder

    keywords: direct, package
    author: Someone someone@example.com
    """

    __version__ = '1.0.0'
    __url__ = "https://github.com/codrsquad/simple"
    __download_url__ = "https://github.com/codrsquad/simple/archive/{version}.tar.gz"


    def main():
        pass


* ``explain`` output::

              author: (auto-adjust          ) Someone
                  \_: (direct/__init__.py:5 ) Someone someone@example.com
        author_email: (auto-adjust          ) someone@example.com
         classifiers: (classifiers.txt      ) ['Framework :: Pytest', 'Programming Language :: Python', 'License :: OSI Approved :: Apache Software License']
         description: (direct/__init__.py:2 ) A package implemented by one direct ((not under src/)) module folder
        download_url: (auto-fill            ) https://github.com/codrsquad/simple/archive/1.0.0.tar.gz
                  \_: (direct/__init__.py:10) https://github.com/codrsquad/simple/archive/{version}.tar.gz
        entry_points: (entry_points.ini     ) [console_scripts] direct = direct:main
    install_requires: (requirements.txt     ) ['click>=6.7']
            keywords: (direct/__init__.py:4 ) ['direct', 'package']
             license: (auto-fill            ) Apache 2.0
    long_description: (README.rst           ) 611 chars: direct: A package implemented by one direct ((not under src/)) module folder ...
                name: (setup.py:4           ) direct
            packages: (auto-fill            ) ['direct']
      setup_requires: (explicit             ) ['setupmeta']
              title*: (setup.py:4           ) direct
                 url: (direct/__init__.py:9 ) https://github.com/codrsquad/simple
             version: (direct/__init__.py:8 ) 1.0.0
