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

import re


class BuildLog:
    def __init__(self, filePath):
        self.warnings = []
        self.errors = []
        self._file = open(filePath, 'r')
        self._parseLog()

    def _parseLog(self):
        pattern = re.compile(
            r'[0-9:]+>(.+)\(([0-9]+),[0-9]+\): (error|warning) ([A-Z0-9]+): (.+) \[/')
        for line in self._file.readlines():
            m = pattern.match(line.strip())
            if m is not None:
                item = {'file': m.group(1),
                        'line': int(m.group(2)), 'type': m.group(3),
                        'code': m.group(4), 'message': m.group(5)}
                if item['type'] == 'warning':
                    self.warnings.append(item)
                elif item['type'] == 'error':
                    self.errors.append(item)

    def __del__(self):
        self._file.close()
