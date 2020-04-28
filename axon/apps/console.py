#!/usr/bin/env python
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
"""
This module defines Console App in AXON system.

This app will be common interface for running any commands on console either
by remote nodes or by other apps at same node.

Other apps which need to work on console such as Running traffic through other
tools (Iperf etc) or running port monioring tools shall also use/inherit this
common app.
"""

import logging
import os
import signal
import subprocess
import time

from axon.apps.base import BaseApp

log = logging.getLogger(__name__)


class Console(BaseApp):
    NAME = "CONSOLE"

    def __init__(self):
        """
        Console App runs commands on the console of this node.
        """
        pass

    def run_command(self, cmnd, env=None, cwd=None, timeout=-1):
        """
        This function runs the command "cmnd" and returns the return code and
        result for the command. The command is taken as single string.

        Parameters
        ----------
        cmnd : string
            Command to be executed in string format.
        env : string
            Any environment configuration to be set for environment.
        cwd : string
            Absolute path to the directory where command should be run.
        timeout : int
            time in seconds after which command should be killed. Default of -1
            means command is run without a time limit.

        Returns
        -------
        (int, string)
            returns a tuple of command execution return code and output.
        """

        p = subprocess.Popen(cmnd, shell=True, stdin=None, bufsize=-1, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             close_fds=True, cwd=cwd, preexec_fn=os.setsid)

        # Start the counter for command to finish if requested.
        if timeout > 0:
            time_limit = time.time() + timeout

            while time.time() < time_limit:
                if p.poll() is None:
                    time.sleep(1)
                else:
                    break

            # command is still active, kill it.
            if p.poll() is None:
                log.warning("TIMEOUT : Killing command %s" % cmnd)
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)

        stdout_val = p.communicate()[0]
        return p.returncode, stdout_val.strip()


if __name__ == '__main__':
    # Simple command
    status, result = Console().run_command("ls -lrt")
    print (status, result.decode('utf-8'))

    # Timeout failure
    status, result = Console().run_command("ping 127.0.0.1", timeout=1)
    print (status, result.decode('utf-8'))
