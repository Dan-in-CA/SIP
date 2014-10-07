# !/usr/bin/python
# -*- coding: utf-8 -*-

##############################
#### Revision information ####
import subprocess

major_ver = 2
minor_ver = 1
old_count = 208

try:
    revision = int(subprocess.check_output(['git', 'rev-list', '--count', '--first-parent', 'HEAD']))
    ver_str = '%d.%d.%d' % (major_ver, minor_ver, (revision - old_count))
except Exception:
    print 'Could not use git to determine version!'
    revision = 999
    ver_str = '%d.%d.%d' % (major_ver, minor_ver, revision)

try:
    ver_date = subprocess.check_output(['git', 'log', '-1', '--format=%cd', '--date=short']).strip()
except Exception:
    print 'Could not use git to determine date of last commit!'
    ver_date = '2014-09-10'

#####################
#### Global vars ####

# Settings Dictionary. A set of vars kept in memory and persisted in a file.
# Edit this default dictionary definition to add or remove "key": "value" pairs or change defaults.
# note old passwords stored in the "pwd" option will be lost - reverts to default password.
from calendar import timegm
import json
import time

platform = ''  # must be done before the following import because gpio_pins will try to set it

from helpers import password_salt, password_hash, load_programs, station_names

sd = {
    u"en": 1,
    u"seq": 1,
    u"ir": [0],
    u"rsn": 0,
    u"htp": 8080,
    u"nst": 8,
    u"rdst": 0,
    u"loc": u"",
    u"tz": 48,
    u"tf": 1,
    u"rs": 0,
    u"rd": 0,
    u"mton": 0,
    u"lr": u"100",
    u"sdt": 0,
    u"mas": 0,
    u"wl": 100,
    u"bsy": 0,
    u"lg": u"",
    u"urs": 0,
    u"nopts": 13,
    u"pwd": u"b3BlbmRvb3I=",
    u"password": u"",
    u"ipas": 0,
    u"rst": 1,
    u"mm": 0,
    u"mo": [0],
    u"rbt": 0,
    u"mtoff": 0,
    u"nprogs": 1,
    u"nbrd": 1,
    u"tu": u"C",
    u"snlen": 32,
    u"name": u"OpenSprinkler Pi",
    u"theme": u"basic",
    u"show": [255],
    u"salt": password_salt()
}

sd['password'] = password_hash('opendoor', sd['salt'])

try:
    with open('./data/sd.json', 'r') as sdf:  # A config file
        sd_temp = json.load(sdf)
    for key in sd:  # If file loaded, replce default values in sd with values from file
        if key in sd_temp:
            sd[key] = sd_temp[key]
except IOError:  # If file does not exist, it will be created using defaults.
    with open('./data/sd.json', 'w') as sdf:  # save file
        json.dump(sd, sdf)


now = timegm(time.localtime())
gmtnow = time.time()
plugin_menu = []  # Empty list of lists for plugin links (e.g. ['name', 'URL'])

srvals = [0] * (sd['nst'])  # Shift Register values
rovals = [0] * sd['nbrd'] * 7  # Run Once durations
snames = station_names()  # Load station names from file
pd = load_programs()  # Load program data from file

ps = []  # Program schedule (used for UI display)
for i in range(sd['nst']):
    ps.append([0, 0])

pon = None  # Program on (Holds program number of a running program)
sbits = [0] * (sd['nbrd'] + 1)  # Used to display stations that are on in UI

rs = []  # run schedule
for _ in range(sd['nst']):
    rs.append([0, 0, 0, 0])  # scheduled start time, scheduled stop time, duration, program index

lrun = [0, 0, 0, 0]  # station index, program number, duration, end time (Used in UI)
scount = 0  # Station count, used in set station to track on stations with master association.

options = [
    ["System name", "string", "name", "Unique name of this OpenSprinkler system.", "System"],
    ["Location", "string", "loc", "City name or zip code. Use comma or + in place of space.", "System"],
    ["Time zone", "int", "tz", "Example: GMT-4:00, GMT+5:30 (effective after reboot.)", "System"],
    ["24-hour clock", "boolean", "tf", "Display times in 24 hour format (as opposed to AM/PM style.)", "System"],
    ["HTTP port", "int", "htp", "HTTP port (effective after reboot.)", "System"],
    ["Disable security", "boolean", "ipas", "Allow anonymous users to access the system without a password.", "Change Password"],
    ["Current password", "password", "opw", "Re-enter the current password.", "Change Password"],
    ["New password", "password", "npw", "Enter a new password.", "Change Password"],
    ["Confirm password", "password", "cpw", "Confirm the new password.", "Change Password"],
    ["Sequential", "boolean", "seq", "Sequential or concurrent running mode.", "Station Handling"],
    ["Extension boards", "int", "nbrd", "Number of extension boards.", "Station Handling"],
    ["Station delay", "int", "sdt", "Station delay time (in seconds), between 0 and 240.", "Station Handling"],
    ["Master station", "int", "mas", "Select master station.", "Configure Master"],
    ["Master on adjust", "int", "mton", "Master on delay (in seconds), between +0 and +60.", "Configure Master"],
    ["Master off adjust", "int", "mtoff", "Master off delay (in seconds), between -60 and +60.", "Configure Master"],
    ["Use rain sensor", "boolean", "urs", "Use rain sensor.", "Rain Sensor"],
    ["Normally open", "boolean", "rst", "Rain sensor type.", "Rain Sensor"],
    ["Enable logging", "boolean", "lg", "Log all events - note that repetitive writing to an SD card can shorten its lifespan.", "Logging"],
    ["Max log entries", "int", "lr", "Length of log to keep, 0=no limits.", "Logging"]
]
