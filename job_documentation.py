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

"""Jenkins script to generate documents for TizenFX"""

import os
import re
import sys
import global_configuration as conf
from common.shell import ShellError, sh
from common.project import Project, ProjectError, ProjectNotFoundException


def main():
    env = BuildEnvironment(os.environ)
    proj = Project(env)

    # 1. Get Version of TizenFX
    version = '{}.{}'.format(
        conf.VERSION_PREFIX_MAP[env.category], proj.commit_count + 10000)
    print('[VERSION] {}'.format(version))

    # 2. Restore Project
    proj.restore()

    # 3. Run DocFX
    sh('mono /usr/share/docfx/docfx.exe docs/docfx.json',
       cwd=proj.workspace)

    # 4. Make and push a commit to gh-pages branch
    set_git_configs(proj)
    sh('''
        git branch -f gh-pages origin/gh-pages
        git checkout gh-pages
        git pull --rebase origin gh-pages
        mkdir -p {github_branch}
        cp -fr Artifacts/docs/* {github_branch}/
        git add {github_branch}/
    '''.format(github_branch=env.github_branch_name), cwd=proj.workspace)
    modified = sh('git diff --cached --numstat | wc -l',
                  cwd=proj.workspace, return_stdout=True, print_stdout=False)
    if int(modified.strip()) > 0:
        sh('''
            git commit -m {version}
            git push "https://{userpass}@github.com/{github_repo}.git" gh-pages
        '''.format(version=version,
                   userpass=env.github_userpass, github_repo=env.github_repo))


def set_git_configs(proj):
    sh('''
        git config --local user.name "TizenAPI-Bot"
        git config --local user.email "tizenapi@samsung.com"
    ''', cwd=proj.workspace)


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
            self.github_userpass = env['GITHUB_USERPASS']
            self.github_branch_name = env['GITHUB_BRANCH_NAME']
            self.workspace = env['WORKSPACE']
            self.version = str()
            self.category = conf.BRANCH_API_LEVEL_MAP[self.github_branch_name]
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
