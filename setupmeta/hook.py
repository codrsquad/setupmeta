"""
Hook for setuptools/distutils
"""

import distutils.dist

from setupmeta.model import MetaDefs, SetupMeta


finalize_options_orig = distutils.dist.Distribution.finalize_options
def finalize_options(dist):  # noqa: E302 (keep override close to function it replaces)
    """
    Hook into setuptools' Distribution class before attributes are interpreted.

    This is called before Distribution attributes are finalized and validated,
    allowing us to transform attribute values before they have to conform to
    the usual spec. This step is *before* configuration is additionally read
    from config files.
    """
    dist._setupmeta = SetupMeta().preprocess(dist)
    MetaDefs.fill_dist(dist, dist._setupmeta.to_dict(only_meaningful=False))
    finalize_options_orig(dist)


# Reference to original distutils.dist.Distribution.parse_command_line
parse_command_line_orig = distutils.dist.Distribution.parse_command_line
def parse_command_line(dist, *args, **kwargs):  # noqa: E302 (keep override close to function it replaces)
    """ distutils.dist.Distribution.parse_command_line replacement

    This allows us to insert setupmeta's imputed values for various attributes
    after all configuration has interpreted and read from config files, and just
    before any commands are run. We then call `parse_command_line` to continue
    normal execution.
    """
    # _setupmeta won't be present when running initial setup_requires install.
    # We still need it for our commands.
    if not hasattr(dist, '_setupmeta'):
        dist._setupmeta = SetupMeta()
    dist._setupmeta.finalize(dist)
    MetaDefs.fill_dist(dist, dist._setupmeta.to_dict())

    return parse_command_line_orig(dist, *args, **kwargs)


def register(dist, name, value):
    """ Hook into distutils in order to do our magic

    We use this as a 'distutils.setup_keywords' entry point
    We don't need to do anything specific here (in this function)
    But we do need distutils to import this module
    """
    if name == "setup_requires":
        value = value if isinstance(value, list) else [value]
        if any(item.startswith('setupmeta') for item in value):
            # Replace Distribution finalization hooks so we can inject our parsed options
            distutils.dist.Distribution.finalize_options = finalize_options
            distutils.dist.Distribution.parse_command_line = parse_command_line
        else:
            # Replace Distribution hooks with original implementations (just in case rerunning in same process)
            distutils.dist.Distribution.finalize_options = finalize_options_orig
            distutils.dist.Distribution.parse_command_line = parse_command_line_orig

            # Since this registration may happen after option finalization when loaded
            # in the same process, we delete any unnecessary SetupMeta attribute.
            if hasattr(dist, '_setupmeta'):
                del dist._setupmeta
