from __future__ import print_function

# !/usr/bin/env python

#  This plugin includes example functions that are triggered by events in sip.py

from blinker import signal
import gv

### Alarm Signal (Example of sending and recieving a blinker signal) ###

# Function to be run when sigal is recieved.
def notify_alarm_toggled(name, **kw):
    ### uncomment the following line to print message to standard out on SIP startup ###
    # print("Messge from {}!: {}".format(name, kw["txt"]))
    pass

# instance of named signal
alarm = signal("alarm_toggled")  
# Connect signal to function to be run.
alarm.connect(notify_alarm_toggled)

# Send alarm signal 
# (normally this would be in a function in a different module)
alarm.send("Signaling plugin", txt="Just an example!")

### new day ###
def notify_new_day(name, **kw):
    print("A new day has started.")

new_day = signal("new_day")
new_day.connect(notify_new_day)

### login ###
def notify_login(name, **kw):
    print("someone logged in")


loggedin = signal("loggedin")
loggedin.connect(notify_login)

### Option settings ###
def notify_option_change(name, **kw):
    print("Option settings changed in gv.sd")
    #  gv.sd is a dictionary containing the setting that changed.
    #  See "from options" in gv_reference.txt


option_change = signal("option_change")
option_change.connect(notify_option_change)

### program change ##
def notify_program_change(name, **kw):
    print("Programs changed")
    #  Programs are in gv.pd and /data/programs.json


program_change = signal("program_change")
program_change.connect(notify_program_change)

### program deleted ###
def notify_program_deleted(name, **kw):
    print("Program deleted")
    #  Programs are in gv.pd and /data/programs.json


program_deleted = signal("program_deleted")
program_deleted.connect(notify_program_deleted)

### program toggled ###
def notify_program_toggled(name, index, state):
    if name != "SIP":
        return
    if state:
        status = "enabled"
    else:
        status = "disabled"
    print("program " + str(index  + 1) +" " + status)
    # print("Program toggled on or off")
    #  Programs are in gv.pd and /data/programs.json


program_toggled = signal("program_toggled")
program_toggled.connect(notify_program_toggled)

### Rain Changed ##
def notify_rain_changed(name, **kw):
    print("Rain changed (from plugin)")
    #  Programs are in gv.pd and /data/programs.json


rain_changed = signal("rain_changed")
rain_changed.connect(notify_rain_changed)

### Reboot ###
def notify_rebooted(name, **kw):
    print("System rebooted")


rebooted = signal("rebooted")
rebooted.connect(notify_rebooted)

### Restart ###
def notify_restart(name, **kw):
    print("System is restarting")


restart = signal("restart")
restart.connect(notify_restart)

### Station Names ###
def notify_station_names(name, **kw):
    print("Station names changed")
    # Station names are in gv.snames and /data/snames.json


station_names = signal("station_names")
station_names.connect(notify_station_names)


### Stations were scheduled to run ###
# gets triggered when:
#       - A program is run (Scheduled or "run now")
#       - Stations are manually started with RunOnce
def report_station_scheduled(station, **kw):
    print("A station has been scheduled: {}".format(str(station)))
    
program_started = signal("station_scheduled")
program_started.connect(report_station_scheduled)

### Station Completed ###
def notify_station_completed(station, **kw):
    print("Station {} run completed".format(station))


complete = signal("station_completed")
complete.connect(notify_station_completed)

### System settings ###
def notify_value_change(name, **kw):
    print("Controller values changed in gv.sd")
    #  gv.sd is a dictionary containing the setting that changed.
    #  See "from controller values (cvalues)" gv_reference.txt


value_change = signal("value_change")
value_change.connect(notify_value_change)

### valves ###
def notify_zone_change(name, **kw):
    print("zones changed")
    print(gv.srvals)  #  This shows the state of the zones.


zones = signal("zone_change")
zones.connect(notify_zone_change)
