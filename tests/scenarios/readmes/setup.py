"""
download_url: http://somewhere.net/readmes
foo: bar    # edge case: not a description, key/value definition
"""

from setuptools import setup


setup(
    name="readmes",
    setup_requires=["setupmeta"],
)
