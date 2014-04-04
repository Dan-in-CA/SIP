from gpio_pins import *
from urls import *
import time

urls.extend(['/tr', 'plugins.relay.toggle_relay']) # Add a new url for this plugin.

class toggle_relay:
    """Test by turning relay on for a short time, then off."""
    def GET(self):
        try:
            GPIO.output(pin_relay, GPIO.HIGH)
            time.sleep(3)
            GPIO.output(pin_relay, GPIO.LOW)
        except:
            pass