#!/usr/bin/env python
# this plugins check pressure in pipe if master station is switched on

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
from helpers import stop_stations


# Add a new url to open the data entry page.
urls.extend(['/pressa', 'plugins.pressure_adj.settings',
             '/pressj', 'plugins.pressure_adj.settings_json',
             '/upressa', 'plugins.pressure_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Pressure Monitor Settings', '/pressa'])

################################################################################
# GPIO input pullup:                                                           #
################################################################################

from gpio_pins import GPIO as GPIO

try:
    if gv.platform == 'pi':  # If this will run on Raspberry Pi:
        pin_pressure = 22
    elif gv.platform == 'bo':  # If this will run on Beagle Bone Black:
        pin_pressure = "P9_17"
except AttributeError:
    pass

try:
    GPIO.setup(pin_pressure, GPIO.IN, pull_up_down=GPIO.PUD_UP)
except NameError:
    pass


################################################################################
# Main function loop:                                                          #
################################################################################

class PressureSender(Thread):
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
        print "Pressure plugin is active"
        send = False
        SUBJ = "Reporting from ospi"  # Subject in email
        self.add_status('Waiting...')

        while True:
            try:
                datapressure = get_pressure_options()                             # load data from file
                if datapressure['press'] != 'off':                                # if pressure plugin is enabled
                    if (gv.sd['mas'] != 0) and not (gv.sd['mm']):                   # if is use master station and not manual control
                        if gv.srvals[gv.sd['mas']] != 0:                              # if master station is ON
                            if GPIO.input(pin_pressure) == 0:                           # if sensor is open
                                self._sleep(int(datapressure['time']))                   # wait to activated pressure sensor
                                if GPIO.input(pin_pressure) == 0:                        # if sensor is current open
                                    stop_stations()
                                    self.add_status('Pressure sensor is not activated in time -> stops all stations and sends email.')
                                    if datapressure['sendeml'] != 'off':  # if enabled send email
                                        send = True

                    else:  # if not used master station
                        self.status = ''
                        self.add_status('Not used master station.')

                if send:
                    TEXT = ('On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(
                        time.time())) + ' System detected error: pressure sensor.')
                    try:
                        from plugins.email_adj import email
                        email(SUBJ, TEXT)     # send email without attachments
                        self.add_status('Email was sent: ' + TEXT)
                        send = False
                    except Exception as err:
                        self.add_status('Email was not sent! ' + str(err))

                self._sleep(1)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('Pressure plugin encountered error: ' + err_string)
                self._sleep(60)


checker = PressureSender()

################################################################################
# Helper functions:                                                            #
################################################################################


def get_pressure_options():
    """Returns the data form file."""
    datapressure = {
        'time': 20,
        'press': 'off',
        'sendeml': 'off',
        'sensor': get_pressure_sensor(),
        'status': checker.status
    }
    try:
        with open('./data/pressure_adj.json', 'r') as f:  # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in datapressure:
                datapressure[key] = value
    except Exception:
        pass

    return datapressure


def get_pressure_sensor():
    if GPIO.input(pin_pressure) != 1:
        press = ('Pressure sensor is not active.')  # sensor pin is connected to ground
    else:
        press = ('Pressure sensor is active - pressure in pipeline is OK.')  # sensor pin is unconnected

    return str(press)

################################################################################
# Web pages:                                                                   #
################################################################################


class settings(ProtectedPage):
    """Load an html page for entering pressure adjustments."""

    def GET(self):
        return template_render.pressure_adj(get_pressure_options())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_pressure_options())


class update(ProtectedPage):
    """Save user input to pressure_adj.json file."""

    def GET(self):
        qdict = web.input()
        if 'press' not in qdict:
            qdict['press'] = 'off'
        if 'sendeml' not in qdict:
            qdict['sendeml'] = 'off'
        with open('./data/pressure_adj.json', 'w') as f:  # write the settings to file
            json.dump(qdict, f)
        checker.update()
        raise web.seeother('/')
