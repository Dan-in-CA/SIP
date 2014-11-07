#!/usr/bin/env python
# This plugin sends data to I2C for LCD 16x2 char with PCF8574. Visit for more: www.pihrt.com/elektronika/258-moje-rapsberry-pi-i2c-lcd-16x2.
# This plugin required python pylcd2.py library


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
from helpers import uptime, get_ip, get_cpu_temp, get_rpi_revision

# Add a new url to open the data entry page.
urls.extend(['/lcd', 'plugins.lcd_adj.settings',
             '/lcdj', 'plugins.lcd_adj.settings_json',
             '/lcda', 'plugins.lcd_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['LCD Settings', '/lcd'])

################################################################################
# Main function loop:                                                          #
################################################################################


class LCDSender(Thread):
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
        print "LCD plugin is active"
        text_shift = 0

        while True:
            try:
                datalcd = get_lcd_options()                          # load data from file
                if datalcd['use_lcd'] != 'off':                      # if LCD plugin is enabled
                    if text_shift > 7:  # Print 0-7 messages to LCD
                        text_shift = 0
                        self.status = ''

                    get_LCD_print(self, text_shift)   # Print to LCD 16x2
                    text_shift += 1  # Increment text_shift value

                self._sleep(4)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('LCD plugin encountered error: ' + err_string)
                self._sleep(60)


checker = LCDSender()

################################################################################
# Helper functions:                                                            #
################################################################################


def get_LCD_print(self, report):
    """Print messages to LCD 16x2"""
    datalcd = get_lcd_options()
    
    import Adafruit_CharLCD as LCD
    lcd = LCD.Adafruit_CharLCDPlate()
    lcd.set_color(1.0, 0.0, 0.0)
    lcd.clear()
    ##lcd = pylcd2.lcd(adr, 1 if get_rpi_revision() >= 2 else 0)  # Address for PCF8574 = example 0x20, Bus Raspi = 1 (0 = 256MB, 1=512MB)

    if report == 0:
        lcd.clear()
        lcd.message("Open Sprinkler\nIrrigation Syst.")
        self.add_status('Open Sprinkler. / Irrigation syst.')
    elif report == 1:
        lcd.clear()
        lcd.message("Software ospi:\n"+gv.ver_date)
        self.add_status('Software ospi: / ' + gv.ver_date)
    elif report == 2:
        ip = get_ip()
        lcd.clear()
        lcd.message("My RPi IP:\n"+str(ip))
        self.add_status('My IP is: / ' + str(ip))
    elif report == 3:
        lcd.clear()
        lcd.message("My Port:\n8080")
        self.add_status('Port IP: / 8080')
    elif report == 4:
        temp = get_cpu_temp(gv.sd['tu']) + ' ' + gv.sd['tu']
        lcd.clear()
        lcd.message("CPU Temp.:\n"+temp)
        self.add_status('CPU temperature: / ' + temp)
    elif report == 5:
        da = time.strftime('%d.%m.%Y', time.gmtime(gv.now))
        ti = time.strftime('%H:%M:%S', time.gmtime(gv.now))
        lcd.clear()
        lcd.message(da+"\n"+ti)
        self.add_status(da + ' ' + ti)
    elif report == 6:
        up = uptime()
        lcd.clear()
        lcd.message("System Run Time:\n"+up)
        self.add_status('System run time: / ' + up)
    elif report == 7:
        if gv.sd['rs']:
            rain_sensor = "Active"
        else:
            rain_sensor = "Inactive"
        lcd.clear()
        lcd.message("Rain Sensor:\n"+rain_sensor)
        self.add_status('Rain sensor: / ' + rain_sensor)


def get_lcd_options():
    """Returns the data form file."""
    datalcd = {
        'use_lcd': 'off',
        'adress': '0x20',
        'status': checker.status
    }
    try:
        with open('./data/lcd_adj.json', 'r') as f:  # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in datalcd:
                datalcd[key] = value
    except Exception:
        pass

    return datalcd

################################################################################
# Web pages:                                                                   #
################################################################################


class settings(ProtectedPage):
    """Load an html page for entering lcd adjustments."""

    def GET(self):
        return template_render.lcd_adj(get_lcd_options())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_lcd_options())


class update(ProtectedPage):
    """Save user input to lcd_adj.json file."""

    def GET(self):
        qdict = web.input()
        if 'use_lcd' not in qdict:
            qdict['use_lcd'] = 'off'
        with open('./data/lcd_adj.json', 'w') as f:  # write the settings to file
            json.dump(qdict, f)
        checker.update()
        raise web.seeother('/')
