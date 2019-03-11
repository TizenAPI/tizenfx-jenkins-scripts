#!/usr/bin/env python3
#
# Copyright (c) 2019 Samsung Electronics Co., Ltd All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from subprocess import Popen, PIPE


class ShellError(Exception):
    """Raised when shell return non-zero."""

    def __init__(self, message):
        self.message = message


def sh(cmd, args=(), cwd=None,
       print_stdout=True, return_status=False, return_stdout=False):

    cmdml = cmd.split('\n')
    if (len(cmdml) > 1):
        for cmdsl in cmdml:
            if len(cmdsl.strip()) > 0:
                sh(cmdsl, args, cwd, print_stdout)
        return

    cmd = '{} {}'.format(cmd.strip(), ' '.join(args))
    ret = ''
    if print_stdout:
        print('[shell] ' + cmd)
    pobj = Popen(cmd, cwd=cwd, shell=True, stdout=PIPE,
                 stderr=PIPE, universal_newlines=True)
    while True:
        output = pobj.stdout.readline()
        ret += output
        if output == '' and pobj.poll() is not None:
            break
        if output and print_stdout:
            print(output.strip())
    rc = pobj.poll()
    if return_status:
        return rc
    else:
        if rc:
            raise ShellError("Error running %s, error : %s" %
                             (cmd, pobj.stderr.read()))
    if return_stdout:
        return ret
