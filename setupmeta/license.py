"""
Auto-fill license info (best-effort to cover the 5 top licenses...)

It's one of those annoying things, you're supposed to have:
- a LICENSE* file (copy-pasted legalese)
- a 'license' attribute in your metadata (short word(s), like "MIT")
- 'License :: OSI Approved :: ...' in your classifiers

Like the Shadoks say: (Why do simple when one can do complicated)
Why do simple when one can do complicated?
"""


class LicenseMojo:
    """ Attempt at reasoning with the madness """

    def __init__(self, short, match=None, classifier=None):
        assert short
        self.short = short
        self._match = match or short
        if not isinstance(self._match, list):
            self._match = [self._match]
        self.classifier = classifier or short

    def match(self, contents):
        if not contents or any(m not in contents for m in self._match):
            return None, None
        pre = ''
        post = ''
        short = self.short
        classifier = self.classifier
        if self.short == 'GNU':
            # The GNU guys are extra-allergic to simplicity
            if 'LESSER' in contents:
                pre = 'Lesser '
            elif 'AFFERO' in contents:
                pre = 'Affero '
            if 'Version 3' in contents:
                post = 'v3'
            elif 'Version 2' in contents:
                post = 'v2'
            short = '%sGPL%s' % (pre[0], post)
            classifier = "GNU %sGeneral Public License (%s)" % (pre, short)
        return short, classifier

    def __repr__(self):
        return self.short


# BSD is not even mentioning "BSD" in the legalese... sigh
BSD_CHATTER = [
    'Redistribution and use in source and binary forms',
    'permitted provided that the following conditions',
]


KNOWN_LICENSES = [
    LicenseMojo('MIT', 'MIT License', 'MIT License'),
    LicenseMojo('Apache Software License', 'apache.org/licenses'),
    LicenseMojo('GNU'),
    LicenseMojo('MPL', 'Mozilla Public License'),
    LicenseMojo('BSD', BSD_CHATTER, 'BSD License'),
]


def determined_license(contents):
    """
    :param str|None contents: Contents to determine license from
    :return tuple(str, str): Short name and classifier name
    """
    for mojo in KNOWN_LICENSES:
        short, classifier = mojo.match(contents)
        if short:
            return short, classifier
    return None, None
