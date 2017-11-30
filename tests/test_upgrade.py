import os
import shutil
import subprocess
import tempfile

import pytest

import setupmeta
import conftest

SETUPMETA = os.path.join(conftest.PROJECT, 'setupmeta.py')
GH = 'https://raw.githubusercontent.com/zsimic/setupmeta/master/setupmeta.py'
LOCAL_URL = 'file://%s' % os.path.join(conftest.PROJECT, 'setupmeta.py')


@pytest.fixture(params=['setupmeta', 'bash'])
def mode(request):
    """ Yield one test per scenario """
    yield request.param


def run_self_upgrade(mode, args):
    with conftest.capture_output() as (out, err):
        exit_msg = ''
        try:
            if mode == 'bash':
                os.environ['URL'] = LOCAL_URL
                script = os.path.join(conftest.PROJECT, 'get-setupmeta')
                p = subprocess.Popen(
                    [script] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                output, error = p.communicate()
                return setupmeta.to_str(output) + setupmeta.to_str(error)
            else:
                setupmeta.__url__ = LOCAL_URL
                setupmeta.self_upgrade(args)
        except SystemExit as e:
            # self_upgrade() calls sys.exit()
            exit_msg = "%s" % e
        out = setupmeta.to_str(out.getvalue())
        err = setupmeta.to_str(err.getvalue())
        return out + err + exit_msg


def do_run(mode, args, *expected):
    output = run_self_upgrade(mode, args)
    for msg in expected:
        assert msg in output
    return output


def test_upgrade(mode):
    """ Test that upgrade functionality works """
    tmpdir = tempfile.mkdtemp()

    try:
        if mode != 'bash':
            # Sanity check --help
            do_run(mode, ['--help'], "Install/upgrade")

            # Bogus target
            do_run(mode, ['foo/bar'], "not a valid directory")

            # Bogus invalid url
            do_run(mode, [tmpdir, '-ufoo'], "Could not fetch foo")

            # Bogus existing url
            url = os.path.join(conftest.PROJECT, 'classifiers.txt')
            url = 'file://%s' % url
            do_run(mode, [tmpdir, '-u', url], "Invalid url", "please check")

            # dryrun
            do_run(mode, [tmpdir, '-n'], "Would seed", "--dryrun")

        # 1st run: seed setupmeta
        do_run(mode, [tmpdir], "Seeded ")

        # 2nd run: we're up to date now
        do_run(mode, [tmpdir], "Already up to date")

        # simulate file changed
        with open(os.path.join(tmpdir, 'setupmeta.py'), 'a') as fh:
            fh.write('added one line')

        if mode != 'bash':
            # dryrun
            do_run(mode, [tmpdir, '-n'], "Would upgrade", "--dryrun")

        # 3rd run: we're not up to date anymore
        do_run(mode, [tmpdir], "Upgraded ")

        # 4th run: up to data again now
        do_run(mode, [tmpdir], "Already up to date")

    finally:
        shutil.rmtree(tmpdir)


def test_urls():
    url = 'https://github.com/zsimic/setupmeta'
    assert setupmeta.default_upgrade_url(url=url) == GH

    url = setupmeta.default_upgrade_url(url='file:///foo')
    assert url == 'file:///foo'
