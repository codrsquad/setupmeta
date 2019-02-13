import os
import re

from mock import patch

import setupmeta


RE_META = re.compile(r""".*['"](\S+/METADATA)['"].*""")


def get_metadata_line(output):
    for line in output.split("\n"):
        m = RE_META.match(line)
        if m:
            return m.group(1)


@patch.dict(os.environ, {"SETUPMETA_DEBUG": "1"})
def test_wheel(sample_project):
    # Fake existence of a build folder, that should be in .gitignore (but isn't)
    # Presence of a new file should not mark version as dirty
    build_folder = os.path.join(sample_project, "build")
    os.mkdir(build_folder)
    with open(os.path.join(build_folder, "report.txt"), "w") as fh:
        fh.write("This is some build report\n")

    output = setupmeta.run_program("pip", "-vvv", "wheel", "--only-binary", ":all:", "-w", "dist", ".", capture=True)
    meta = get_metadata_line(output)
    assert meta == "sample-0.1.0.dist-info/METADATA"

    # Now let's modify one of the files
    with open(os.path.join(sample_project, "sample.py"), "w") as fh:
        fh.write("print('hello')\n")

    output = setupmeta.run_program("pip", "-vvv", "wheel", "--only-binary", ":all:", "-w", "dist", ".", capture=True)
    meta = get_metadata_line(output)
    assert meta == "sample-0.1.0.dirty.dist-info/METADATA"
