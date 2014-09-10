# !/usr/bin/env python
# this plugins check sha on github and update ospy file from github

from threading import Thread
from random import randint

import web, json, re, time
import subprocess
import gv # Get access to ospy's settings
import urllib, urllib2
import os.path

from urls import urls # Get access to ospy's URLsimport errno
from ospy import template_render
from webpages import ProtectedPage

from gpio_pins import * # Provides access to GPIO pins

# Add a new url to open the data entry page.
urls.extend(['/UPl', 'plugins.system_update.loading', '/UPu', 'plugins.system_update.update', '/UPr', 'plugins.system_update.reboot'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['System update', '/UPl'])


################################################################################
# git hub user                                                                 #
################################################################################

user = 'martinpihrt' #Rimco, Dan-in-CA etd...
    
################################################################################
# Main function loop:                                                          #
################################################################################

class SystemUpdate(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
        self.status = ''

        self._sleep_time = 0

    def add_status(self, msg):
        if self.status:
            self.status += '\n' + msg
        else:
            self.status = msg
        print msg

    def update(self):
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def run(self):
        time.sleep(randint(3, 10)) # Sleep some time to prevent printing before startup information
        print "System plugin is active"
      
        while True:
            try:
                self._sleep(1)
                

            except Exception as err:
                self.add_status('System plugin encountered error: ' + str(err))
                self._sleep(60)

checker = SystemUpdate()
        	
################################################################################
# Helper functions:                                                            #
################################################################################

def get_rev_data():
    """Returns the update revision data."""
    statusmsg = ''
    current = ''
    latest = ''
    err = ''

    try:
       datagit = urllib2.urlopen("https://api.github.com/repos/"+user+"/OSPy/git/refs/heads/master")
       datagit = json.load(datagit)
       latest = datagit['object']['sha']
       err = '1'
    except:
       latest = '----------------------------------------------------------------------'
       err = '0'

    try:
        if os.path.isfile(".git/FETCH_HEAD"):
           with open(".git/FETCH_HEAD", "r") as f:
              data = f.read()
           f.closed
           current = re.search("\w{40}", data)
           current = current.group(0)
    except:
        current = ''

    
    if err == '1':
        if latest == current: # if sha local = sha latest
              statusmsg = 'Ready - Using the latest version.'
        elif current == '':
              statusmsg = 'You must first click RUN UPDATE button.'
        else:
              statusmsg = 'On the server is a new version.'

    else:
        statusmsg = 'Error: no connection to server github.'

    dataup = {'latest': latest, 'current': current, 'ver': gv.ver_str, 'revdate': gv.ver_date, 'status': statusmsg, 'user': user}
    return dataup  
    
################################################################################
# Web pages:                                                                   #
################################################################################

class loading(ProtectedPage):
    """Load an html page rev data."""
    def GET(self):
        return template_render.system_update(get_rev_data()) 
        
class update(ProtectedPage):
    """Update OSPi from github and return text message from comm line."""
    def GET(self):
        dataup = get_rev_data()
        command = "git config core.filemode false" # http://superuser.com/questions/204757/git-chmod-problem-checkout-screws-exec-bit
                                                   # ignore local chmod permission 
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        command = "git pull"                       
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        print "Update plugin reports: ",output
        dataup['status'] = output
        return template_render.system_update(dataup)
        raise web.seeother('/UPl')

class reboot(ProtectedPage):
    """Reboot system."""
    def GET(self):
        gv.srvals = [0]*(gv.sd['nst'])
        set_output()
        print "The OSPy system now reboots after update"
        command = "/etc/init.d/ospy.sh restart"
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        print "Update plugin reports: ",output
        raise web.seeother('/')
               
