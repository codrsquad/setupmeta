"""
Auto-fill license info (best-effort to cover the 5 top licenses...)

It's one of those annoying things, you're supposed to have:
- a LICENSE* file (copy-pasted legalese)
- a 'license' attribute in your metadata (short word(s), like "MIT")
- 'License :: OSI Approved :: ...' in your classifiers

Like the Shadoks say: why do simple when one can do complicated?
"""

import re


RE_VERSION = re.compile(r"version (\d+(.\d+)?)", re.IGNORECASE)


class License:
    def __init__(self, short, match=None, classifier=None):
        self.short = short
        self._match = match or short
        if not isinstance(self._match, list):
            self._match = [self._match]
        self.classifier = classifier or short

    def match(self, contents):
        if not contents or any(m not in contents for m in self._match):
            return None, None
        pre = ""
        post = ""
        short = self.short
        classifier = self.classifier

        version = None
        m = RE_VERSION.search(contents)
        if m:
            version = m.group(1)

        if self.short == "GNU":
            # The GNU guys are extra-allergic to simplicity
            if "LESSER" in contents:
                pre = "Lesser "
            elif "AFFERO" in contents:
                pre = "Affero "
            if version:
                post = "v%s" % version[0]
            short = "%sGPL%s" % (pre and pre[0], post)
            classifier = "GNU %sGeneral Public License (%s)" % (pre, short)
        if short == "Apache" and version:
            # Most project seem to abbreviate this to "Apache 2.0"
            short = "%s %s" % (self.short, version)
        return short, "License :: OSI Approved :: %s" % classifier


# BSD is not even mentioning "BSD" in the legalese... sigh
BSD_CHATTER = ["Redistribution and use in source and binary forms", "permitted provided that the following conditions"]


KNOWN_LICENSES = [
    License("MIT", "MIT License", "MIT License"),
    License("Apache", "apache.org/licenses", "Apache Software License"),
    License("GNU"),
    License("MPL", "Mozilla Public License"),
    License("BSD", BSD_CHATTER, "BSD License"),
]


def determined_license(contents):
    """
    :param str|None contents: Contents to determine license from
    :return tuple(str, str): Short name and classifier name
    """
    for license in KNOWN_LICENSES:
        short, classifier = license.match(contents)
        if short:
            return short, classifier
    return None, None
