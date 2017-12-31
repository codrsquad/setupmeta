"""
author: Zoran Simic zoran@simicweb.com      # will be auto-adjusted
url: https://github.com/zsimic              # url will be auto-completed
download_url: archive/{version}.tar.gz      # will be auto-completed too
keywords: setup, docstring
"""

from setuptools import setup


__keywords__ = 'some,list,of,keywords,here,long,enough,to,be,abbreviated,by,the,explain,command'


setup(
    name='complex',
    versioning='changes',
    setup_requires=['setupmeta'],

    # This will overshadow classifiers.txt
    classifiers=['Programming Language :: Python'],

    extras_require=dict(
        bar=['docutils'],
        baz=['some', 'long', 'list-of', 'requirements'],
        foo=['long', 'enough', 'to-be', 'abbreviated'],
    ),

    # Here to verify that explicit takes precedence
    keywords=__keywords__.split(','),

    entry_points=dict(console_scripts="a=b"),

    # For illustration purposes
    license='foo',
)
