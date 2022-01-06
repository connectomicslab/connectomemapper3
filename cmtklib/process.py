# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module providing a `run()` command using `subprocess`."""

import os
import subprocess


def run(command, env=None, cwd=None):
    """Function calls by `MainWindowHandler` to run datalad commands.

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
    merged_env = os.environ

    if (cwd is None) or (cwd == {}):
        cwd = os.getcwd()

    if env is not None:
        merged_env.update(env)

    process = subprocess.run(
        command,
        capture_output=True,
        shell=True,
        env=merged_env,
        cwd=cwd,
    )
    print(process.stdout.decode("utf8"))

    if process.returncode != 0:
        raise Exception(
                f'Non zero return code: {process.returncode}\n\n'
                f'\tStandard error:\n {process.stderr.decode("utf8")}')
