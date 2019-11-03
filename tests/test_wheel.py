import os

import setupmeta


def test_wheel(sample_project):
    # Fake existence of a build folder, that should be in .gitignore (but isn't)
    # Presence of a new file there should not mark version as dirty
    build_folder = os.path.join(sample_project, "build")
    os.mkdir(build_folder)
    with open(os.path.join(build_folder, "report.txt"), "w") as fh:
        fh.write("This is some build report\n")

    dist_folder = os.path.join(sample_project, "dist")

    assert setupmeta.run_program("pip", "wheel", "--only-binary", ":all:", "-w", "dist", ".") == 0
    files = os.listdir(dist_folder)
    assert len(files) == 2
    assert "sample-0.1.0-py2.py3-none-any.whl" in files

    # Now let's modify one of the files
    with open(os.path.join(sample_project, "sample.py"), "w") as fh:
        fh.write("print('hello')\n")

    assert setupmeta.run_program("pip", "wheel", "--only-binary", ":all:", "-w", "dist", ".") == 0
    files = os.listdir(dist_folder)
    assert len(files) == 3
    assert "sample-0.1.0-py2.py3-none-any.whl" in files
    assert "sample-0.1.0.dirty-py2.py3-none-any.whl" in files
