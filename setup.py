# This library is self-using and auto-bootstraps itself

import os
import subprocess  # nosec
import sys

import setuptools


HERE = os.path.dirname(os.path.abspath(__file__))
EGG = os.path.join(HERE, "setupmeta.egg-info")

ENTRY_POINTS = """
[distutils.commands]
check = setupmeta.commands:CheckCommand
cleanall = setupmeta.commands:CleanCommand
entrypoints = setupmeta.commands:EntryPointsCommand
explain = setupmeta.commands:ExplainCommand
version = setupmeta.commands:VersionCommand

[setuptools.finalize_distribution_options]
setupmeta = setupmeta.hook:finalize_dist

[distutils.setup_keywords]
setup_requires = setupmeta.hook:register_keyword
versioning = setupmeta.hook:register_keyword
"""


def decode(text):
    if isinstance(text, bytes):
        return text.decode("utf-8")

    return text


def run_bootstrap(message):
    sys.stderr.write("--- Bootstrapping %s\n" % message)
    p = subprocess.Popen([sys.executable, "setup.py", "egg_info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # nosec
    output, error = p.communicate()
    if p.returncode:
        print(decode(output))
        sys.stderr.write("%s\n" % decode(error))
        sys.exit(p.returncode)

    if not os.path.isdir(EGG):
        sys.exit("Could not bootstrap egg-info")


def complete_args(args):
    args["setup_requires"] = ["setupmeta"]
    args["versioning"] = "dev"


if __name__ == "__main__":
    os.chdir(HERE)
    have_egg = os.path.isdir(EGG)

    # Explicit on entry points due to bootstrap
    args = dict(
        name="setupmeta",
        entry_points=ENTRY_POINTS,
        packages=["setupmeta"],
        python_requires=">=2.7",
        zip_safe=True,
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX",
            "Operating System :: Unix",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Software Development :: Build Tools",
            "Topic :: Software Development :: Libraries",
            "Topic :: Software Development :: Version Control",
            "Topic :: System :: Installation/Setup",
            "Topic :: System :: Software Distribution",
            "Topic :: Utilities",
        ],
    )
    if have_egg:
        # We're bootstrapped, we can self-refer
        complete_args(args)

    if len(sys.argv) == 2 and sys.argv[1] == "egg_info":
        # egg_info as lone command is bootstrap mode
        setuptools.setup(**args)
        sys.exit(0)

    if not have_egg:
        # No egg yet, not running egg_info -> must bootstrap
        run_bootstrap("first pass")

        # Rerun one more time to get the right VERSION filled-in etc
        run_bootstrap("second pass")

        # We're bootstrapped now, we can self-refer
        complete_args(args)

    setuptools.setup(**args)
