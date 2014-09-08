# !/usr/bin/env python
# this plugins send email at google email

from threading import Thread
from random import randint

import web, json, re, time
import os
import gv # Get access to ospy's settings

from urls import urls # Get access to ospy's URLs
import errno

from ospy import template_render
from webpages import ProtectedPage
from helpers import email, timestr 

# Add a new url to open the data entry page.
urls.extend(['/emla', 'plugins.email_adj.settings', '/emlj', 'plugins.email_adj.settings_json', '/uemla', 'plugins.email_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Email adjust settings', '/emla'])
    
################################################################################
# Main function loop:                                                          #
################################################################################

class EmailSender(Thread):
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
        print "Email plugin is active"
        SUBJ = "Reporting from OSPy" # Subject in email
        log = 1 # send email only 1x
        rain = 0    
        norain = 0  
        last = 0    

        while True:
            try:
                #self.status = ''
                dataeml = get_email_options() # load data from file
                # send if power on
                if dataeml["emllog"] != "off":          # if eml_log send email is enable (on)
                    if (log == 1):                       # only if plugin run 1x (power on)        
                       TEXT = ('On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time())) + ' System was powered on.')
                       email(dataeml['emladr'],SUBJ,TEXT,"/home/pi/OSPy/data/log.json",dataeml['emlusr'],gv.sd['name'],dataeml['emlpwd'])        # send email with attachments from /home/pi/OSPi/data/log.json
                       if email:
                          log = 0
                          self.status = ''
                          self.add_status('Email was send: ' + TEXT)
                          self._sleep(1)                                    
                       else:
                          self.status = ''
                          self.add_status('Email was not send: connection error.')
                          self._sleep(1) 
                
                # send if rain detected
                if gv.sd['rs'] == 0:		      # if rain sensed is inactive emlrain is enabled
                    norain = 1
                if gv.sd['rs'] == 1:
                    rain = 1
                if dataeml["emlrain"] != "off":            # if eml_rain send email is enable (on)
                    if (rain == 1) and (norain == 1):      # send email only 1x if  gv.sd rs change
                        if gv.sd['rs'] and gv.sd['urs']:   # if rain sensed and use rain sensor
                              TEXT = ('On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time())) + ' System detected rain.')
                              email(dataeml['emladr'],SUBJ,TEXT,"",dataeml['emlusr'],gv.sd['name'],dataeml['emlpwd'])     # send email without attachments
                              if email:
                                  norain = 0
                                  rain = 0
                                  self.add_status('Email was send: ' + TEXT)
                                  self._sleep(1)
                              else:
                                  self.status = ''
                                  self.add_status('Email was not send: connection error.')
                                  self._sleep(1)

                if dataeml["emlrun"] != "off":            # if eml_rain send email is enable (on)   
                   state = ''            
                   for b in range(gv.sd['nbrd']): # Check each station once a second
                      for s in range(8):
                         sid = b*8 + s # station index
                         if gv.srvals[sid]: # if this station is on
                            last = 1  
                            state = 'on' 
                  
                   if last == 1 and  state != 'on':   
                      last = 2         
                      pgr = ''
                      if gv.lrun[1] == 98:
                         pgr = 'Run-once'
                      elif gv.lrun[1] == 99:
                         pgr = 'Manual'
                      else:
                         pgr = str(gv.lrun[1])

                      dur = str(timestr(gv.lrun[2]))
                      start = time.gmtime(gv.now - gv.lrun[2])

                      TEXT = 'On '+time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time()))+' System last run: '+'Station '+str(gv.lrun[0])+', Program '+pgr+', Duration '+dur+', Start time '+ time.strftime("%d.%m.%Y at %H:%M:%S", start)
                      email(dataeml['emladr'],SUBJ,TEXT,"",dataeml['emlusr'],gv.sd['name'],dataeml['emlpwd'])     # send email without attachments
                      if email:
                         last = 0 # send is ok
                         self.add_status('Email was send: ' + TEXT)
                         self._sleep(1)
                      else:
                         self.status = ''
                         self.add_status('Email was not send: connection error.')
                         self._sleep(1)
                         last = 1 # send repeat
    
                self._sleep(1)

            except Exception as err:
                self.add_status('Email plugin encountered error: ' + str(err))
                self._sleep(60)

checker = EmailSender()
        	
################################################################################
# Helper functions:                                                            #
################################################################################

	   
def get_email_options():
    """Returns the defaults data form file."""
    dataeml = {
        	'emlusr': 'username',
        	'emlpwd': '',
        	'emladr': 'adr@dom.com',
        	'emllog': 'off',
        	'emlrain': 'off',
        	'emlrun': 'off',
        	'status': checker.status
        	}
    try:
        with open('./data/email_adj.json', 'r') as f: # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in dataeml:
                dataeml[key] = value
    except Exception:
        pass
   
    return dataeml

################################################################################
# Web pages:                                                                   #
################################################################################

class settings(ProtectedPage):
    """Load an html page for entering email adjustments."""
    def GET(self):
        return template_render.email_adj(get_email_options())

class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_email_options())

class update(ProtectedPage):
    """Save user input to email_adj.json file."""
    def GET(self):
        qdict = web.input()
        if not qdict.has_key('emllog'):
            qdict['emllog'] = 'off'
        if not qdict.has_key('emlrain'):
            qdict['emlrain'] = 'off'
        if not qdict.has_key('emlrun'):
            qdict['emlrun'] = 'off'     
        with open('./data/email_adj.json', 'w') as f: # write the settings to file
            json.dump(qdict, f)
        checker.update()
        raise web.seeother('/')
