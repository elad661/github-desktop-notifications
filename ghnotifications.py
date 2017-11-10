#! /usr/bin/env python3
# ghnotifications.py - Polls notifications from GitHub and sends them to libnotify
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

import configparser
import gi
import os
import github3
import webbrowser
gi.require_version("Notify", "0.7")
from gi.repository import GLib, Notify

APP_SHORTNAME = "github-desktop-notifications"
DEFAULT_POLL_INTERVAL = 90


class Notifier(object):
    def __init__(self, username, token):
        self.username = username
        self.token = token
        self.github = github3.login(username, token=token)
        self.polling_interval = DEFAULT_POLL_INTERVAL
        self.seen_notifications = {}
        self.active_notifications = set()
        Notify.init(APP_SHORTNAME)

    def notification_callback(self, notification, action, userdata):
        """ Callback for desktop notification click """
        self.active_notifications.remove(notification)
        webbrowser.open(userdata['url'])

    def notify(self, gh_notification):
        if gh_notification.id in self.seen_notifications:
            print("yes")
            seen = self.seen_notifications[gh_notification.id]
            print(seen)
            print(gh_notification.updated_at)
            if gh_notification.updated_at <= seen:
                print("ignored")
                return  # Ignore seen notifications

        self.seen_notifications[gh_notification.id] = gh_notification.updated_at

        repo = gh_notification.repository.full_name
        subject = gh_notification.subject['title']
        issue_id = gh_notification.subject['url'].split('/')[-1]
        issue = self.github.issue(gh_notification.repository.owner,
                                  gh_notification.repository.name,
                                  issue_id)
        url = issue.html_url
        comment = sorted(issue.comments(), key=lambda c: c.created_at, reverse=True)[0]
        comment_from = comment.user.login
        comment_body = comment.body[:140]
        if len(comment.body) > 140:
            comment_body += '…'

        notification_title = f"{repo} #{issue_id} - {subject}"
        body = f"Status: <b>{issue.state}</b>\n" +\
                f"Last comment from: {comment_from}\n" +\
                f"\n{comment_body}"

        notification = Notify.Notification.new(notification_title, body)
        notification.add_action("default", "open", self.notification_callback, {"url": url})
        notification.show()
        # Need to keep the reference to the notification,
        # otherwise it will be grabage collected and the callback won't fire
        self.active_notifications.add(notification)

    def poll_github(self):
        """ Poll github for new notifications """
        notification_iterator = self.github.notifications(participating=True)
        for notification in notification_iterator:
            self.notify(notification)

        # figure out if we need to change our polling interval
        interval = int(notification_iterator.last_response.headers['X-Poll-Interval'])
        if interval > DEFAULT_POLL_INTERVAL:
            # slower polling requested by server, change our interval
            self.polling_interval = interval
            self.start_polling()
            return False  # return False to clear the current timeout

        if interval < self.polling_interval and DEFAULT_POLL_INTERVAL >= interval:
            # server allowed for more frequent polling, change our interval
            self.polling_interval = interval
            self.start_polling()
            return False  # return False to clear the current timeout

        return True

    def start_polling(self):
        GLib.timeout_add_seconds(self.polling_interval, self.poll_github)


def main():
    configfile = f"{APP_SHORTNAME}.conf"
    if 'XDG_CONFIG_HOME' in os.environ:
        configdir = os.environ['XDG_CONFIG_HOME']
    else:
        configdir = os.path.expanduser(os.path.join('~', '.config'))
    configfile = os.path.join(configdir, configfile)

    config = configparser.ConfigParser()
    config.read(configfile)

    username = config[APP_SHORTNAME]['username']
    token = config[APP_SHORTNAME]['token']

    notifier = Notifier(username, token)
    notifier.poll_github()
    notifier.start_polling()

    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()
