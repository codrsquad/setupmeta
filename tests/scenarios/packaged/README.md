# Project description

This scenario simulates a PKG, with no git source available.

During testing, `src/pre-packaged` is renamed to `src/pre_packaged.egg-info`,
which will simulate a pip-expanded tarball + running of `setup.py egg_info`.

This simulates how setupmeta behaves in such an environment.
