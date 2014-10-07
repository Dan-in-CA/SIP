# !/usr/bin/env python
# this plugins send and check SMS data for modem to control your ospi

from threading import Thread
from random import randint
import json
import time
import sys
import traceback

import web
import gv  # Get access to ospi's settings
from helpers import get_ip, uptime, reboot, poweroff, timestr, jsave, restart
from urls import urls  # Get access to ospi's URLs
from ospi import template_render
from webpages import ProtectedPage


# Add a new url to open the data entry page.
urls.extend(['/smsa', 'plugins.sms_adj.settings',
             '/smsj', 'plugins.sms_adj.settings_json',
             '/usmsa', 'plugins.sms_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['SMS Settings', '/smsa'])

# Plugin system will catch the following error and disable the plugin automatically:
import gammu  # for SMS modem import gammu
# if no install modem and gammu visit: http://www.pihrt.com/elektronika/259-moje-rapsberry-pi-sms-ovladani-rpi
# USB modem HUAWEI E303 + SIM card with telephone provider

################################################################################
# Main function loop:                                                          #
################################################################################


class SMS(Thread):
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
        print "SMS plugin is active"

        while True:
            try:
                #self.status = ''
                data = get_sms_options()
                if data["use_sms"] != "off":  # if use_sms is enable (on)
                    sms_check(self)  # Check SMS command from modem
                self._sleep(20)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('SMS plugin encountered error: ' + err_string)
                self._sleep(60)


checker = SMS()


################################################################################
# Helper functions:                                                            #
################################################################################

def get_sms_options():
    """Returns the data form file."""
    data = {
        'tel1': '+xxxyyyyyyyyy',
        'tel2': '+xxxyyyyyyyyy',
        'use_sms': 'off',
        'txt1': 'info',
        'txt2': 'stop',
        'txt3': 'start',
        'txt4': 'reboot',
        'txt5': 'poweroff',
        'txt6': 'update',
        'status': checker.status
    }

    try:
        with open('./data/sms_adj.json', 'r') as f:  # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in data:
                data[key] = value
    except Exception:
        pass

    return data


def sms_check(self):
    """Control and processing SMS"""
    data = get_sms_options()  # Load data from json file
    tel1 = data['tel1']
    tel2 = data['tel2']
    comm1 = data['txt1']
    comm2 = data['txt2']
    comm3 = data['txt3']
    comm4 = data['txt4']
    comm5 = data['txt5']
    comm6 = data['txt6']

    sm = gammu.StateMachine()
    sm.ReadConfig()
    try:
        sm.Init()
        print "Checking SMS..."
    except:
        print "Error: SMS modem fault"

    status = sm.GetSMSStatus()
    remain = status['SIMUsed'] + status['PhoneUsed'] + status['TemplatesUsed']
    sms = []
    start = True
    while remain > 0:
        if start:
            cursms = sm.GetNextSMS(Start=True, Folder=0)
            start = False
        else:
            cursms = sm.GetNextSMS(Location=cursms[0]['Location'], Folder=0)
        remain = remain - len(cursms)
        sms.append(cursms)
    data = gammu.LinkSMS(sms)
    for x in data:
        v = gammu.DecodeSMS(x)
        m = x[0]
        print '%-15s: %s' % ('Sender', m['Number'])
        print '%-15s: %s' % ('Date', str(m['DateTime']))
        print '%-15s: %s' % ('State', m['State'])
        print '%-15s: %s' % ('SMS command', m['Text'])
        if (m['Number'] == tel1) or (m['Number'] == tel2):  # If telephone is admin 1 or admin 2
            self.add_status(time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time())) + ' SMS from admin')
            if m['State'] == "UnRead":          # If SMS is unread
                if m['Text'] == comm1:           # If command = comm1 (info - send SMS to admin phone1 and phone2)
                    self.add_status('Command ' + comm1 + ' is processed')
                    if gv.lrun[1] == 98:
                        pgr = 'Run-once'
                    elif gv.lrun[1] == 99:
                        pgr = 'Manual'
                    else:
                        pgr = str(gv.lrun[1])
                    start = time.gmtime(gv.now - gv.lrun[2])
                    if pgr != '0':
                        logline = ' {program: ' + pgr + ',station: ' + str(gv.lrun[0]) + ',duration: ' + timestr(
                            gv.lrun[2]) + ',start: ' + time.strftime("%H:%M:%S - %Y-%m-%d", start) + '}'
                    else:
                        logline = ' Last program none'
                    revision = ' Rev: ' + gv.ver_date
                    datastr = ('On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(
                        time.time())) + '. Run time: ' + uptime() + ' IP: ' + get_ip() + logline + revision)
                    message = {
                        'Text': datastr,
                        'SMSC': {'Location': 1},
                        'Number': m['Number'],
                    }
                    sm.SendSMS(message)
                    self.add_status(
                        'Command: ' + comm1 + ' was processed and confirmation was sent as SMS to: ' + m['Number'])
                    self.add_status('SMS text: ' + datastr)

                    sm.DeleteSMS(m['Folder'], m['Location'])  # SMS deleted
                    self.add_status('Received SMS was deleted')

                elif m['Text'] == comm2:        # If command = comm2 (stop - system OSPi off)
                    self.add_status('Command ' + comm2 + ' is processed')
                    gv.sd['en'] = 0            # disable system OSPi
                    jsave(gv.sd, 'sd')         # save en = 0
                    message = {
                        'Text': 'Command: ' + comm2 + ' was processed',
                        'SMSC': {'Location': 1},
                        'Number': m['Number'],
                    }
                    sm.SendSMS(message)
                    self.add_status(
                        'Command: ' + comm2 + ' was processed and confirmation was sent as SMS to: ' + m['Number'])
                    sm.DeleteSMS(m['Folder'], m['Location'])
                    self.add_status('Received SMS was deleted')

                elif m['Text'] == comm3:         # If command = comm3 (start - system ospi on)
                    self.add_status('Command ' + comm3 + ' is processed')
                    gv.sd['en'] = 1             # enable system OSPi
                    jsave(gv.sd, 'sd')          # save en = 1
                    message = {
                        'Text': 'Command: ' + comm3 + ' was processed',
                        'SMSC': {'Location': 1},
                        'Number': m['Number'],
                    }
                    sm.SendSMS(message)
                    self.add_status(
                        'Command: ' + comm3 + ' was processed and confirmation was sent as SMS to: ' + m['Number'])
                    sm.DeleteSMS(m['Folder'], m['Location'])
                    self.add_status('Received SMS was deleted')

                elif m['Text'] == comm4:        # If command = comm4 (reboot system)
                    self.add_status('Command ' + comm4 + ' is processed')
                    message = {
                        'Text': 'Command: ' + comm4 + ' was processed',
                        'SMSC': {'Location': 1},
                        'Number': m['Number'],
                    }
                    sm.SendSMS(message)
                    self.add_status(
                        'Command: ' + comm4 + ' was processed and confirmation was sent as SMS to: ' + m['Number'])
                    sm.DeleteSMS(m['Folder'], m['Location'])
                    self.add_status('Received SMS was deleted and system is now reboot')
                    self._sleep(10)
                    reboot()                    # restart linux system

                elif m['Text'] == comm5:        # If command = comm5 (poweroff system)
                    self.add_status('Command ' + comm5 + ' is processed')
                    message = {
                        'Text': 'Command: ' + comm5 + ' was processed',
                        'SMSC': {'Location': 1},
                        'Number': m['Number'],
                    }
                    sm.SendSMS(message)
                    self.add_status(
                        'Command: ' + comm5 + ' was processed and confirmation was sent as SMS to: ' + m['Number'])
                    sm.DeleteSMS(m['Folder'], m['Location'])
                    self.add_status('Received SMS was deleted and system is now poweroff')
                    self._sleep(10)
                    poweroff()                  # poweroff linux system

                elif m['Text'] == comm6:        # If command = comm6 (update ospi system)
                    self.add_status('Command ' + comm6 + ' is processed')
                    message = {
                        'Text': 'Command: ' + comm6 + ' was processed',
                        'SMSC': {'Location': 1},
                        'Number': m['Number'],
                    }
                    sm.SendSMS(message)
                    self.add_status(
                        'Command: ' + comm6 + ' was processed and confirmation was sent as SMS to: ' + m['Number'])
                    try:
                        from plugins.system_update import perform_update

                        perform_update()
                        self.add_status('Received SMS was deleted, update was performed and program will restart')
                    except ImportError:
                        self.add_status('Received SMS was deleted, but could not perform update')

                    sm.DeleteSMS(m['Folder'], m['Location'])

                else:                            # If SMS command is not defined
                    sm.DeleteSMS(m['Folder'], m['Location'])
                    self.add_status('Received command ' + m['Text'] + ' is not defined!')

            else:                                # If SMS was read
                sm.DeleteSMS(m['Folder'], m['Location'])
                self.add_status('Received SMS was deleted - SMS was read')
        else:                          # If telephone number is not admin 1 or admin 2 phone number
            sm.DeleteSMS(m['Folder'], m['Location'])
            self.add_status('Received SMS was deleted - SMS was not from admin')


################################################################################
# Web pages:                                                                   #
################################################################################

class settings(ProtectedPage):
    """Load an html page for entering sms adjustments."""

    def GET(self):
        return template_render.sms_adj(get_sms_options())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_sms_options())


class update(ProtectedPage):
    """Save user input to sms_adj.json file."""

    def GET(self):
        qdict = web.input()
        if 'use_sms' not in qdict:
            qdict['use_sms'] = 'off'
        with open('./data/sms_adj.json', 'w') as f:  # write the settings to file
            json.dump(qdict, f)
        checker.update()
        raise web.seeother('/')
