#!/usr/bin/env python
# This plugin read data (temp or voltage) from I2C PCF8591 on adress 0x48. For temperature probe use LM35D

from threading import Thread
from random import randint

import web, json, re, os, time
import gv # Get access to ospi's settings

from urls import urls # Get access to ospi's URLs
from ospy import template_render
from webpages import ProtectedPage

import errno

import smbus # for PCF 8591

# I2C bus Rev Raspi RPI=1 rev1 RPI=0 rev0 
try:
   ADC = smbus.SMBus(1)
except ImportError:
   ADC = smbus.SMBus(0)
   pass

# Add a new url to open the data entry page.
urls.extend(['/pcf', 'plugins.pcf_8591_adj.settings', '/pcfj', 'plugins.pcf_8591_adj.settings_json', '/pcfa', 'plugins.pcf_8591_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['PCF8591 voltage and temperature adjustments ', '/pcf'])

################################################################################
# Main function loop:                                                          #
################################################################################

class PCFSender(Thread):
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
        print "PCF plugin is active"
        
        while True:
            try:
                datapcf = get_pcf_options()                          # load data from file
                if datapcf['use_pcf'] != 'off':                      # if pcf plugin is enabled
                    print "test"
                    if datapcf['use_log'] != 'off':                  # if log is enabled
                    print "test"
                                        
                                      
                else: # if not enabled plugin
                     self.status = '' 
                     self.add_status('PCF plugin not enabled.')

                self._sleep(4)   

            except Exception as err:
                self.status = '' 
                self.add_status('PCF plugin encountered error: ' + str(err))
                self._sleep(5)  
 
checker = PCFSender()

################################################################################
# Helper functions:                                                            #
################################################################################

def get_measure(AD_pin):
    """return voltage from A/D PCF8591"""
    try:
       ADC.write_byte_data(0x48, (0x40 + AD_pin),AD_pin)
       involt = ADC.read_byte(0x48)
       data = round(((involt*3.3)/255), 1)
       return data
    except:
       return 0.0

def get_write_DA(Y): # PCF8591 D/A converter Y=(0-255) for future use
    ADC.write_byte_data(0x48, 0x40,Y)
     

def get_pcf_options():
    """Returns the data form file."""
    datapcf = {
              'use_pcf': 'off',
              'use_log': 'off',
              'time': '0',
              'ad0': 'off',
              'ad1': 'off',
              'ad2': 'off',
              'ad3': 'off',
              'ad0text': 'probe_1',
              'ad1text': 'probe_2',
              'ad2text': 'probe_3',
              'ad3text': 'probe_4',
              'ad0val': get_measure(0),
              'ad1val': get_measure(1),
              'ad2val': get_measure(2),
              'ad3val': get_measure(3),
              'status': checker.status
              }
    try:
        with open('./data/pcf_adj.json', 'r') as f: # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in datapcf:
                datapcf[key] = value
    except Exception:
        pass
    
    return datapcf

################################################################################
# Web pages:                                                                   #
################################################################################
 
class settings(ProtectedPage):
    """Load an html page for entering lcd adjustments."""
    def GET(self):
        return template_render.pcf_8591_adj(get_pcf_options())

class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_pcf_options())

class update(ProtectedPage):
    """Save user input to pcf_adj.json file."""
    def GET(self):
        qdict = web.input()
        if not qdict.has_key('use_pcf'):
            qdict['use_pcf'] = 'off'              
        if not qdict.has_key('use_log'):
            qdict['use_log'] = 'off'
        if not qdict.has_key('ad0'):
            qdict['ad0'] = 'off'
        if not qdict.has_key('ad1'):
            qdict['ad1'] = 'off'
        if not qdict.has_key('ad2'):
            qdict['ad2'] = 'off'
        if not qdict.has_key('ad3'):
            qdict['ad3'] = 'off'
        with open('./data/pcf_adj.json', 'w') as f: # write the settings to file
            json.dump(qdict, f)
        checker.update()
        raise web.seeother('/')

class pcf_log(ProtectedPage):
    """Simple PCF Log API"""

    def GET(self):
        records = read_log()
        data = "Date, Start Time, Zone, Duration, Program\n"
        for r in records:
            event = json.loads(r)
            data += event["date"] + ", " + event["start"] + ", " + str(event["station"]) + ", " + event[
                "duration"] + ", " + event["program"] + "\n"

        web.header('Content-Type', 'text/csv')
        return data
