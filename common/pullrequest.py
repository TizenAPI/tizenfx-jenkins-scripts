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
import re
from github import Github, GithubObject, GithubException
from common.buildlog import BuildLog

DIFF_PATTERN = re.compile(r'^@@ \-([0-9,]+) \+([0-9,]+) @@')


class PullRequest:
    def __init__(self, env):
        self.number = env.github_pr_number
        self.state = env.github_pr_state
        self.target_branch = env.github_pr_target_branch

        gh = Github(env.github_token)
        repo = gh.get_repo(env.github_repo)
        self._ghpr = repo.get_pull(self.number)

        self.latest_commit = self._ghpr.get_commits().reversed[0]
        self.changed_files = self._ghpr.get_files()

        self._map_difflines()

    def _map_difflines(self):
        self._line_to_position_map = {}
        self._file_diffhunk_paris = {}

        for f in self.changed_files:
            path = f.filename
            if f.patch is None:
                continue
            self._line_to_position_map[path] = {}
            diff_lines = []
            line_number = 0
            for position, line in enumerate(f.patch.split("\n")):
                m = DIFF_PATTERN.match(line)
                if m is not None:
                    hunkrange = m.group(2).split(',')
                    if len(hunkrange) == 1:
                        hunkrange.append(1)
                    diff_lines.append(list(map(int, hunkrange)))
                    line_number = int(hunkrange[0])
                    continue
                elif line[0] == '-':
                    continue
                self._line_to_position_map[path][line_number] = position
                line_number += 1
            self._file_diffhunk_paris[path] = diff_lines

    def set_status(self, state,
                   target_url=GithubObject.NotSet,
                   description=GithubObject.NotSet,
                   context=GithubObject.NotSet):
        if self._ghpr.commits < 1:
            return False
        self.latest_commit.create_status(
            state, target_url, description, context)
        return True

    def set_labels(self, *labels):
        self._ghpr.set_labels(*labels)

    def add_to_labels(self, *labels):
        try:
            self._ghpr.add_to_labels(*labels)
        except GithubException as err:
            print('Warning: ' + err.data['message'])

    def remove_from_labels(self, label):
        try:
            self._ghpr.remove_from_labels(label)
        except GithubException as err:
            print('Warning: ' + err.data['message'])

    def get_labels(self):
        return self._ghpr.get_labels()

    def create_review_comment(self, path, line_number, body):
        position = self._line_to_position_map[path][line_number]
        for c in self._ghpr.get_comments():
            if c.path == path and c.position == position and c.body == body:
                return False
        if self._ghpr.commits < 1:
            return False
        self._ghpr.create_review_comment(
            body, self.latest_commit, path, position)
        return True

    def create_issue_comment(self, body):
        self._ghpr.create_issue_comment(body)

    def report_warnings_as_review_comment(self, logfile):
        if not os.path.exists(logfile):
            return
        build_log = BuildLog(logfile)

        for f in self.changed_files:
            path = f.filename
            if f.patch is None:
                continue

            for line in self._file_diffhunk_paris[path]:
                for warn in build_log.warnings:
                    if not path.endswith(warn['file']):
                        continue
                    if (line[0]) <= warn['line'] \
                            and warn['line'] < (line[0] + line[1]):
                        body = 'warning {}: {}'.format(
                            warn['code'], warn['message'])
                        self.create_review_comment(path, warn['line'], body)

    def report_errors_as_issue_comment(self, logfile):
        if not os.path.exists(logfile):
            return
        bl = BuildLog(logfile)

        if len(bl.errors) < 1:
            return
        body = '### Build Error:\n'
        for err in bl.errors:
            body += '> {}({}): {}: {}\n' \
                .format(err['file'], err['line'], err['code'], err['message'])
        self.create_issue_comment(body)
