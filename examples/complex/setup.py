"""
author: Zoran Simic zoran@simicweb.com      # will be auto-adjusted
url: https://github.com/zsimic              # url will be auto-completed
download_url: archive/{version}.tar.gz      # will be auto-completed too
keywords: setup, docstring
"""

from setuptools import setup


__keywords__ = 'setup'


setup(
    name='complex',
    setup_requires=['setupmeta'],

    # This will overshadow classifiers.txt
    classifiers=['Programming Language :: Python'],

    extras_require=dict(bar=['docutils']),

    keywords=['one', 'more'],
)
