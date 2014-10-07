# !/usr/bin/env python
# this plugins check sha on github and update ospi file from github

from threading import Thread, Event, Condition
from random import randint
import time
import subprocess
import sys
import traceback

import web
import gv  # Get access to ospi's settings
from urls import urls  # Get access to ospi's URLsimport errno
from ospi import template_render
from webpages import ProtectedPage
from helpers import restart


# Add a new url to open the data entry page.
urls.extend(['/UPs', 'plugins.system_update.status_page',
             '/UPsr', 'plugins.system_update.refresh_page',
             '/UPu', 'plugins.system_update.update_page',
             '/UPr', 'plugins.system_update.restart_page'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['System update', '/UPs'])


class StatusChecker(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
        self.started = Event()
        self._done = Condition()

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
        print msg

    def update_wait(self):
        self._done.acquire()
        self._sleep_time = 0
        self._done.wait(10)
        self._done.release()

    def update(self):
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def _update_rev_data(self):
        """Returns the update revision data."""

        command = 'git remote update'
        subprocess.call(command.split())

        command = 'git config --get remote.origin.url'
        remote = subprocess.check_output(command.split()).strip()
        if remote:
            self.status['remote'] = remote

        command = 'git log -1 origin/master --format=%cd --date=short'
        new_date = subprocess.check_output(command.split()).strip()

        command = 'git rev-list origin/master --count --first-parent'
        new_revision = int(subprocess.check_output(command.split()))

        command = 'git log HEAD..origin/master --oneline'
        changes = '  ' + '\n  '.join(subprocess.check_output(command.split()).split('\n'))

        if new_revision == gv.revision and new_date == gv.ver_date:
            self.add_status('Up-to-date.')
            self.status['can_update'] = False
        elif new_revision > gv.revision:
            self.add_status('New version is available!')
            self.add_status('Currently running revision: %d (%s)' % ((gv.revision - gv.old_count), gv.ver_date))
            self.add_status('Available revision: %d (%s)' % (new_revision, new_date))
            self.add_status('Changes:\n' + changes)
            self.status['can_update'] = True
        else:
            #  self.add_status('Running unknown version!')
            self.add_status('Currently running revision: %d (%s)' % ((gv.revision - gv.old_count), gv.ver_date))
            self.add_status('Available revision: %d (%s)' % ((new_revision - gv.old_count), new_date))
            self.status['can_update'] = False

        self._done.acquire()
        self._done.notify_all()
        self._done.release()

    def run(self):
        self._sleep(randint(3, 10))  # Sleep some time to prevent printing before startup information

        while True:
            try:
                self.status['status'] = ''
                self._update_rev_data()
                self.started.set()
                self._sleep(3600)

            except Exception:
                self.started.set()
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('System update plug-in encountered error:\n' + err_string)
                self._sleep(60)

checker = StatusChecker()

################################################################################
# Helper functions:                                                            #
################################################################################


def perform_update():
    # ignore local chmod permission
    command = "git config core.filemode false"  # http://superuser.com/questions/204757/git-chmod-problem-checkout-screws-exec-bit
    subprocess.call(command.split())

    command = "git pull"
    output = subprocess.check_output(command.split())

    print 'Update result:', output
    restart(3)

################################################################################
# Web pages:                                                                   #
################################################################################


class status_page(ProtectedPage):
    """Load an html page rev data."""

    def GET(self):
        checker.started.wait(10)    # Make sure we are initialized
        return template_render.system_update(checker.status)


class refresh_page(ProtectedPage):
    """Refresh status and show it."""

    def GET(self):
        checker.update_wait()
        raise web.seeother('/UPs')


class update_page(ProtectedPage):
    """Update OSPi from github and return text message from comm line."""

    def GET(self):
        perform_update()
        return template_render.restarting('/UPs')


class restart_page(ProtectedPage):
    """Restart system."""

    def GET(self):
        restart(3)
        return template_render.restarting('/UPs')
