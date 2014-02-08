try:
    import RPi.GPIO as GPIO # Required for accessing General Purpose Input Output pins on Raspberry Pi
except ImportError:
    try:
        import Adafruit_BBIO.GPIO as GPIO # Required for accessing General Purpose Input Output pins on Beagle Bone Black
    except ImportError:
        print 'No GPIO module was loaded'
        pass

def register(): #perform any necessary action on load.
#    pass
    print 'relay module loaded.'

def getDoorState():
    if GPIO.input(pin_door_sense):
        res1 = "'Open'"
    else:
        res1 = "'Closed'"
    return res1

# Simulate garage door button push by turning relay on for a short time
def toggle_door():
    GPIO.output(pin_relay, ospi.HIGH)
    time.sleep(1)
    GPIO.output(pin_relay, GPIO.LOW)