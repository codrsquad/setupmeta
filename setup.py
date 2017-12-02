"""
Stop copy-paste technology in setup.py

keywords: anti copy-paste, convenient, setup.py
"""

import os
import setuptools
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
EGG = os.path.join(HERE, 'setupmeta.egg-info')

ENTRY_POINTS = """
[distutils.setup_keywords]
name = setupmeta:register
"""


if __name__ == "__main__":
    os.chdir(HERE)
    args = dict(
        name='setupmeta',
        py_modules=['setupmeta'],
        entry_points=ENTRY_POINTS
    )

    if len(sys.argv) != 2 or sys.argv[1] != 'egg_info':
        # egg_info ran as sole command is bootstrap mode
        # don't refer to self in that case
        if not os.path.isdir(EGG):
            # Must run egg_info on its own at least once for bootstrap
            p = subprocess.Popen([sys.executable, 'setup.py', 'egg_info'])
            p.communicate()
            if p.returncode:
                sys.exit(p.returncode)
            if not os.path.isdir(EGG):
                sys.exit("Could not bootstrap egg-info")

        # We're bootstrapped now, we can self-refer
        args['setup_requires'] = ['setupmeta']

    setuptools.setup(**args)
