"""
Stop copy-paste technology in setup.py

Development Status :: 5 - Production/Stable
License :: OSI Approved :: Apache Software License
Programming Language :: Python
"""

from setupmeta import setup

setup_requirements = [
    # 'pytest-runner',
    # TODO(zsimic): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # 'pytest',
    # TODO: put package test requirements here
]


setup(
    name='setupmeta',
    author='Zoran Simic zoran@simicweb.com',
    keywords='anti copy-paste, convenient, setup.py',
    # test_suite='tests',
    # tests_require=test_requirements,
    # setup_requires=setup_requirements,
)
