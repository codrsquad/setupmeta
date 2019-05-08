from setuptools import setup


def main_part(version):
    return "1.0"


setup(
    name="bogus",
    setup_requires="setupmeta",
    versioning={
        "main": main_part,
        "extra": [],
    },
)
