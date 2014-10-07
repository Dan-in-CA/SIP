#!/usr/bin/env python
# This plugin read data (temp or voltage) from I2C PCF8591 on adress 0x48. For temperature probe use LM35D. Power for PCF8591 or LM35D is 5V dc! no 3.3V dc

from threading import Thread
from random import randint
import json
import time
import sys
import traceback

import web
import gv  # Get access to ospi's settings
from urls import urls  # Get access to ospi's URLs
from ospi import template_render
from webpages import ProtectedPage
from helpers import get_rpi_revision

# I2C bus Rev Raspi RPI=1 rev1 RPI=0 rev0 
try:
    import smbus  # for PCF 8591
    ADC = smbus.SMBus(1 if get_rpi_revision() >= 2 else 0)
except ImportError:
    ADC = None

# Add a new url to open the data entry page.
urls.extend(['/pcf', 'plugins.pcf_8591_adj.settings',
             '/pcfj', 'plugins.pcf_8591_adj.settings_json',
             '/pcfa', 'plugins.pcf_8591_adj.update',
             '/pcfl', 'plugins.pcf_8591_adj.pcf_log',
             '/pcfr', 'plugins.pcf_8591_adj.delete_log'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['PCF8591 voltage and temperature settings ', '/pcf'])

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
        time.sleep(randint(3, 10))  # Sleep some time to prevent printing before startup information
        print "PCF8591 plugin is active"
        last_time = gv.now

        while True:
            try:
                datapcf = get_pcf_options()                          # load data from file
                if datapcf['use_pcf'] != 'off':                      # if pcf plugin is enabled
                    if datapcf['use_log'] != 'off' and datapcf['time'] != '0':  # if log is enabled and time is not 0 min
                        actual_time = gv.now
                        if actual_time - last_time > (int(datapcf['time']) * 60):       # if is time for save
                            ad0 = get_now_measure(1)
                            ad1 = get_now_measure(2)
                            ad2 = get_now_measure(3)
                            ad3 = get_now_measure(4)
                            if datapcf['ad0'] != 'off': 
                               ad0 = get_volt(ad0)
                            else:
                               ad0 = get_temp(ad0)
                            if datapcf['ad1'] != 'off': 
                               ad1 = get_volt(ad1)
                            else:
                               ad1 = get_temp(ad1)
                            if datapcf['ad2'] != 'off': 
                               ad2 = get_volt(ad2)
                            else:
                               ad2 = get_temp(ad2)
                            if datapcf['ad3'] != 'off': 
                               ad3 = get_volt(ad3)
                            else:
                               ad3 = get_temp(ad3)
                            last_time = actual_time
                            self.status = ''
                            TEXT = 'On ' + time.strftime('%d.%m.%Y at %H:%M:%S', time.localtime(time.time())) + \
                                   ' save PCF8591 data AD0=' + str(ad0) + \
                                   ' AD1=' + str(ad1) + \
                                   ' AD2=' + str(ad2) + \
                                   ' AD3=' + str(ad3)
                            self.add_status(TEXT)
                            write_log(ad0, ad1, ad2, ad3)
                
                out_val = datapcf['da0val']  
                get_write_DA(int(out_val)) # send to DA 0 output value 0-255 -> 0-5V 
               
                self._sleep(1)
               
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('PCF plugin encountered error: ' + err_string)
                self._sleep(5)

checker = PCFSender()

################################################################################
# Helper functions:                                                            #
################################################################################

def get_volt(data):
    """Return voltage 0-5.0V from number"""
    volt = (data*5.0)/255
    volt = round(volt,1)
    return volt

def get_temp(data):
    """Return temperature 0-100C from data"""
    temp = ((data*5.0)/255)*100.0
    temp = round(temp,1)
    return temp

def get_now_measure(AD_pin):
    """Return number 0-255 from A/D PCF8591 to webpage"""
    ADC.write_byte_data(0x48, (0x40 + AD_pin), AD_pin)
    return ADC.read_byte(0x48)  

def get_write_DA(Y):  # PCF8591 D/A converter Y=(0-255) for future use
    """Write analog voltage to output"""
    ADC.write_byte_data(0x48, 0x40, Y)

def get_pcf_options():
    """Returns the data form file."""
    datapcf = {
        'use_pcf': 'off',
        'use_log': 'off',
        'time': '0',
        'records': '0',
        'ad0': 'off',
        'ad1': 'off',
        'ad2': 'off',
        'ad3': 'off',
        'ad0text': 'label_1',
        'ad1text': 'label_2',
        'ad2text': 'label_3',
        'ad3text': 'label_4',
        'ad0val': get_now_measure(1),
        'ad1val': get_now_measure(2),
        'ad2val': get_now_measure(3),
        'ad3val': get_now_measure(4),
        'da0val': '0', 
        'status': checker.status
    }
    try:
        with open('./data/pcf_adj.json', 'r') as f:  # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in datapcf:
                datapcf[key] = value
    except Exception:
        pass

    return datapcf


def read_log():
    """Read pcf log"""
    try:
        with open('./data/pcflog.json') as logf:
            records = logf.readlines()
        return records
    except IOError:
        return []


def write_log(ad0, ad1, ad2, ad3):
    """Add run data to csv file - most recent first."""
    datapcf = get_pcf_options()
    logline = '{"Time":"' + time.strftime('%H:%M:%S","Date":"%d-%m-%Y"', time.gmtime(gv.now)) + ',"AD0":"' + str(
        ad0) + '","AD1":"' + str(ad1) + '","AD2":"' + str(ad2) + '","AD3":"' + str(ad3) + '"}\n'
    log = read_log()
    log.insert(0, logline)
    with open('./data/pcflog.json', 'w') as f:
        if int(datapcf['records']) != 0:
            f.writelines(log[:int(datapcf['records'])])
        else:
            f.writelines(log)
    return

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
        if 'use_pcf' not in qdict:
            qdict['use_pcf'] = 'off'
        if 'use_log' not in qdict:
            qdict['use_log'] = 'off'
        if 'ad0' not in qdict:
            qdict['ad0'] = 'off'
        if 'ad1' not in qdict:
            qdict['ad1'] = 'off'
        if 'ad2' not in qdict:
            qdict['ad2'] = 'off'
        if 'ad3' not in qdict:
            qdict['ad3'] = 'off'
        with open('./data/pcf_adj.json', 'w') as f:  # write the settings to file
            json.dump(qdict, f)
        checker.update()
        raise web.seeother('/')


class pcf_log(ProtectedPage):  # save log file from web as csv file type
    """Simple PCF Log API"""

    def GET(self):
        records = read_log()
        data = "Date, Time, AD0, AD1, AD2, AD3\n"
        for r in records:
            event = json.loads(r)
            data += event["Date"] + ", " + event["Time"] + ", " + str(event["AD0"]) + ", " + str(
                event["AD1"]) + ", " + str(event["AD2"]) + ", " + str(event["AD3"]) + ", " + "\n"
        web.header('Content-Type', 'text/csv')
        return data


class delete_log(ProtectedPage):  # delete log file from web
    """Delete all pcflog records"""

    def GET(self):
        qdict = web.input()
        with open('./data/pcflog.json', 'w') as f:
            f.write('')
        raise web.seeother('/pcf')


