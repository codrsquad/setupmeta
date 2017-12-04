"""
Hook for setuptools
"""

import distutils.dist

from setupmeta.model import MetaDefs, SetupMeta


def distutils_hook(dist, command, *args, **kwargs):
    """ distutils.dist.Distribution.get_option_dict replacement

    distutils calls this right after having processed 'setup_requires'
    It really calls self.get_option_dict(command), we jump in
    so we can decorate the 'dist' object appropriately for our own commands
    """
    if not hasattr(dist, '_setupmeta'):
        # Add our ._setupmeta object
        # (distutils calls this several times, we need only one)
        dist._setupmeta = SetupMeta(dist)
        MetaDefs.fill_dist(dist, dist._setupmeta.to_dict())
    original = MetaDefs.dd_original
    return original(dist, command, *args, **kwargs)


def register(*args, **kwargs):
    """ Hook into distutils in order to do our magic

    We use this as a 'distutils.setup_keywords' entry point, see setup.py
    """
    if MetaDefs.dd_original is None:
        # Replace Distribution.get_option_dict so we can inject our parsing
        # This is the earliest I found after 'setup_requires' are imported
        # Do the replacement only once (distutils calls this several times...)
        MetaDefs.dd_original = distutils.dist.Distribution.get_option_dict
        distutils.dist.Distribution.get_option_dict = distutils_hook
