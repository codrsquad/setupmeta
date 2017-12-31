from setuptools import setup


def main_part(version):
    return '1.0'


setup(
    name='bogus',
    versioning={
        'main': main_part,
        'extra': []
    },
)
