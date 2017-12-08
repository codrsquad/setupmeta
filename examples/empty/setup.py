"""
foo: bar    # edge case: not a description, key/value definition
"""

from setuptools import setup


setup(
    name='empty',
    setup_requires=['setupmeta']
)
