"""
To be replaced by a dependency on toml or pipfile,
if that still works via setup_requires
"""


def toml_key_value(line):
    line = line and line.strip()
    if not line:
        return None, None
    if '=' not in line:
        return None, line
    key, _, value = line.partition('=')
    key = key.strip()
    value = value.strip()
    if not key or not value:
        return None, None
    key = toml_key(key)
    if key is None:
        return None, line
    return key, value


def toml_accumulated_value(acc, text):
    if acc:
        return "%s %s" % (acc, text)
    return text


def is_toml_section(line):
    if not line or len(line) < 3:
        return False
    if line[0] == '[' and line[-1] == ']':
        line = line[1:-1]
        if len(line) >= 3 and line[0] == '[' and line[-1] == ']':
            line = line[1:-1]
        return toml_key(line) is not None


def normalized_toml(lines):
    """ Collapse toml multi-lines into one line """
    if not lines:
        return None
    result = []
    prev_key = None
    acc = None
    for line in lines:
        key, value = toml_key_value(line)
        if key or is_toml_section(line):
            if acc:
                if prev_key:
                    result.append("%s=%s" % (prev_key, acc))
                else:
                    result.append(acc)
                acc = None
            prev_key = key
            acc = toml_accumulated_value(acc, value)
            continue
        acc = toml_accumulated_value(acc, line)
    if prev_key:
        result.append("%s=%s" % (prev_key, acc))
    return result


def parsed_toml(text):
    """ Can't afford to require toml """
    if isinstance(text, dict):
        return text
    if text and not isinstance(text, list):
        text = text.split('\n')
    text = normalized_toml(text)
    if not text:
        return None
    sections = {}
    section = sections
    for line in text:
        key, value = toml_key_value(line)
        if key is None and value is None:
            continue
        if key is None and is_toml_section(value):
            section_name = line.strip('[]')
            section = sections.get(section_name)
            if section is None:
                section = {}
                sections[section_name] = section
        else:
            section[key] = toml_value(value)
    return sections


def toml_key(text):
    text = text and text.strip()
    if not text or len(text) < 2:
        return text
    fc = text[0]
    if fc == '"' or fc == "'":
        if text[-1] != fc:
            return None
        return text[1:-1]
    return text


def toml_value(text):
    text = text and text.strip()
    if not text:
        return text
    if text.startswith('{'):
        rdict = {}
        for line in text.strip('{}').split(','):
            key, _, value = line.partition('=')
            rdict[toml_key(key)] = toml_value(value)
        return rdict
    if text.startswith('['):
        rlist = []
        for line in text.strip('[]').split(','):
            rlist.append(toml_value(line))
        return rlist
    if text.startswith('"'):
        return toml_key(text)
    if text == 'true':
        return True
    if text == 'false':
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text
