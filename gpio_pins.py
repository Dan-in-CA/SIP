import sys, gv

try:
    import RPi.GPIO as GPIO # Required for accessing General Purpose Input Output pins on Raspberry Pi
    gv.platform = 'pi'
except ImportError:
    try:
        import Adafruit_BBIO.GPIO as GPIO # Required for accessing General Purpose Input Output pins on Beagle Bone Black
        gv.platform = 'bo'
    except ImportError:
        print 'No GPIO module was loaded from GPIO Pins module'
        #sys.exit(1)

try:
    GPIO.setwarnings(False)
except:
    pass    

  #### pin defines ####
try:
    if gv.platform == 'pi': # If this will run on Raspberry Pi:
        GPIO.setmode(GPIO.BOARD) #IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.
        pin_sr_dat = 13
        pin_sr_clk = 7
        pin_sr_noe = 11
        pin_sr_lat = 15
        pin_rain_sense = 8
        pin_relay = 10
    elif gv.platform == 'bo': # If this will run on Beagle Bone Black:
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
    GPIO.setup(pin_sr_clk, GPIO.OUT)
    GPIO.setup(pin_sr_noe, GPIO.OUT)
    GPIO.setup(pin_sr_dat, GPIO.OUT)
    GPIO.setup(pin_sr_lat, GPIO.OUT)
    GPIO.setup(pin_rain_sense, GPIO.IN)
    GPIO.setup(pin_relay, GPIO.OUT)
except NameError:
    pass