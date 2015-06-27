# !/usr/bin/env python
#  This plugin includes example functions that are triggered by events in ospi.py

from blinker import signal
import gv

### login ###
def notify_login(name, **kw):
    print "someone logged in"\

loggedin = signal('loggedin')
loggedin.connect(notify_login)

### valves ###
def notify_zone_change(name, **kw):
    print "zones changed"
    print gv.srvals #  This shows the state of the zones.

zones = signal('zone_change')
zones.connect(notify_zone_change)

### System settings ###
def notify_value_change(name, **kw):
    print "Controller values changed in gv.sd"
    #  gv.sd is a dictionary containing the setting that changed.
    #  See "from controller values (cvalues)" gv_reference.txt

value_change = signal('value_change')
value_change.connect(notify_value_change)

### Option settings ###
def notify_option_change(name, **kw):
    print "Option settings changed in gv.sd"
    #  gv.sd is a dictionary containing the setting that changed.
    #  See "from options" gv_reference.txt

option_change = signal('option_change')
option_change.connect(notify_option_change)

### Reboot ###
def notify_rebooted(name, **kw):
    print "Systm rebooted"

rebooted = signal('rebooted')
rebooted.connect(notify_rebooted)

### station names ###
def notify_station_names(name, **kw):
    print "Station names changed"
    # Station names are in gv.snames and /data/snames.json

station_names = signal('station_names')
station_names.connect(notify_station_names)

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