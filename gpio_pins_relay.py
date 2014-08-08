import gv

try:
    import RPi.GPIO as GPIO # Required for accessing General Purpose Input Output pins on Raspberry Pi
    gv.platform = 'pi'
except ImportError:
    try:
        import Adafruit_BBIO.GPIO as GPIO # Required for accessing General Purpose Input Output pins on Beagle Bone Black
        gv.platform = 'bo'
    except ImportError:
        gv.platform = '' # if no platform, allows program to still run.
        print 'No GPIO module was loaded from GPIO Pins module'

try:
    GPIO.setwarnings(TRUE)
    GPIO.cleanup()
except:
    pass

  #### pin defines ####
try:
    if gv.platform == 'pi': # If this will run on Raspberry Pi:  // WAS gv.platform == 'pi':
        GPIO.setmode(GPIO.BOARD) #IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.
        #create dictionary of pins to allow for concatination of pin names in setPinState method
        pins = dict()
        pins['pin_1'] = 8
        pins['pin_2'] = 7
        pins['pin_3'] = 5
        pins['pin_4'] = 3
        pins['pin_5'] = 10
        pins['pin_6'] = 12
        pins['pin_7'] = 13
        pins['pin_8'] = 11
        
        for items in pins:
		print pins[items]
        
    elif gv.platform == 'bo': # If this will run on Beagle Bone Black:
        pin_sr_dat = "P9_11"
        pin_sr_clk = "P9_13"
        pin_sr_noe = "P9_14"
        pin_sr_lat = "P9_12"
        pin_rain_sense = "P9_15"
        pin_relay = "P9_16"
except AttributeError:
    pass
#### setup GPIO pins as output or input and initialize to off/LOW ####
try:
    GPIO.setup(pins['pin_1'], GPIO.OUT)
    GPIO.output(pins['pin_1'], GPIO.LOW)
    GPIO.setup(pins['pin_2'], GPIO.OUT)
    GPIO.output(pins['pin_2'], GPIO.LOW)
    GPIO.setup(pins['pin_3'], GPIO.OUT)
    GPIO.output(pins['pin_3'], GPIO.LOW)
    GPIO.setup(pins['pin_4'], GPIO.OUT)
    GPIO.output(pins['pin_4'], GPIO.LOW)
    GPIO.setup(pins['pin_5'], GPIO.OUT)
    GPIO.output(pins['pin_5'], GPIO.LOW)
    GPIO.setup(pins['pin_6'], GPIO.OUT)
    GPIO.output(pins['pin_6'], GPIO.LOW)
    GPIO.setup(pins['pin_7'], GPIO.OUT)
    GPIO.output(pins['pin_7'], GPIO.LOW)
    GPIO.setup(pins['pin_8'], GPIO.OUT)
    GPIO.output(pins['pin_8'], GPIO.LOW)
    
except NameError:
    pass

#def disableShiftRegisterOutput():
#    """Disable output from shift register."""
#    try:
#        GPIO.output(pin_sr_noe, GPIO.HIGH)
#    except NameError:
#        pass

#def enableShiftRegisterOutput():
#    """Enable output from shift register."""
#    try:
#        GPIO.output(pin_sr_noe, GPIO.LOW)
#    except NameError:
#        pass

#def setShiftRegister(srvals):
#    """Set the state of each output pin on the shift register from the srvals list."""
#    print "*******"
#    print srvals
#    try:
#        GPIO.output(pin_sr_clk, GPIO.LOW)
#        GPIO.output(pin_sr_lat, GPIO.LOW)
#        for s in range(gv.sd['nst']):
#            GPIO.output(pin_sr_clk, GPIO.LOW)
#            if srvals[gv.sd['nst']-1-s]:
#                GPIO.output(pin_sr_dat, GPIO.HIGH)
#            else:
#                GPIO.output(pin_sr_dat, GPIO.LOW)
#            GPIO.output(pin_sr_clk, GPIO.HIGH)
#        GPIO.output(pin_sr_lat, GPIO.HIGH)
#    except NameError:
#        pass

######### NEW METHOD TO SET PIN STATUS BASED ON gv.srvals ##########
def setPinState(srvals):
    """SET The state of each output RANGE"""
    print("gv.sd is: ")
    print(gv.sd['nst'])
    try:
        for s in range(gv.sd['nst']):
            print("s is " + str(s))
            pinNo = "pin_" + str(s+1)
            print("pinNo is:")
            print(pinNo)
            if srvals[gv.sd['nst']-1-s]:
			  try:
    			      #GPIO.output(pins[pinNo], GPIO.HIGH)
			      print("Pin " + str(s+1) + " is: " + str(pins[pinNo]) + " and it is HIGH")
			  except NameError:
			      pass
            else:
			  try:
    			      #GPIO.output(pins[pinNo], GPIO.LOW)
			      print("Pin " + str(s+1) + " is: " + str(pins[pinNo]) + " and it is LOW")
			  except NameError:
			      pass
    except NameError:
		pass

def set_output():
    """Activate triacs according to shift register state."""
    #disableShiftRegisterOutput()
    #setShiftRegister(gv.srvals) # gv.srvals stores shift register state
    setPinState(gv.srvals)
    #enableShiftRegisterOutput()
    
