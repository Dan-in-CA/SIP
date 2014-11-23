# -*- coding: utf-8 -*-

import gv
from blinker import signal

zone_change = signal('zone_change')

try:
    import RPi.GPIO as GPIO  # Required for accessing General Purpose Input Output pins on Raspberry Pi
    gv.platform = 'pi'
except ImportError:
    try:
        import Adafruit_BBIO.GPIO as GPIO  # Required for accessing General Purpose Input Output pins on Beagle Bone Black
        gv.platform = 'bo'
    except ImportError:
        gv.platform = ''  # if no platform, allows program to still run.
        print 'No GPIO module was loaded from GPIO Pins module'
         # Makes it runnable on machines other than RPi
        #  GPIO = None

try:
    GPIO.setwarnings(False)
    GPIO.cleanup()
except Exception:
    pass

  #### pin defines ####

try:
    if gv.platform == 'pi':  # If this will run on Raspberry Pi:
        GPIO.setmode(GPIO.BOARD)  # IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.
        pin_sr_dat = 13
        pin_sr_clk = 7
        pin_sr_noe = 11
        pin_sr_lat = 15
        pin_rain_sense = 8
        pin_relay = 10
    elif gv.platform == 'bo':  # If this will run on Beagle Bone Black:
        pin_sr_dat = "P9_11"
        pin_sr_clk = "P9_13"
        pin_sr_noe = "P9_14"
        pin_sr_lat = "P9_12"
        pin_rain_sense = "P9_15"
        pin_relay = "P9_16"
except AttributeError:
    pass

#### setup GPIO pins as output or input ####

try:
    GPIO.setup(pin_sr_noe, GPIO.OUT)
    GPIO.output(pin_sr_noe, GPIO.HIGH)
    GPIO.setup(pin_sr_clk, GPIO.OUT)
    GPIO.output(pin_sr_clk, GPIO.LOW)
    GPIO.setup(pin_sr_dat, GPIO.OUT)
    GPIO.output(pin_sr_dat, GPIO.LOW)
    GPIO.setup(pin_sr_lat, GPIO.OUT)
    GPIO.output(pin_sr_lat, GPIO.LOW)
    GPIO.setup(pin_rain_sense, GPIO.IN)
    GPIO.setup(pin_relay, GPIO.OUT)
except NameError:
    pass


def disableShiftRegisterOutput():
    """Disable output from shift register."""

    try:
        GPIO.output(pin_sr_noe, GPIO.HIGH)
    except NameError:
        pass


def enableShiftRegisterOutput():
    """Enable output from shift register."""

    try:
        GPIO.output(pin_sr_noe, GPIO.LOW)
    except NameError:
        pass


def setShiftRegister(srvals):
    """Set the state of each output pin on the shift register from the srvals list."""

    try:
        GPIO.output(pin_sr_clk, GPIO.LOW)
        GPIO.output(pin_sr_lat, GPIO.LOW)
        for s in range(gv.sd['nst']):
            GPIO.output(pin_sr_clk, GPIO.LOW)
            if srvals[gv.sd['nst']-1-s]:
                GPIO.output(pin_sr_dat, GPIO.HIGH)
            else:
                GPIO.output(pin_sr_dat, GPIO.LOW)
            GPIO.output(pin_sr_clk, GPIO.HIGH)
        GPIO.output(pin_sr_lat, GPIO.HIGH)
    except NameError:
        pass


def set_output():
    """Activate triacs according to shift register state."""

    disableShiftRegisterOutput()
    setShiftRegister(gv.srvals)  # gv.srvals stores shift register state
    enableShiftRegisterOutput()
    zone_change.send()