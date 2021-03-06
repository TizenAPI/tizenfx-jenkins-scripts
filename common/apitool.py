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
from common.shell import sh
from common.project import ProjectError

APITOOL_PATH = '../tools/bin/APITool.dll'


def extract(proj, output):
    artifacts_dir = os.path.join(proj.workspace, 'Artifacts/bin/public')
    if not os.path.isdir(artifacts_dir):
        raise ProjectError('No Artifacts')
    apitool_cmd = [
        os.path.join(os.path.dirname(__file__), APITOOL_PATH),
        'print', '--include-hidden', '--format=json',
        '-o ' + output, artifacts_dir]
    sh('dotnet', apitool_cmd)
