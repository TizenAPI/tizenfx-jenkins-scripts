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

"""Jenkins script to check the Pull Request"""

import os
import re
import sys
import difflib
from common.pullrequest import PullRequest
from common.project import Project, ProjectError, ProjectNotFoundException
from common.buildlog import BuildLog
from common.shell import ShellError
from common.apidb import APIDB
from common import apitool
import global_configuration as conf

CTX_CHK_BUILD = 'Build Checker'
CTX_CHK_API = 'API Checker'
LABEL_INTERNAL_API_CHANGED = 'Internal API Changed'
LABEL_ACR_REQUIRED = 'ACR Required'
LABEL_ACR_ACCEPTED = 'ACR Accepted'


def main():
    env = BuildEnvironment(os.environ)
    pr = PullRequest(env)
    proj = Project(env)

    if pr.target_branch not in conf.BRANCH_API_LEVEL_MAP.keys():
        print('{} branch is not a managed branch.\n'
              .format(pr.target_branch))
        return

    # Step 1: Set a label for API level detection to the pull request.
    pr.add_to_labels(conf.BRANCH_API_LEVEL_MAP[pr.target_branch])

    # Step 2: Set pending status to all checkers.
    set_pending_to_all_checkers(pr, env)

    # Step 3: Run "Build Checker"
    run_build_checker(pr, proj, env)

    # Step 4: Run "API Checker"
    run_api_checker(pr, proj, env)


def set_pending_to_all_checkers(pr, env):
    pr.set_status('pending', description='Build started.',
                  context=CTX_CHK_BUILD, target_url=env.build_url)
    pr.set_status('pending', description='Wait for build to finish.',
                  context=CTX_CHK_API, target_url=env.build_url)


def run_build_checker(pr, proj, env):
    try:
        proj.build()
        pr.set_status('success', description='Build finished.',
                      context=CTX_CHK_BUILD, target_url=env.build_url)
        pr.report_warnings_as_review_comment(proj.logfile)
    except ShellError:
        pr.set_status('failure', description='Build failed.',
                      context=CTX_CHK_BUILD, target_url=env.build_url)
        pr.report_errors_as_issue_comment(proj.logfile)
        raise
    except:
        pr.set_status('error', description='System error.',
                      context=CTX_CHK_BUILD, target_url=env.build_url)
        raise


def run_api_checker(pr, proj, env):
    pr.set_status('pending', description='API check started.',
                  context=CTX_CHK_API, target_url=env.build_url)

    try:
        category = conf.BRANCH_API_LEVEL_MAP[pr.target_branch]
        apijson_file = os.path.join(proj.workspace, 'Artifacts/build.api.json')

        # extract API
        apitool.extract(proj, apijson_file)

        # compare API with APIDB
        comp = APIDB(env).compare(category, apijson_file)

        # set labels
        if comp.internal_api_changed:
            pr.add_to_labels(LABEL_INTERNAL_API_CHANGED)
        else:
            pr.remove_from_labels(LABEL_INTERNAL_API_CHANGED)
        if comp.public_api_changed:
            if not pr.exists_in_labels(LABEL_ACR_ACCEPTED):
                pr.add_to_labels(LABEL_ACR_REQUIRED)
        else:
            pr.remove_from_labels(LABEL_ACR_REQUIRED)

        if comp.total_changed_count > 0:
            # TODO: if public api is changed, go to acr process
            # create an api changed report as a comment
            body = make_api_changed_report(comp)
            pr.create_issue_comment(body)

        pr.set_status('success', description='API check finished.',
                      context=CTX_CHK_API, target_url=env.build_url)

    except:
        pr.set_status('error', description='System error.',
                      context=CTX_CHK_API, target_url=env.build_url)
        raise


def make_api_changed_report(comp):
    differ = difflib.Differ()
    diff_lines = []

    if len(comp.added) > 0:
        for i in comp.added:
            diff_lines.extend(print_api_for_diff(comp.new_api[i], '+ '))
    if len(comp.changed) > 0:
        for i in comp.changed:
            diff_lines.extend(differ.compare(
                print_api_for_diff(comp.old_api[i]),
                print_api_for_diff(comp.new_api[i])))
    if len(comp.removed) > 0:
        for i in comp.removed:
            diff_lines.extend(print_api_for_diff(comp.old_api[i], '- '))

    body = ''
    if comp.public_api_changed:
        body += '**Public API Changed**\n'
        body += 'Please follow the ACR process for the changed API below.\n'
    elif comp.internal_api_changed:
        body += '**Internal API Changed**\n'

    if comp.total_changed_count > 5:
        body += ('<details><summary>'
                 'Show API Changes. (Added: {}, Changed: {}, Removed: {})'
                 '</summary>\n\n'.format(
                     len(comp.added), len(comp.changed), len(comp.removed)))

    body += '```diff\n'
    for line in diff_lines:
        if line[0] is not '?':
            body += line
    body += '```\n'

    if comp.total_changed_count > 5:
        body += '</details>\n'

    return body


def print_api_for_diff(info, prefix=''):
    lines = []
    for p in info.get('Privileges', []):
        lines.append('{}/// <privilege>{}</privilege>\n'.format(prefix, p))
    for f in info.get('Features', []):
        lines.append('{}/// <feature>{}</feature>\n'.format(prefix, f))
    if 'Since' in info.keys():
        lines.append('{}/// <since_tizen> {} </since_tizen>\n'
                     .format(prefix, info['Since']))
    if info['IsHidden']:
        lines.append('{}[EditorBrowsable(EditorBrowsableState.Never)]\n'
                     .format(prefix))

    lines.append('{}{}{}\n\n'
                 .format(prefix,
                         'static ' if info['IsStatic'] else '',
                         info['Signature']))
    return lines


class NotValidEnvironmentException(Exception):
    """Raised when there are no requried environment variables."""
    pass


class BuildEnvironment:

    def __init__(self, env):
        try:
            self.github_token = env['GITHUB_TOKEN']
            self.github_repo_git_url = env['GITHUB_REPO_GIT_URL']
            m = re.match(r'git://github.com/(.+/.+)\.git',
                         self.github_repo_git_url)
            self.github_repo = m.group(1)
            self.github_pr_number = int(env['GITHUB_PR_NUMBER'])
            self.github_pr_state = env['GITHUB_PR_STATE']
            self.github_pr_target_branch = env['GITHUB_PR_TARGET_BRANCH']
            self.build_url = env['BUILD_URL']
            self.workspace = env['WORKSPACE']
            self.aws_access_key_id = env['AWS_ACCESS_KEY_ID']
            self.aws_secret_access_key = env['AWS_SECRET_ACCESS_KEY']
        except KeyError:
            raise NotValidEnvironmentException()


if __name__ == "__main__":
    try:
        main()
    except NotValidEnvironmentException:
        sys.stderr.write(
            "Error: No required environment variables to run checkers.\n")
        sys.exit(1)
    except ProjectNotFoundException:
        sys.stderr.write("Error: No such found project to build.\n")
        sys.exit(1)
    except ProjectError as err:
        sys.stderr.write("Error: " + err.message + '\n')
        sys.exit(1)
    except ShellError as err:
        sys.stderr.write("Error: " + err.message + '\n')
        sys.exit(1)
