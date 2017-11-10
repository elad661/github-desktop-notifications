#! /usr/bin/env python3
# install.py - install github-desktop-notifications
#
# Copyright (C) 2017 Elad Alfassa <elad@fedoraproject.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import github3
import os
import os.path
import configparser
from gi.repository import Gio
from getpass import getuser, getpass

APP_SHORTNAME = "github-desktop-notifications"
APP_NAME = "Desktop Notifications for GitHub"
APP_URL = "https://github.com/elad661/github-desktop-notifications"
SCOPES = ['notifications', 'repo', 'user']


def twofactor():
    """ Request a 2-Factor-Authentication code """
    code = ''
    while not code:
        code = input('2FA code: ')
    return code


def login():
    """ Log in to GitHub """
    default_user = getuser()
    user = input(f"GitHub Username [{default_user}]: ") or default_user
    password = ''
    while not password:
        password = getpass('Password for {0}: '.format(user))

    auth = github3.authorize(user, password, SCOPES, APP_NAME, APP_URL,
                             two_factor_callback=twofactor)

    gh = github3.login(token=auth.token)
    print(f"Successfully logged in as {gh.me().name}")

    return user, auth.token


def main():
    print(f"Installing {APP_NAME}.")
    print("Log in to your github account")

    username, token = login()

    configfile = f"{APP_SHORTNAME}.conf"
    if 'XDG_CONFIG_HOME' in os.environ:
        configdir = os.environ['XDG_CONFIG_HOME']
    else:
        configdir = os.path.expanduser(os.path.join('~', '.config'))
    configfile = os.path.join(configdir, configfile)

    config = configparser.ConfigParser()
    config.add_section(APP_SHORTNAME)
    config.set(APP_SHORTNAME, "username", username)
    config.set(APP_SHORTNAME, "token", token)

    with open(configfile, "w") as f:
        config.write(f)

    print(f"Config file saved: {configfile}")
    with open(f"{APP_SHORTNAME}.desktop.in", "r") as f:
        autorun_template = f.read()

    path = os.path.join(os.path.dirname(__file__), "ghnotifications.py")
    path = f"/usr/bin/env python3 {path}"
    autorun = autorun_template.format(PATH=path)

    autorun_dir = os.path.join(configdir, "autostart")
    autorun_file = os.path.join(autorun_dir, f"{APP_SHORTNAME}.desktop")

    with open(autorun_file, "w") as f:
        f.write(autorun)

    print(f"Installed autorun file to {autorun_dir}.")
    print("Installation complete. Starting notification watcher")
    launcher = Gio.DesktopAppInfo.new_from_filename(autorun_file)
    launcher.launch()

if __name__ == "__main__":
    main()
