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

"""Jenkins script to update API DB"""

import os
import re
import sys
from common.project import Project, ProjectError, ProjectNotFoundException
from common.shell import ShellError
from common.apidb import APIDB
from common import apitool
import global_configuration as conf


def main():
    env = BuildEnvironment(os.environ)

    if env.github_branch_name not in conf.BRANCH_API_LEVEL_MAP.keys():
        print('{} branch is not a managed branch.\n'
              .format(env.github_branch_name))
        return

    # Build project
    proj = Project(env)
    proj.build()

    # Extract API from the project
    apijson_file = os.path.join(proj.workspace, 'Artifacts/build.api.json')
    apitool.extract(proj, apijson_file)

    # Update APIDB
    category = conf.BRANCH_API_LEVEL_MAP[env.github_branch_name]
    db = APIDB(env)
    db.import_datafile(category, apijson_file)


class NotValidEnvironmentException(Exception):
    """Raised when there are no requried environment variables."""
    pass


class BuildEnvironment:

    def __init__(self, env):
        try:
            self.github_repo_git_url = env['GITHUB_REPO_GIT_URL']
            m = re.match(r'git://github.com/(.+/.+)\.git',
                         self.github_repo_git_url)
            self.github_repo = m.group(1)
            self.github_branch_name = env['GITHUB_BRANCH_NAME']
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
