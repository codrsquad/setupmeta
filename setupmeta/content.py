"""
Functionality related to interacting with project and distutils content
"""

import glob
import os
import re

import setupmeta


# Recognized README tokens
RE_README_TOKEN = re.compile(r"(.?)\.\. \[\[([a-z]+) (.+)\]\](.)?")


def load_contents(relative_path, limit=0):
    """Return contents of file with 'relative_path'

    :param str relative_path: Relative path to file
    :param int limit: Max number of lines to load
    :return str|None: Contents, if any
    """
    lines = setupmeta.readlines(relative_path, limit=limit)
    if lines is not None:
        return "".join(lines).strip()


def load_readme(relative_path, limit=0):
    """ Loader for README files """
    lines = setupmeta.readlines(relative_path, limit=limit)
    if lines is not None:
        content = []
        for line in lines:
            m = RE_README_TOKEN.search(line)
            if not m:
                content.append(line)
                continue

            pre, post = m.group(1), m.group(4)
            pre = pre and pre.strip()
            post = post and post.strip()
            if pre or post:
                content.append(line)
                continue  # Not beginning/end, or no spaces around

            action = m.group(2)
            param = m.group(3)
            if action == "end" and param == "long_description":
                break

            if action == "include":
                included = load_readme(param, limit=limit)
                if included:
                    content.append(included)

        return "".join(content).strip()


def resolved_paths(relative_paths):
    """
    :param list(str) relative_paths: Ex: "README.rst", "README*"
    :return str|None: Contents of the first non-empty file found
    """
    candidates = []
    for path in relative_paths:
        # De-dupe and respect order (especially for globbed paths)
        if "*" in path:
            full_path = setupmeta.project_path(path)
            for expanded in sorted(glob.glob(full_path)):
                relative_path = os.path.basename(expanded)
                if relative_path not in candidates:
                    candidates.append(relative_path)
            continue
        if path not in candidates:
            candidates.append(path)
    return candidates


def find_contents(relative_paths, loader=None, limit=0):
    """Return contents of first file found in 'relative_paths', globs OK

    :param list(str) relative_paths: Ex: "README.rst", "README*"
    :param callable|None loader: Optional custom loader function
    :param int limit: Max number of lines to load
    :return str|None, str|None: Contents and path where they came from, if any
    """
    if loader is None:
        loader = load_contents
    for relative_path in resolved_paths(relative_paths):
        contents = loader(relative_path, limit=limit)
        if contents:
            return contents, relative_path
    return None, None
