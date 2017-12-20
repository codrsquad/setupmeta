"""
Simplify your setup.py

url: https://github.com/zsimic/setupmeta
author: Zoran Simic zoran@simicweb.com
"""

import os
import subprocess       # nosec
import sys


__version__ = '0.5.0'


def which(program):
    if not program:
        return None
    if os.path.isabs(program) or os.path.exists(program):
        return program
    for p in os.environ.get('PATH', '').split(':'):
        fp = os.path.join(p, program)
        if os.path.isfile(fp):
            return fp
    return None


def run_program(program, *args, **kwargs):
    """ Run shell 'program' with 'args' """
    full_path = which(program)
    mode = kwargs.pop('mode', '')
    if not full_path:
        if 'fatal' in mode:
            sys.exit("'%s' is not installed" % program)
        if 'exitcode' in mode:
            return 1, None
        return None

    if 'dryrun' in mode:
        print("Would run: %s %s" % (full_path, ' '.join(args)))
        if 'exitcode' in mode:
            return 0, None
        return None

    if 'passthrough' in mode:
        print("Running: %s %s" % (full_path, ' '.join(args)))
    else:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE

    p = subprocess.Popen([full_path] + list(args), **kwargs)    # nosec
    output, error = p.communicate()
    output = decode(output)
    error = decode(error)

    if error:
        sys.stderr.write(error)

    if p.returncode:
        if 'fatal' in mode:
            sys.exit(p.returncode)
        if 'exitcode' in mode:
            return p.returncode, output
        raise Exception("%s exited with code %s" % (program, p.returncode))

    if 'exitcode' in mode:
        return p.returncode, output
    return output


def decode(value):
    """ Python 2/3 friendly decoding of output """
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return value


def stringify_dict(data):
    """
    :param dict data: Some python versions don't sort by key...
    :return str: Represented dict in a predictable manner
    """
    if not isinstance(data, dict):
        return stringify(data)
    result = []
    for k, v in sorted(data.items()):
        result.append("%s: %s" % (stringify(k), stringify(v)))
    return "{%s}" % ', '.join(result)


def stringify(value):
    """ Avoid having the annoying u'..' in str() representations """
    if isinstance(value, list):
        return repr([stringify(s) for s in value])
    if isinstance(value, tuple):
        return repr(tuple(stringify(s) for s in value))
    if isinstance(value, dict):
        return stringify_dict(value)
    return simplify_str(value)


if sys.version_info[0] < 3:
    def simplify_str(value):
        value = decode(value)
        if isinstance(value, unicode):      # noqa
            return value.encode('ascii', 'ignore')
        return str(value)

else:
    def simplify_str(value):
        """ Pretty string representation of 'text' for python3 """
        return str(decode(value))
