#!/usr/bin/python
# -*- coding: utf-8 -*-

# this plugin checks sha on github and updates SIP from github

import time
import subprocess
import sys
import traceback
import json

import web
import gv  # Get access to SIP's settings
from urls import urls  # Get access to SIP's URLsimport errno
from sip import template_render
from webpages import ProtectedPage
from helpers import restart

# Add a new url to open the data entry page.
urls.extend(['/UPs', 'plugins.system_update.status_page',
             '/UPu', 'plugins.system_update.update_page'
             ])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append([_('System update'), '/UPs'])


class StatusChecker():
    def __init__(self):

        self.status = {
            'ver_str': gv.ver_str,
            'ver_date': gv.ver_date,
            'status': '',
            'remote': 'None!',
            'can_update': False}

        self._sleep_time = 0

    def add_status(self, msg):
        if self.status['status']:
            self.status['status'] += '\n' + msg
        else:
            self.status['status'] = msg
#        print msg #  For testing

    def update(self):
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def update_rev_data(self):
        """Returns the update revision data."""

        command = 'git remote update'
        subprocess.call(command.split())

        command = 'git config --get remote.origin.url'
        remote = subprocess.check_output(command.split()).strip()
        if remote:
            self.status['remote'] = remote

        command = 'git log -1 origin/master --format=%cd --date=short'
        new_date = subprocess.check_output(command.split()).strip()

        command = 'git rev-list origin/master --count'
        new_revision = int(subprocess.check_output(command.split()))

        command = 'git log HEAD..origin/master --oneline'
        changes = '  ' + '\n  '.join(subprocess.check_output(command.split()).split('\n'))

        if new_revision == gv.revision and new_date == gv.ver_date:
            self.add_status(_('Up-to-date.'))
            self.status['can_update'] = False
        elif new_revision > gv.revision:
            self.add_status(_('New version is available!'))
            self.add_status(_('Available revision')+': %d.%d.%d (%s)' % (gv.major_ver, gv.minor_ver, new_revision - gv.old_count, new_date))
            self.add_status(_('Changes')+':\n' + changes)
            self.status['can_update'] = True
        else:
            self.add_status(_('Currently running revision')+': %d (%s)' % ((gv.revision - gv.old_count), gv.ver_date))
            self.add_status(_('Available revision')+': %d (%s)' % ((new_revision - gv.old_count), new_date))
            self.status['can_update'] = False

    def run(self):

        try:
            self.status['status'] = ''

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.add_status(_('System update plug-in encountered error')+':\n' + err_string)

checker = StatusChecker()

################################################################################
# Helper functions:                                                            #
################################################################################


def perform_update():

    command = "git config core.filemode true"
    subprocess.call(command.split())
    
    command = "git pull"
    subprocess.call(command.split())

#     command = "git checkout master"  # Make sure we are on the master branch
#     output = subprocess.check_output(command.split())

#     command = "git stash"  # stash any local changes
#     output = subprocess.check_output(command.split())

#     command = "git fetch --prune"
#     output = subprocess.check_output(command.split())
# 
#     command = "git merge -X theirs origin/master"
#     output = subprocess.check_output(command.split())
# 
#     command = "rm sessions/*"
#     subprocess.call(command.split())


#    print 'Update result:', output #  For testing

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
        raise web.seeother('/restart')

