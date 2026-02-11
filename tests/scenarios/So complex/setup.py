"""
author: Someone someone@example.com         # will be auto-adjusted
url: https://example.com/complex            # url will be auto-completed
download_url: archive/{version}.tar.gz      # will be auto-completed too
keywords: setup, doc"string                 # Exercise quoting edge case
version: 1.0a1
"""

from setuptools import setup

__version__ = '1.0b1'  # fmt: skip # noqa: Q000
__keywords__ = "some,really,long,list,of,keywords,here,long,enough,to,be,abbreviated,by,the,explain,command"
__title__ = "My cplx-nm_here"


setup(
    versioning="branch(release,main):{major}.{minor}.{patch}+h{$*BUILD_ID:local}.{dirty}",
    setup_requires=["setupmeta"],
    # Edge case galore
    classifiers=["Programming Language :: Python", "foo"],
    extras_require={
        "bar": ["docutils"],
        "baz": ["some", "really", "long", "list-of", "requirements"],
        "foo": ["long", "enough", "to-be", "abbreviated"],
    },
    description=f"Wass{'u' * 120}p!?",
    keywords=__keywords__.split(","),
    entry_points={"console_scripts": "a=b"},
    license="foo",
)
