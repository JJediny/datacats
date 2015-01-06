# Copyright 2014-2015 Boxkite Inc.

# This file is part of the DataCats package and is released under
# the terms of the GNU Affero General Public License version 3.0.
# See LICENSE.txt or http://www.fsf.org/licensing/licenses/agpl-3.0.html

import sys
from os.path import exists, abspath
from getpass import getpass

from datacats.project import Project, ProjectError
from datacats.cli.install import install

def write(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def create(project_name, port, bare, image_only, no_sysadmin, ckan):
    """
    Create a new DataCats project directory, init the data dir.
    Optionally start the web server and create an admin user.
    """
    try:
        project = Project.new(project_name, 'master', port)
    except ProjectError as e:
        print e
        return

    write('Creating project "{0}"'.format(project.name))
    steps = [
        project.create_directories,
        project.create_bash_profile,
        project.save,
        project.create_virtualenv,
        project.create_source,
        project.start_data_and_search,
        project.fix_storage_permissions,
        project.create_ckan_ini,
        lambda: project.update_ckan_ini(skin=not bare),
        project.fix_project_permissions,
        ]

    if not bare:
        steps.append(project.create_install_template_skin)

    steps.append(project.ckan_db_init)

    for fn in steps:
        fn()
        write('.')

    if not image_only:
        project.start_web()
        write('.\n')
        write('Site available at {0}\n'.format(project.web_address()))

    if not no_sysadmin:
        adminpw = confirm_password()
        project.create_admin_set_password(adminpw)

    if image_only:
        project.stop_data_and_search()
        write('.\n')


def init(project_dir, port, image_only):
    """
    Init the data dir for an existing project dir.
    Optionally start the web server.
    """
    project_dir = abspath(project_dir or '.')
    try:
        project = Project.load(project_dir)
        if port:
            project.port = int(port)
            project.save()
    except ProjectError as e:
        print e
        return

    write('Creating from existing project "{0}"'.format(project.name))
    steps = [
        lambda: project.create_directories(create_project_dir=False),
        project.create_virtualenv,
        project.start_data_and_search,
        project.fix_storage_permissions,
        project.fix_project_permissions,
        ]

    for fn in steps:
        fn()
        write('.')
    write('\n')

    install(project)

    write('Initializing database')
    project.ckan_db_init()
    write('\n')

    if image_only:
        project.stop_data_and_search()
    else:
        project.start_web()
        write('Site available at {0}\n'.format(project.web_address()))


def confirm_password():
    while True:
        p1 = getpass('admin user password:')
        if len(p1) < 4:
            print 'At least 4 characters are required'
            continue
        p2 = getpass('confirm password:')
        if p1 == p2:
            return p1
        print 'Passwords do not match'
