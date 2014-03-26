from gpio_pins import *
import time

def register(): #perform any necessary action on load.
    print 'relay module loaded.'

# Test by turning relay on for a short time, then off
def toggle_relay():
    try:
        GPIO.output(pin_relay, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(pin_relay, GPIO.LOW)
    except:
        pass