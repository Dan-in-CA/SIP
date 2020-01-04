# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from six.moves import range

# local module imports
from blinker import signal
import gv
try:
    import RPi.GPIO as GPIO
    gv.platform = u"pi"
except ImportError:
    try:
        import Adafruit_BBIO.GPIO as GPIO  # Required for accessing GPIO pins on Beagle Bone Black
        gv.pin_map = [None] * 11  # map only the pins we are using
        gv.pin_map.extend([u"P9_" + str(i) for i in range(11, 17)])
        gv.platform = u"bo"
    except ImportError:
        gv.pin_map = [
            i for i in range(27)
        ]  # assume 26 pins all mapped.  Maybe we should not assume anything, but...
        gv.platform = ""  # if no platform, allows program to still run.
        print(u"No GPIO module was loaded from GPIO Pins module") 
           
# fmt: off
if gv.platform == u"pi":    
    rev = GPIO.RPI_REVISION
    if rev == 1:
        # map 26 physical pins (1 based) with 0 for pins that do not have a gpio number
        if gv.use_pigpio:
            gv.pin_map = [ #  BMC numbering 
                0, #  offset for 1 based numbering
                0,  0,
                0,  0,
                1,  0,
                4,  14,
                0,  15,
                17, 18,
                21, 0,
                22, 23,
                0,  24,
                10, 0,
                9,  25,
                11, 8,
                0,  7,
            ]
        else:
            gv.pin_map = [ #  Board numbering
                0, #  offset for 1 based numbering
                0,  0,
                0,  0,
                5,  0,
                7,  8,
                0,  10,
                11, 12,
                13, 0,
                15, 16,
                0,  18,
                19, 0,
                21, 22,
                23, 24,
                0,  26,
            ]
    elif rev == 2:
        # map 26 physical pins (1 based) with 0 for pins that do not have a gpio number
        if gv.use_pigpio:
            gv.pin_map = [ #  BMC numbering
                0, #  offset for 1 based numbering
                0,  0,
                2,  0,
                3,  0,
                4,  14,
                0,  15,
                17, 18,
                27, 0,
                22, 23,
                0,  24,
                10, 0,
                9,  25,
                11, 8,
                0,  7,
            ]
        else:
            gv.pin_map = [#  Board numbering
                0, #  offset for 1 based numbering
                0,  0,
                0,  0,
                5,  0,
                7,  8,
                0,  10,
                11, 12,
                13, 0,
                15, 16,
                0,  18,
                19, 0,
                21, 22,
                23, 24,
                0,  26,
            ]
    elif rev == 3:
        # map 40 physical pins (1 based) with 0 for pins that do not have a gpio number
        if gv.use_pigpio:
            gv.pin_map = [ #  BMC numbering
                0, #  offset for 1 based numbering
                0,  0,
                2,  0,
                3,  0,
                4,  14,
                0,  15,
                17, 18,
                27, 0,
                22, 23,
                0,  24,
                10, 0,
                9,  25,
                11, 8,
                0,  7,
                0,  0,
                5,  0,
                6,  12,
                13, 0,
                19, 16,
                26, 20,
                0,  21,
            ]
        else:
            gv.pin_map = [#  Board numbering
                0, #  offset for 1 based numbering
                0,  0,
                3,  0,
                5,  0,
                7,  8,
                0,  10,
                11, 12,
                13, 0,
                15, 16,
                0,  18,
                19, 0,
                21, 22,
                23, 24,
                0,  26,
                0,  0,
                29, 0,
                31, 32,
                33, 0,
                35, 36,
                37, 38,
                0,  40,
            ]
    else:
        print(u"Unknown pi pin revision.  Using pin mapping for rev 3")
# fmt: on

zone_change = signal(u"zone_change")

try:
    if gv.use_pigpio:
        import pigpio

        pi = pigpio.pi()
    else:
        GPIO.setwarnings(False)
        GPIO.setmode(
            GPIO.BOARD
        )  # IO channels are referenced by header connector pin numbers.
except Exception:
    pass


global pin_rain_sense
global pin_relay

try:
    if gv.platform == u"pi":  # If this will run on Raspberry Pi:
        GPIO.setmode(GPIO.BOARD)
        pin_rain_sense = gv.pin_map[8]
        pin_relay = gv.pin_map[10]
    elif gv.platform == u"bo":  # If this will run on Beagle Bone Black:
        pin_rain_sense = gv.pin_map[15]
        pin_relay = gv.pin_map[16]
except AttributeError:
    pass

try:
    if gv.use_pigpio:
        pi.set_mode(pin_rain_sense, pigpio.INPUT)
        pi.set_pull_up_down(pin_rain_sense, pigpio.PUD_UP)
        pi.set_mode(pin_relay, pigpio.OUTPUT)
    else:
        GPIO.setup(pin_rain_sense, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(pin_relay, GPIO.OUT)
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
    global pi

    try:
        if gv.platform == u"pi":  # If this will run on Raspberry Pi:
            if not gv.use_pigpio:
                GPIO.setmode(
                    GPIO.BOARD
                )  # IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.
            pin_sr_dat = gv.pin_map[13]
            pin_sr_clk = gv.pin_map[7]
            pin_sr_noe = gv.pin_map[11]
            pin_sr_lat = gv.pin_map[15]
        elif gv.platform == u"bo":  # If this will run on Beagle Bone Black:
            pin_sr_dat = gv.pin_map[11]
            pin_sr_clk = gv.pin_map[13]
            pin_sr_noe = gv.pin_map[14]
            pin_sr_lat = gv.pin_map[12]

    except AttributeError:
        pass

    #### setup GPIO pins as output or input ####
    try:
        if gv.use_pigpio:
            pi.set_mode(pin_sr_noe, pigpio.OUTPUT)
            pi.set_mode(pin_sr_clk, pigpio.OUTPUT)
            pi.set_mode(pin_sr_dat, pigpio.OUTPUT)
            pi.set_mode(pin_sr_lat, pigpio.OUTPUT)
            pi.write(pin_sr_noe, 1)
            pi.write(pin_sr_clk, 0)
            pi.write(pin_sr_dat, 0)
            pi.write(pin_sr_lat, 0)
        else:
            GPIO.setup(pin_sr_noe, GPIO.OUT)
            GPIO.setup(pin_sr_clk, GPIO.OUT)
            GPIO.setup(pin_sr_dat, GPIO.OUT)
            GPIO.setup(pin_sr_lat, GPIO.OUT)
            GPIO.output(pin_sr_noe, GPIO.HIGH)
            GPIO.output(pin_sr_clk, GPIO.LOW)
            GPIO.output(pin_sr_dat, GPIO.LOW)
            GPIO.output(pin_sr_lat, GPIO.LOW)
    except NameError:
        pass


def disableShiftRegisterOutput():
    """Disable output from shift register."""

    global pi
    try:
        pin_sr_noe
    except NameError:
        if gv.use_gpio_pins:
            setup_pins()
    try:
        if gv.use_pigpio:
            pi.write(pin_sr_noe, 1)
        else:
            GPIO.output(pin_sr_noe, GPIO.HIGH)
    except Exception:
        pass


def enableShiftRegisterOutput():
    """Enable output from shift register."""

    global pi
    try:
        if gv.use_pigpio:
            pi.write(pin_sr_noe, 0)
        else:
            GPIO.output(pin_sr_noe, GPIO.LOW)
    except Exception:
        pass


def setShiftRegister(srvals):
    """Set the state of each output pin on the shift register from the srvals list."""

    global pi
    try:
        if gv.use_pigpio:
            pi.write(pin_sr_clk, 0)
            pi.write(pin_sr_lat, 0)
            for s in range(gv.sd[u"nst"]):
                pi.write(pin_sr_clk, 0)
                if srvals[gv.sd[u"nst"] - 1 - s]:
                    pi.write(pin_sr_dat, 1)
                else:
                    pi.write(pin_sr_dat, 0)
                pi.write(pin_sr_clk, 1)
            pi.write(pin_sr_lat, 1)
        else:
            GPIO.output(pin_sr_clk, GPIO.LOW)
            GPIO.output(pin_sr_lat, GPIO.LOW)
            for s in range(gv.sd[u"nst"]):
                GPIO.output(pin_sr_clk, GPIO.LOW)
                if srvals[gv.sd[u"nst"] - 1 - s]:
                    GPIO.output(pin_sr_dat, GPIO.HIGH)
                else:
                    GPIO.output(pin_sr_dat, GPIO.LOW)
                GPIO.output(pin_sr_clk, GPIO.HIGH)
            GPIO.output(pin_sr_lat, GPIO.HIGH)
    except Exception:
        pass


def set_output():
    """
    Activate pins according to gv.srvals.
    """

    with gv.output_srvals_lock:
        gv.output_srvals = gv.srvals
        if gv.sd[u"alr"]:
            gv.output_srvals = [
                1 - i for i in gv.output_srvals
            ]  #  invert logic of shift registers
        disableShiftRegisterOutput()
        setShiftRegister(gv.output_srvals)  # gv.srvals stores shift register state
        enableShiftRegisterOutput()
        zone_change.send()
