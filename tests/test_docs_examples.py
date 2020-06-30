"""
Let's make sure them docs work yah?
"""
from contextlib import contextmanager
import os
import sys
import subprocess

import pytest


def repodir():
    """Return the abspath to the repo directory.
    """
    dirname = os.path.dirname
    dirpath = os.path.abspath(
        dirname(dirname(os.path.realpath(__file__)))
    )
    return dirpath


# GUI lib examples that probably don't need to be run from testing
# (at least without a lot more work).
_no_run = ['qt_ticker_table.py', 'tk.py']


def examples_dir():
    """Return the abspath to the examples directory.
    """
    return os.path.join(repodir(), 'examples')


@pytest.fixture
def run_example_in_subproc(testdir):

    @contextmanager
    def run(script_code):
        kwargs = dict()

        script_file = testdir.makefile('.py', script_code)
        cmdargs = [
            sys.executable,
            str(script_file),
        ]

        proc = testdir.popen(
            cmdargs,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )
        assert not proc.returncode
        yield proc
        proc.wait()
        assert proc.returncode == 0

    yield run


@pytest.mark.parametrize(
    'example_script',
    [f for f in os.listdir(examples_dir()) if '__' not in f],
)
def test_example(run_example_in_subproc, example_script):
    """Load and run scripts from this repo's ``examples/`` dir as a user
    would copy and pasing them into their editor.
    """
    ex_file = os.path.join(examples_dir(), example_script)

    if os.path.basename(ex_file) in _no_run:
        pytest.skip()

    with open(ex_file, 'r') as ex:
        code = ex.read()

        with run_example_in_subproc(code) as proc:
            proc.wait()
            err, _ = proc.stderr.read(), proc.stdout.read()

            # if we get some gnarly output let's aggregate and raise
            errmsg = err.decode()
            errlines = errmsg.splitlines()
            if err and 'Error' in errlines[-1]:
                raise Exception(errmsg)

            assert proc.returncode == 0
