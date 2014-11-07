#!/usr/bin/python
import RPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# init list with pin numbers
pinList = [2, 3, 4, 17, 27, 22, 10, 9]

# loop through pins and set mode and state to 'low'
for i in pinList: 
    GPIO.setup(i, GPIO.OUT) 
    GPIO.output(i, GPIO.HIGH)

# time to sleep between operations in the main loop
SleepTimeS = 0.2
SleepTimeL = 0.5

# main loop
try:
   while True:
      for i in pinList:
         GPIO.output(i, GPIO.LOW)
         time.sleep(SleepTimeS);
         GPIO.output(i, GPIO.HIGH)
         time.sleep(SleepTimeS);
         GPIO.output(i, GPIO.LOW)
         time.sleep(SleepTimeS);
         GPIO.output(i, GPIO.HIGH)
         time.sleep(SleepTimeL);

# End program cleanly with keyboard
except KeyboardInterrupt:
  print "  Quit"

  # Reset GPIO settings
  GPIO.cleanup()

# find more information on this script at
# http://youtu.be/oaf_zQcrg7g
