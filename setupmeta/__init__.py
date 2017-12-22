"""
Simplify your setup.py

url: https://github.com/zsimic/setupmeta
author: Zoran Simic zoran@simicweb.com
"""

import os
import subprocess       # nosec
import sys


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
    """
    Run 'program' with 'args'

    :param str program: Path to program to run
    :param list(str) args: Arguments to pass to program
    :param bool dryrun: When True, do not run, just print what would be ran
    :param bool fatal: When True, exit immediately on return code != 0
    :param bool capture: None: let output pass through, return exit code
                         False: ignore output, return exit code
                         True: return exit code and output/error
    """
    full_path = which(program)
    fatal = kwargs.pop('fatal', False)
    dryrun = kwargs.pop('dryrun', False)
    capture = kwargs.pop('capture', None)   # None
    represented = "%s %s" % (full_path, ' '.join(args))
    if not full_path:
        if capture is True:
            return None
        if fatal:
            sys.exit("'%s' is not installed" % program)
        return 1

    if dryrun:
        print("Would run: %s" % represented)
        if capture is True:
            return None
        return 0

    if capture is None:
        print("Running: %s" % represented)

    else:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE

    p = subprocess.Popen([full_path] + list(args), **kwargs)    # nosec
    output, error = p.communicate()

    if error:
        sys.stderr.write(decode(error))

    if capture is True:
        return decode(output)

    if p.returncode and fatal:
        print("%s exited with code %s" % (represented, p.returncode))
        sys.exit(p.returncode)

    return p.returncode


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
