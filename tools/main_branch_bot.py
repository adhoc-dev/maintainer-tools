# License AGPLv3 (http://www.gnu.org/licenses/agpl-3.0-standalone.html)
# Copyright (c) 2016-2018 ACSONE SA/NV
import os
from os.path import join as opj
import subprocess
import sys
import traceback

import click

from .oca_projects import (
    get_repositories_and_branches, temporary_clone, MAIN_BRANCHES,
)
from .dist_to_simple_index import dist_to_simple_index


def _get_python(branch, python2):
    version = tuple(map(int, branch.split('.')))
    if version < (11, 0):
        return python2
    elif sys.version_info[0] == 3:
        return sys.executable
    else:
        return 'python3'


@click.command()
@click.option('--target', required=True,
              type=click.Path(dir_okay=True, file_okay=False, exists=True),
              help="Root of a PEP 503 directory structure.")
@click.option('--repo',
              help="Repo to act on (default all OCA addons repos).")
@click.option('--branch',
              help="Branch to act on (default all branches from 8.0).")
@click.option('--push/--no-push',
              help="Git commit and push changes made.")
@click.option('--python2', default='python2',
              help="Python 2 executable to use when building python 2 "
                   "wheels for branches < 11.0")
def main(target, repo, branch, push, python2):
    """ OCA Git Bot for main addon branches

    \b
    - generate README.rst from readme/*.rst fragments
    - generate default setup.py
    - generate sdists and wheels to a PEP 503 directory

    Branches before 8.0 are ignored.
    """
    exit_code = 0
    target = os.path.abspath(target)
    repos = ()
    if repo:
        repos = (repo, )
    branches = MAIN_BRANCHES
    if branch:
        branches = (branch, )
    for repo, branch in get_repositories_and_branches(repos, branches):
        if branch in ('6.1', '7.0'):
            continue
        with temporary_clone(repo, branch):
            try:
                # update addons table in README.md
                sys.stderr.write(
                    "============> updating addons table in %s@%s\n" %
                    (repo, branch)
                )
                subprocess.check_call(['oca-gen-addons-table', '--commit'])
                # generate README.rst
                sys.stderr.write(
                    "============> oca-gen-addon-readme in %s@%s\n" %
                    (repo, branch),
                )
                gen_addon_readme_cmd = [
                    'oca-gen-addon-readme',
                    '--repo-name', repo,
                    '--branch', branch,
                    '--addons-dir', '.',
                ]
                if push:
                    gen_addon_readme_cmd.append('--commit')
                subprocess.check_call(gen_addon_readme_cmd)
                # generate default setup.py
                sys.stderr.write(
                    "============> setuptools-odoo-make-default in %s@%s\n" %
                    (repo, branch),
                )
                make_default_setup_cmd = [
                    'setuptools-odoo-make-default',
                    '--addons-dir', '.',
                    '--metapackage', 'oca-' + repo,
                    '--clean',
                ]
                if push:
                    make_default_setup_cmd.append('--commit')
                subprocess.check_call(make_default_setup_cmd)
                # push changes to git, if any
                if push:
                    sys.stderr.write(
                        "============> git push in %s@%s\n" %
                        (repo, branch),
                    )
                    subprocess.check_call([
                        'git', 'push', 'origin', branch,
                    ])
                # make dists and wheels for each installable addon
                # and _metapackage
                sys.stderr.write(
                    "============> dist_to_simple_index in %s@%s\n" %
                    (repo, branch),
                )
                setup_dirs = [opj('setup', d) for d in os.listdir('setup')]
                dist_to_simple_index(
                    target, setup_dirs,
                    # use the right python to generate wheels
                    python=_get_python(branch, python2),
                )
            except Exception:
                exit_code = 1
                sys.stderr.write(
                    "/!\\ exception in %s@%s\n" %
                    (repo, branch),
                )
                traceback.print_exc()
    sys.exit(exit_code)
