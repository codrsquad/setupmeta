"""
Simplify your setup.py

url: https://github.com/zsimic/setupmeta
author: Zoran Simic zoran@simicweb.com
"""

import os
import sys


__version__ = '0.4.1'


def which(program):
    if not program:
        return None
    if os.path.isabs(program):
        return program
    for p in os.environ.get('PATH', '').split(':'):
        fp = os.path.join(p, program)
        if os.path.isfile(fp):
            return fp
    return None


def run_program(program, *args, **kwargs):
    """ Run shell 'program' with 'args' """
    import subprocess                                           # nosec
    full_path = which(program)
    passthrough = kwargs.pop('passthrough', False)
    if not full_path:
        if passthrough:
            sys.exit("'%s' is not installed" % program)
        return None
    if passthrough == 'dryrun':
        print("Would run: %s %s" % (full_path, to_str(args)))
        return None
    if not passthrough:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
    p = subprocess.Popen([full_path] + list(args), **kwargs)    # nosec
    output, error = p.communicate()
    output = to_str(output) if output else None
    if p.returncode:
        if passthrough:
            if error:
                sys.stderr.write(to_str(error))
            sys.exit(p.returncode)
        raise Exception("%s exited with code %s" % (program, p.returncode))
    return output


def str_dict(data):
    """
    :param dict data: Some python versions don't sort by key...
    :return str: Represented dict in a predictable manner
    """
    if not isinstance(data, dict):
        return to_str(data)
    result = []
    for k, v in sorted(data.items()):
        result.append("%s: %s" % (to_str(k), to_str(v)))
    return "{%s}" % ', '.join(result)


if sys.version_info[0] < 3:
    def strify(value):
        """ Avoid having the annoying u'..' in str() representations """
        if isinstance(value, unicode):      # noqa
            return value.encode('ascii', 'ignore')
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return [strify(s) for s in value]
        if isinstance(value, tuple):
            return tuple(strify(s) for s in value)
        if isinstance(value, dict):
            return str_dict(value)
        return value

    def to_str(text):
        """ Pretty string representation of 'text' for python2 """
        return str(strify(text))

else:
    def to_str(text):
        """ Pretty string representation of 'text' for python3 """
        if isinstance(text, bytes):
            return text.decode('utf-8')
        if isinstance(text, dict):
            return str_dict(text)
        return str(text)
