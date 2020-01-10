# coding=utf-8
"""
This is a package that has setupmeta pinned to an explicit version range.
"""
from setuptools import setup


setup(
    name="pinned",
    setup_requires=["setupmeta>=0.0.0"],
)
