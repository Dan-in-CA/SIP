

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
    GPIO.output(pin_relay, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(pin_relay, GPIO.LOW)