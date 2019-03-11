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
from glob import glob
from common.shell import sh


class ProjectError(Exception):
    """Handle with generic errors about the project"""

    def __init__(self, message):
        self.message = message


class ProjectNotFoundException(Exception):
    """Raised when the project workspace is not found."""
    pass


class Project:

    def __init__(self, env, workspace=None):
        self.workspace = None
        self.buildshell = None
        self.logfile = None
        self._env = env

        if workspace is not None:
            if self._is_valid_workspace(workspace):
                self.workspace = workspace
            else:
                raise ProjectNotFoundException()
        else:
            self._find_workspace(env)

        self.buildshell = os.path.join(self.workspace, 'build.sh')
        self.logfile = os.path.join(self.workspace, 'msbuild.log')

    @property
    def commit_count(self):
        count = sh('cd {} && git rev-list --count HEAD'.format(self.workspace),
                   print_stdout=False, return_stdout=True)
        return int(count)

    def build(self, with_analysis=True, dummy=False, pack=False):
        args = ['full', '/flp:LogFile=%s' % self.logfile]
        if with_analysis:
            args.append('/p:BuildWithAnalysis=True')
        sh(self.buildshell, args)
        if dummy:
            sh(self.buildshell, ['dummy'])
        if pack:
            sh(self.buildshell, ['pack'])

    def push_nuget_packages(self, apikey, source):
        nupkgs = glob(os.path.join(self.workspace, 'Artifacts/*.nupkg'))
        for p in nupkgs:
            cmd = 'dotnet nuget push {} -k {} -s {} -t 3000'.format(
                  p, apikey, source)
            sh(cmd, cwd=self.workspace)

    def _find_workspace(self, env):
        if self._is_valid_workspace(env.workspace):
            self.workspace = env.workspace
            return

        candidate = os.path.dirname(os.path.abspath(__file__))
        while True:
            parent = os.path.dirname(candidate)
            if candidate == parent:
                break
            if self._is_valid_workspace(candidate):
                self.workspace = candidate
                break
            candidate = parent

        if self.workspace is None:
            raise ProjectNotFoundException()

    def _is_valid_workspace(self, workspace):
        if workspace is not None:
            if os.path.isdir(workspace):
                if os.path.exists(os.path.join(workspace, 'build.sh')):
                    return True
        return False
