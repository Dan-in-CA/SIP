# -*- coding: utf-8 -*-

import gv

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

from blinker import signal

zone_change = signal('zone_change')

try:
    GPIO.setwarnings(False)
except Exception:
    pass


global pin_rain_sense

try:
    if gv.platform == 'pi':  # If this will run on Raspberry Pi:
        GPIO.setmode(GPIO.BOARD)  # IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.
        pin_rain_sense = 8        
    elif gv.platform == 'bo':  # If this will run on Beagle Bone Black:
        pin_rain_sense = "P9_15"        
except AttributeError:
    pass
try:
    GPIO.setup(pin_rain_sense, GPIO.IN)    
except NameError:
    pass


def setup_pins():
    """
    Define and setup GPIO pins for shift register operation
    """

    global pin_sr_dat
    global pin_sr_clk
    global pin_sr_noe
    global pin_sr_lat
    global pin_relay

    try:
        if gv.platform == 'pi':  # If this will run on Raspberry Pi:
            GPIO.setmode(GPIO.BOARD)  # IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.
            pin_sr_dat = 13
            pin_sr_clk = 7
            pin_sr_noe = 11
            pin_sr_lat = 15
            pin_relay = 10
        elif gv.platform == 'bo':  # If this will run on Beagle Bone Black:
            pin_sr_dat = "P9_11"
            pin_sr_clk = "P9_13"
            pin_sr_noe = "P9_14"
            pin_sr_lat = "P9_12"
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
        GPIO.setup(pin_relay, GPIO.OUT)
    except NameError:
        pass


def disableShiftRegisterOutput():
    """Disable output from shift register."""

    try:
        pin_sr_noe
    except NameError:
        if gv.use_gpio_pins:
            setup_pins()
    try:
        GPIO.output(pin_sr_noe, GPIO.HIGH)
    except Exception:
        pass


def enableShiftRegisterOutput():
    """Enable output from shift register."""

    try:
        GPIO.output(pin_sr_noe, GPIO.LOW)
    except Exception:
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
    except Exception:
        pass


def set_output():
    """Activate triacs according to shift register state."""

    disableShiftRegisterOutput()
    setShiftRegister(gv.srvals)  # gv.srvals stores shift register state
    enableShiftRegisterOutput()
    zone_change.send()