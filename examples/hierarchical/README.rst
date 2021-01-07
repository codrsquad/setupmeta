hierarchical: A hierarchical package (code under src/)
======================================================

This is a project that keeps its code under a ``src/`` subfolder:

* ``name`` is given explicitly in ``setup.py``

* module + submodule in ``src/hierarchical/`` -> ``packages`` is properly set to ``['hierarchical', 'hierarchical.submodule']``

* ``version``, ``keywords``, etc comes from ``src/hierarchical/__init__.py`` (``download_url`` mentions ``{version}``)

* an ``entry_points.ini`` file is used to specify some entry points

* a ``README.rst`` file partially used as ``long_description``

.. [[end long_description]]


This part will be ignored for setup.py ``long_description``, due to ``[[end long_description]]`` hidden token above (see source of this README, line 15)

* project layout is::

    |-- LICENSE.txt
    |-- README.rst
    |-- classifiers.txt
    |-- entry_points.ini
    |-- requirements.txt
    |-- setup.py
    |-- src/
        |-- hierarchical/               # Python module under src/
            |-- __init__.py             # Definitions are taken from here
            |-- submodule/              # Submodule shows up in 'packages'
                |-- __init__.py


* ``setup.py`` contents::

    from setuptools import setup


    setup(
        name="hierarchical",
        setup_requires=['setupmeta']
    )


* ``src/hierarchical/__init__.py`` contents::

    """
    A hierarchical package (code under src/, tests under tests/)

    keywords: hierarchical, package
    author: Someone someone@example.com
    """

    __version__ = '1.0.0'
    __url__ = "https://github.com/codrsquad/simple"
    __download_url__ = "https://github.com/codrsquad/simple/archive/{version}.tar.gz"


    def main():
        pass


* ``explain`` output::

              author: (auto-adjust                    ) Someone
                  \_: (src/hierarchical/__init__.py:5 ) Someone someone@example.com
        author_email: (auto-adjust                    ) someone@example.com
         classifiers: (classifiers.txt                ) ['Framework :: Pytest', 'Programming Language :: Python', 'License :: OSI Approved :: MIT License']
         description: (README.rst:1                   ) A hierarchical package (code under src/)
                  \_: (src/hierarchical/__init__.py:2 ) A hierarchical package (code under src/, tests under tests/)
        download_url: (auto-fill                      ) https://github.com/codrsquad/simple/archive/1.0.0.tar.gz
                  \_: (src/hierarchical/__init__.py:10) https://github.com/codrsquad/simple/archive/{version}.tar.gz
        entry_points: (entry_points.ini               ) [console_scripts] hierarchical = hierarchical:main subm = hierarchical.submodule:main
    install_requires: (requirements.txt               ) ['arrow', 'click>=6.7']
            keywords: (src/hierarchical/__init__.py:4 ) ['hierarchical', 'package']
             license: (auto-fill                      ) MIT
    long_description: (README.rst                     ) 616 chars: hierarchical: A hierarchical package (code under src/) ...
                name: (setup.py:4                     ) hierarchical
         package_dir: (auto-fill                      ) {: src}
            packages: (auto-fill                      ) ['hierarchical', 'hierarchical.submodule']
      setup_requires: (explicit                       ) ['setupmeta']
              title*: (setup.py:4                     ) hierarchical
                 url: (src/hierarchical/__init__.py:9 ) https://github.com/codrsquad/simple
             version: (src/hierarchical/__init__.py:8 ) 1.0.0
