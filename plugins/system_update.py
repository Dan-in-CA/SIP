#!/usr/bin/python
# -*- coding: utf-8 -*-

# this plugin checks sha on github and updates SIP from github

# standard library imports
import json
import subprocess
import sys
import time
import traceback

# local module imports
import gv  # Get access to SIP's settings
from helpers import restart
from sip import template_render
from urls import urls  # Get access to SIP's URLsimport errno
import web
from webpages import ProtectedPage

# Add a new url to open the data entry page.
urls.extend([u"/UPs", u"plugins.system_update.status_page",
             u"/UPu", u"plugins.system_update.update_page"
             ])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append([_(u"System update"), u"/UPs"])


class StatusChecker():
    def __init__(self):

        self.status = {
            u"ver_str": gv.ver_str,
            u"ver_date": gv.ver_date,
            u"status": u"",
            u"remote": u"'None!",
            u"can_update": False}

        self._sleep_time = 0

    def add_status(self, msg):
        if self.status[u"status"]:
            self.status[u"status"] += u"\n" + msg
        else:
            self.status[u"status"] = msg

    def update(self):
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def update_rev_data(self):
        """Returns the update revision data."""

        command = u"git remote update"
        subprocess.call(command.split()) #  housekeeping, no retruned data needed.

        command = u"git config --get remote.origin.url"
        remote = subprocess.check_output(command.split()).strip()
        remote = remote.decode('utf-8')
        if remote:
            self.status[u"remote"] = remote

        command = u"git log -1 origin/master --format=%cd --date=short"
        new_date = subprocess.check_output(command.split()).strip()
        new_date = new_date.decode('utf-8')

        command = u"git rev-list origin/master --count"
        new_revision = int(subprocess.check_output(command.split()))

        command =u"git log HEAD..origin/master --oneline"
        log_H = (subprocess.check_output(command.split()))
        log_H = log_H.decode('utf-8').split(u"\n")
        changes = u"  " + u"\n  ".join(log_H)

        if new_revision == gv.revision and new_date == gv.ver_date:
            self.add_status(_(u"Up-to-date."))
            self.status[u"can_update"] = False
        elif new_revision > gv.revision:
            self.add_status(_(u"New version is available!"))
            self.add_status(_(u"Available revision") + u": %d.%d.%d (%s)" % (gv.major_ver, gv.minor_ver, new_revision - gv.old_count, new_date))
            self.add_status(_(u"Changes") + u":\n" + changes)
            self.status[u"can_update"] = True
        else:
            self.add_status(_(u"Currently running revision") + u": %d (%s)" % ((gv.revision - gv.old_count), gv.ver_date))
            self.add_status(_(u"Available revision") + u": %d (%s)" % ((new_revision - gv.old_count), new_date))
            self.status[u"can_update"] = False

    def run(self):

        try:
            self.status[u"status"] = u""

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err_string = u"".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.add_status(_(u"System update plug-in encountered error") + u":\n" + err_string)

checker = StatusChecker()

################################################################################
# Helper functions:                                                            #
################################################################################


def perform_update():

    command = u"git config core.filemode true"
    subprocess.call(command.split())
    
    command = u"git pull"
    subprocess.call(command.split())

################################################################################
# Web pages:                                                                   #
################################################################################


class status_page(ProtectedPage):
    """Load an html page with rev data."""

    def GET(self):
        checker.update_rev_data()
        return template_render.system_update(checker.status)

class update_page(ProtectedPage):
    """Update SIP from github and return text message from command line."""

    def GET(self):
        perform_update()
        raise web.seeother(u"/restart")

