import os
import shutil
import tempfile

import setupmeta
import conftest

SETUPMETA = os.path.join(conftest.PROJECT, 'setupmeta.py')


def run_self_upgrade(args):
    with conftest.capture_output() as (out, err):
        exit_msg = ''
        try:
            setupmeta.self_upgrade(args)
        except SystemExit as e:
            # self_upgrade() calls sys.exit()
            exit_msg = "%s" % e
        out = setupmeta.to_str(out.getvalue())
        err = setupmeta.to_str(err.getvalue())
        return out + err + exit_msg


def run_setupmeta(args, *expected):
    output = run_self_upgrade(args)
    for msg in expected:
        assert msg in output
    return output


def test_upgrade():
    """ Test that upgrade functionality works """
    tmpdir = tempfile.mkdtemp()
    local_url = 'file://%s' % os.path.join(conftest.PROJECT, 'setupmeta.py')
    setupmeta.__url__ = local_url

    try:
        # Sanity check --help
        run_setupmeta(['--help'], "Install/upgrade")

        # Bogus target
        run_setupmeta(['foo/bar'], "not a valid directory")

        # Bogus invalid url
        run_setupmeta([tmpdir, '-ufoo'], "Could not fetch foo")

        # Bogus existing url
        url = 'file://%s' % os.path.join(conftest.PROJECT, 'classifiers.txt')
        run_setupmeta([tmpdir, '-u', url], "Invalid url", "please check")

        # dryrun
        run_setupmeta([tmpdir, '-n'], "Would seed", "--dryrun")

        # 1st run: seed setupmeta
        run_setupmeta([tmpdir], "Seeded ")

        # 2nd run: we're up to date now
        run_setupmeta([tmpdir], "Already up to date")

        # simulate file changed
        with open(os.path.join(tmpdir, 'setupmeta.py'), 'a') as fh:
            fh.write('added one line')

        # dryrun
        run_setupmeta([tmpdir, '-n'], "Would upgrade", "--dryrun")

        # 3rd run: we're not up to date anymore
        run_setupmeta([tmpdir], "Upgraded ")

        # 4th run: up to data again now
        run_setupmeta([tmpdir], "Already up to date")

    finally:
        shutil.rmtree(tmpdir)
