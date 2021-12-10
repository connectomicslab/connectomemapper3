# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module providing a `run()` command using `subprocess`."""

import os
import subprocess


def run(command, env=None, cwd=None):
    """Function calls by `CMP_MainWindowHandler` to run datalad commands.

    It runs the command specified as input via ``subprocess.run()``.

    Parameters
    ----------
    command : string
        String containing the command to be executed (required)

    env : os.environ
        Specify a custom os.environ

    cwd : os.path
        Specify a custom current working directory

    Examples
    --------
    >>> cmd = 'datalad save'
    >>> run(cmd) # doctest: +SKIP

    """
    if (cwd is None) or (cwd == {}):
        cwd = os.getcwd()

    merged_env = os.environ
    if env is not None:
        merged_env.update(env)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        env=merged_env,
        cwd=cwd,
    )
    while True:
        line = process.stdout.readline()
        line = str(line)[:-1]
        print(line)
        if line == "" and process.poll() is not None:
            break
    if process.returncode != 0:
        raise Exception("Non zero return code: %d" % process.returncode)
