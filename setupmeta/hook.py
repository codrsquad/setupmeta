"""
Hook for setuptools/distutils
"""

import distutils.dist

from setupmeta.model import MetaDefs, SetupMeta


# Reference to original distutils.dist.Distribution.parse_command_line
dd_original = distutils.dist.Distribution.parse_command_line


def distutils_hook(dist, *args, **kwargs):
    """ distutils.dist.Distribution.parse_command_line replacement

    distutils calls this right after having processed 'setup_requires'
    It really calls self.parse_command_line(command), we jump in
    so we can decorate the 'dist' object appropriately for our own commands
    """
    if dist.script_args and not hasattr(dist, "_setupmeta"):
        # Add our ._setupmeta object (distutils calls this several times, we need only one)
        dist._setupmeta = SetupMeta(dist)
        MetaDefs.fill_dist(dist, dist._setupmeta.to_dict())
    return dd_original(dist, *args, **kwargs)


def register(dist, name, value):
    """ Hook into distutils in order to do our magic

    We use this as a 'distutils.setup_keywords' entry point
    We don't need to do anything specific here (in this function)
    But we do need distutils to import this module
    """
    if name == "setup_requires":
        if value == "setupmeta" or "setupmeta" in value:
            # Replace Distribution.parse_command_line so we can inject our parsing
            distutils.dist.Distribution.parse_command_line = distutils_hook

        else:
            distutils.dist.Distribution.parse_command_line = dd_original
