#!/usr/bin/env python

from gpio_pins import *
from urls import *
import web, time

urls.extend(['/tr', 'plugins.relay.toggle_relay']) # Add a new url for this plugin.

gv.plugin_menu.append(['Test Relay', '/tr']) # Add this plugin to the home page plugins menu

class toggle_relay:
    """Test relay by turning it on for a short time, then off."""
    def GET(self):
        try:
            GPIO.output(pin_relay, GPIO.HIGH) # turn relay on
            time.sleep(3)
            GPIO.output(pin_relay, GPIO.LOW) #Turn relay off
        except:
            pass
        raise web.seeother('/') # return to home page