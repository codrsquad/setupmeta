"""
Hook for setuptools/distutils
"""

import distutils.dist
import functools

from setupmeta.model import MetaDefs, SetupMeta


def finalize_dist(dist, setup_requires=None):
    """
    Hook into setuptools' Distribution class before attributes are interpreted.

    This is called before Distribution attributes are finalized and validated,
    allowing us to transform attribute values before they have to conform to
    the usual spec. This step is *before* configuration is additionally read
    from config files.
    """
    setup_requires = setup_requires or dist.setup_requires
    setup_requires = setup_requires if isinstance(setup_requires, list) else [setup_requires]

    if any(dep.startswith('setupmeta') for dep in setup_requires):
        dist._setupmeta = SetupMeta().preprocess(dist)
        MetaDefs.fill_dist(dist, dist._setupmeta.to_dict(only_meaningful=False))

        # Override parse_command_line for this instance only.
        dist.parse_command_line = functools.partial(parse_command_line, dist)


# Reference to original distutils.dist.Distribution.parse_command_line
parse_command_line_orig = distutils.dist.Distribution.parse_command_line
def parse_command_line(dist, *args, **kwargs):  # noqa: E302 (keep override close to function it replaces)
    """ distutils.dist.Distribution.parse_command_line replacement

    This allows us to insert setupmeta's imputed values for various attributes
    after all configuration has interpreted and read from config files, and just
    before any commands are run. We then call `parse_command_line` to continue
    normal execution.
    """
    dist._setupmeta.finalize(dist)
    MetaDefs.fill_dist(dist, dist._setupmeta.to_dict())

    return parse_command_line_orig(dist, *args, **kwargs)


def register_keyword(dist, name, value):
    """
    Allow registration of our 'versioning' keyword.

    We also use this as an opportunity to verify that setupmeta is
    initialized correctly, just in case `setup_requires` is populated late
    (which appears to be the case in some contexts).

    TODO: Add validation for the `versioning` keyword?
    """
    if name == 'setup_requires' and not hasattr(dist, '_setupmeta'):
        finalize_dist(dist, setup_requires=value)
