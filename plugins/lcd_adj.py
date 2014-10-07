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
    adr = 0x20
    if datalcd['adress'] == '0x20':  # range adress from PCF8574 or PCF 8574A
        adr = 0x20
    elif datalcd['adress'] == '0x21':
        adr = 0x21
    elif datalcd['adress'] == '0x22':
        adr = 0x22
    elif datalcd['adress'] == '0x23':
        adr = 0x23
    elif datalcd['adress'] == '0x24':
        adr = 0x24
    elif datalcd['adress'] == '0x25':
        adr = 0x25
    elif datalcd['adress'] == '0x26':
        adr = 0x26
    elif datalcd['adress'] == '0x27':
        adr = 0x27
    elif datalcd['adress'] == '0x38':
        adr = 0x38
    elif datalcd['adress'] == '0x39':
        adr = 0x39
    elif datalcd['adress'] == '0x3a':
        adr = 0x3a
    elif datalcd['adress'] == '0x3b':
        adr = 0x3b
    elif datalcd['adress'] == '0x3c':
        adr = 0x3c
    elif datalcd['adress'] == '0x3d':
        adr = 0x3d
    elif datalcd['adress'] == '0x3e':
        adr = 0x3e
    elif datalcd['adress'] == '0x3f':
        adr = 0x3f
    else:
        self.status = ''
        self.add_status('Error: Address is not range 0x20-0x27 or 0x38-0x3F!')
        self._sleep(5)
        return

    import pylcd2  # Library for LCD 16x2 PCF8574
    lcd = pylcd2.lcd(adr, 1 if get_rpi_revision() >= 2 else 0)  # Address for PCF8574 = example 0x20, Bus Raspi = 1 (0 = 256MB, 1=512MB)

    if report == 0:
        lcd.lcd_clear()
        lcd.lcd_puts("Open Sprinkler", 1)
        lcd.lcd_puts("Irrigation syst.", 2)
        self.add_status('Open Sprinkler. / Irrigation syst.')
    elif report == 1:
        lcd.lcd_clear()
        lcd.lcd_puts("Software ospi:", 1)
        lcd.lcd_puts(gv.ver_date, 2)
        self.add_status('Software ospi: / ' + gv.ver_date)
    elif report == 2:
        lcd.lcd_clear()
        ip = get_ip()
        lcd.lcd_puts("My IP is:", 1)
        lcd.lcd_puts(str(ip), 2)
        self.add_status('My IP is: / ' + str(ip))
    elif report == 3:
        lcd.lcd_clear()
        lcd.lcd_puts("Port IP:", 1)
        lcd.lcd_puts("8080", 2)
        self.add_status('Port IP: / 8080')
    elif report == 4:
        lcd.lcd_clear()
        temp = get_cpu_temp(gv.sd['tu']) + ' ' + gv.sd['tu']
        lcd.lcd_puts("CPU temperature:", 1)
        lcd.lcd_puts(temp, 2)
        self.add_status('CPU temperature: / ' + temp)
    elif report == 5:
        lcd.lcd_clear()
        da = time.strftime('%d.%m.%Y', time.gmtime(gv.now))
        ti = time.strftime('%H:%M:%S', time.gmtime(gv.now))
        lcd.lcd_puts(da, 1)
        lcd.lcd_puts(ti, 2)
        self.add_status(da + ' ' + ti)
    elif report == 6:
        lcd.lcd_clear()
        up = uptime()
        lcd.lcd_puts("System run time:", 1)
        lcd.lcd_puts(up, 2)
        self.add_status('System run time: / ' + up)
    elif report == 7:
        lcd.lcd_clear()
        if gv.sd['rs']:
            rain_sensor = "Active"
        else:
            rain_sensor = "Inactive"
        lcd.lcd_puts("Rain sensor:", 1)
        lcd.lcd_puts(rain_sensor, 2)
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
