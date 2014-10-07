# !/usr/bin/env python

import time

import gv
from gpio_pins import GPIO, pin_relay
from urls import urls
import web
from webpages import ProtectedPage


urls.extend(['/tr', 'plugins.relay.toggle_relay'])  # Add a new url for this plugin.

gv.plugin_menu.append(['Test Relay', '/tr'])  # Add this plugin to the home page plugins menu


class toggle_relay(ProtectedPage):
    """Test relay by turning it on for a short time, then off."""
    def GET(self):
        try:
            GPIO.output(pin_relay, GPIO.HIGH)  # turn relay on
            time.sleep(3)
            GPIO.output(pin_relay, GPIO.LOW)  # Turn relay off
        except Exception:
            pass
        raise web.seeother('/')  # return to home page