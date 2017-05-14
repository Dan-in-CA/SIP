# !/usr/bin/env python
#  This plugin includes example functions that are triggered by events in sip.py

from blinker import signal
import gv

### Alarm Signal ###
def notify_alarm_toggled(name, **kw):
    print "ALARM from {}!: {}".format(name, kw['txt'])
    
alarm = signal('alarm_toggled')
alarm.connect(notify_alarm_toggled)

# Send an alarm!
alarm.send("Example_Sender",txt="Just and example!")

### login ###
def notify_login(name, **kw):
    print "someone logged in"\

loggedin = signal('loggedin')
loggedin.connect(notify_login)

### Option settings ###
def notify_option_change(name, **kw):
    print "Option settings changed in gv.sd"
    #  gv.sd is a dictionary containing the setting that changed.
    #  See "from options" gv_reference.txt

option_change = signal('option_change')
option_change.connect(notify_option_change)

### program change ##
def notify_program_change(name, **kw):
    print "Programs changed"
    #  Programs are in gv.pd and /data/programs.json

program_change = signal('program_change')
program_change.connect(notify_program_change)

### program deleted ###
def notify_program_deleted(name, **kw):
    print "Program deleted"
    #  Programs are in gv.pd and /data/programs.json

program_deleted = signal('program_deleted')
program_deleted.connect(notify_program_deleted)

### program toggled ###
def notify_program_toggled(name, **kw):
    print "Program toggled on or off"
    #  Programs are in gv.pd and /data/programs.json

program_toggled = signal('program_toggled')
program_toggled.connect(notify_program_toggled)

### Rain Changed ##
def notify_rain_changed(name, **kw):
    print "Rain changed (from plugin)"
    #  Programs are in gv.pd and /data/programs.json

rain_changed = signal('rain_changed')
rain_changed.connect(notify_rain_changed)

### Reboot ###
def notify_rebooted(name, **kw):
    print "System rebooted"

rebooted = signal('rebooted')
rebooted.connect(notify_rebooted)

### Restart ###
def notify_restart(name, **kw):
    print "System is restarting"

restart = signal('restart')
restart.connect(notify_restart)

### Station Names ###
def notify_station_names(name, **kw):
    print "Station names changed"
    # Station names are in gv.snames and /data/snames.json

station_names = signal('station_names')
station_names.connect(notify_station_names)

### Stations were sheduled to run ###
# gets triggered when:
#       - A program is run (Scheduled or "run now")
#       - Stations are manually started with RunOnce
def notify_station_scheduled(name, **kw):
    print "Some Stations has been scheduled: {}".format(str(gv.rs))
program_started = signal('stations_scheduled')
program_started.connect(notify_station_scheduled)

### Station Completed ###
def notify_station_completed(station, **kw):
    print "Station {} run completed".format(station)

complete = signal('station_completed')
complete.connect(notify_station_completed)

### System settings ###
def notify_value_change(name, **kw):
    print "Controller values changed in gv.sd"
    #  gv.sd is a dictionary containing the setting that changed.
    #  See "from controller values (cvalues)" gv_reference.txt

value_change = signal('value_change')
value_change.connect(notify_value_change)

### valves ###
def notify_zone_change(name, **kw):
    print "zones changed"
    print gv.srvals #  This shows the state of the zones.
    
zones = signal('zone_change')
zones.connect(notify_zone_change)

