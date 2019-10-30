from setupmeta import license


BSD_SAMPLE = """
...
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
...
"""


def test_license():
    assert license.determined_license(None) is None
    assert license.determined_license("") is None
    assert license.determined_license("blah blah version 5") is None
    assert license.determined_license("... Version 2.0 http://www.apache.org/licenses/ ...") == "Apache 2.0"
    assert license.determined_license(BSD_SAMPLE) == "BSD"
    assert license.determined_license("MIT License ...") == "MIT"
    assert license.determined_license("Mozilla Public License Version 2.0 ...") == "MPL"
    assert license.determined_license("GNU AFFERO GENERAL PUBLIC LICENSE Version 3 ...") == "AGPLv3"
    assert license.determined_license("GNU GENERAL PUBLIC LICENSE Version 3 ...") == "GPLv3"
    assert license.determined_license("GNU LESSER GENERAL PUBLIC LICENSE Version 3 ...") == "LGPLv3"
