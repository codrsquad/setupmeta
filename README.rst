Stop copy-pasting stuff in setup.py
===================================

This project aims at disrupting the proliferation of copy-paste tech that's currently affecting all ``setup.py`` writers in this world.

Scan (first find wins):
    - setup(`attrs`)
    - convenience defaults:
        - `packages` to `[name]`
        - `long_description` = `read(README*)`
    - look for key/value definitions:
        - +optional pygradle support:
            - `PYGRADLE_PROJECT_VERSION`
        - `package/__version__.py`
        - `package/__init__.py`
        - `package.py`
        - `setup.py`
