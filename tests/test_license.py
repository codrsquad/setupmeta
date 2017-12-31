from setupmeta import license


BSD_SAMPLE = """
...
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
...
"""

APACHE_SAMPLE = "... Version 2.0 http://www.apache.org/licenses/ ..."
MIT_SAMPLE = "MIT License ..."
MPL_SAMPLE = "Mozilla Public License Version 2.0 ..."
AGPL_SAMPLE = "GNU AFFERO GENERAL PUBLIC LICENSE Version 3 ..."
GPL_SAMPLE = "GNU GENERAL PUBLIC LICENSE Version 3 ..."
LGPL_SAMPLE = "GNU LESSER GENERAL PUBLIC LICENSE Version 3 ..."


def check_license(sample, short, classifier):
    s, c = license.determined_license(sample)
    assert s == short
    if classifier:
        assert c == "License :: OSI Approved :: %s" % classifier
    else:
        assert c is None


def test_license():
    check_license(None, None, None)
    check_license('', None, None)
    check_license('blah blah version 5', None, None)
    check_license(APACHE_SAMPLE, 'Apache 2.0', 'Apache Software License')
    check_license(BSD_SAMPLE, 'BSD', 'BSD License')
    check_license(MIT_SAMPLE, 'MIT', 'MIT License')
    check_license(MPL_SAMPLE, 'MPL', 'MPL')
    check_license(AGPL_SAMPLE, 'AGPLv3', 'GNU Affero General Public License (AGPLv3)')
    check_license(GPL_SAMPLE, 'GPLv3', 'GNU General Public License (GPLv3)')
    check_license(LGPL_SAMPLE, 'LGPLv3', 'GNU Lesser General Public License (LGPLv3)')
