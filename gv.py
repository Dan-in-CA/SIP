#!/usr/bin/python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from six.moves import range

# standard library imports
from calendar import timegm
import json
import subprocess
from threading import RLock
import time

##############################
#### Revision information ####
major_ver = 4
minor_ver = 0
old_count = 868 #  update this to reset revision number.

try:
    revision = int(subprocess.check_output([u"git", u"rev-list", u"--count", u"HEAD"]))
    ver_str = u"{}.{}.{}".format(major_ver, minor_ver, (revision - old_count))
except Exception as e:
    report_error(_(u"Could not use git to determine version!"), e)
    revision = 999
    ver_str = u"{}.{}.{}".format(major_ver, minor_ver, revision)

try:
    ver_date = subprocess.check_output(
        [u"git", u"log", u"-1", u"--format=%cd", u"--date=short"]
    ).strip()
    ver_date = ver_date.decode('utf-8')
except Exception as e:
    report_error(_(u"Could not use git to determine date of last commit!"), e)
    ver_date = u"2015-01-09"

#####################
#### Global vars ####

# Settings Dictionary. A set of vars kept in memory and persisted in a file.
# Edit this default dictionary definition to add or remove "key": "value" pairs or change defaults.
# note old passphrases stored in the "pwd" option will be lost - reverts to default passphrase.

sd = {
    u"en": 1,
    u"seq": 1,
    u"ir": [0],
    u"iw": [0],
    u"rsn": 0,
    u"htp": 80,
    u"htip": u"::",
    u"nst": 8,
    u"rdst": 0,
    u"loc": u"",
    u"tz": 48,
    u"tf": 1,
    u"rs": 0,
    u"rd": 0,
    u"mton": 0,
    u"lr": 100,
    u"sdt": 0,
    u"mas": 0,
    u"wl": 100,
    u"bsy": 0,
    u"lg": 1,
    u"urs": 0,
    u"nopts": 13,
    u"upas": 0,
    u"rst": 1,
    u"mm": 0,
    u"mo": [0],
    u"rbt": 0,
    u"mtoff": 0,
    u"nbrd": 1,
    u"tu": u"C",
    u"snlen": 32,
    u"name": u"SIP",
    u"theme": u"basic",
    u"show": [255],
    u"passphrase": u"12d4e6fc471fbe073df5a0678fcffb9f75b12161e4e3f6d1e1bd81ffb22163bf",
    u"lang": u"default",
    u"idd": 0,
    u"pigpio": 0,
    u"alr": 0
}

try:
    with open(u"./data/sd.json", u"r") as sdf:  # A config file
        sd_temp = json.load(sdf)
    for key in sd:  # If file loaded, replce default values in sd with values from file
        if key in sd_temp:
            sd[key] = sd_temp[key]
except IOError:  # If file does not exist, it will be created using defaults.
    with open(u"./data/sd.json", u"w") as sdf:  # save file
        json.dump(sd, sdf, indent=4, sort_keys=True)

if sd[u"pigpio"]:
    try:
        subprocess.check_output(u"pigpiod", stderr=subprocess.STDOUT)
        use_pigpio = True
    except Exception as e:
        report_error(u"pigpio not found. Using RPi.GPIO", e)
else:
    use_pigpio = False

from helpers import load_programs, station_names

nowt = time.localtime()
now = timegm(nowt)
plugin_menu = []  # Empty list of lists for plugin links (e.g. ["name", "URL"])
srvals = [0] * (sd[u"nst"])  # Shift Register values
output_srvals = [0] * (sd[u"nst"])  # Shift Register values last set by set_output()
output_srvals_lock = RLock()
rovals = [0] * sd[u"nbrd"] * 7  # Run Once durations
snames = station_names()  # Load station names from file
pd = load_programs()  # Load program data from file
plugin_data = {}  # Empty dictionary to hold plugin based global data
plugFtr = []  # Empty dictionary to hold plugin data for display in footer
plugStn = []  # Empty dictionary to hold plugin data for display on timeline

ps = []  # Program schedule (used for UI display)
for i in range(sd[u"nst"]):
    ps.append([0, 0])

pon = None  # Program on (Holds program number of a running program)
sbits = [0] * (sd[u"nbrd"] + 1)  # Used to display stations that are on in UI

rs = []  # run schedule
for j in range(sd[u"nst"]):
    rs.append(
        [0, 0, 0, 0]
    )  # scheduled start time, scheduled stop time, duration, program index

lrun = [0, 0, 0, 0]  # station index, program number, duration, end time (Used in UI)
scount = (
    0
)  # Station count, used in set station to track on stations with master association.
use_gpio_pins = True

options = [
    [
        _(u"System name"),
        u"string",
        u"name",
        _(u"Unique name of this SIP system."),
        _(u"System"),
    ],
    [
        _(u"Location"),
        u"string",
        u"loc",
        _(u"City name or zip code. Use comma or + in place of space."),
        _(u"System"),
    ],
    [_(u"Language"), u"list", u"lang", _(u"Select language."), _(u"System")],
    [
        _(u"24-hour clock"),
        u"boolean",
        u"tf",
        _(u"Display times in 24 hour format (as opposed to AM/PM style.)"),
        _(u"System"),
    ],
    [_(u"HTTP port"), u"int", u"htp", _(u"HTTP port."), _(u"System")],
    [
        _(u"HTTP IP addr"),
        u"string",
        u"htip",
        _(u"IP Address used for HTTP server socket.  IPv4 or IPv6 address"),
        _(u"System"),
    ],
    [
        _(u"Use pigpio"),
        u"boolean",
        u"pigpio",
        _(u"GPIO Library to use. Default is RPi.GPIO"),
        _(u"System"),
    ],
    [
        _(u"Water Scaling"),
        u"int",
        u"wl",
        _(u"Water scaling (as %), between 0 and 100."),
        _(u"System"),
    ],
    [
        _(u"Enable passphrase"),
        u"boolean",
        u"upas",
        _(u"Minimal security. \nPrevent unauthorized users from accessing the system without a passphrase. \n*** Default is opendoor ***"),
        _(u"Manage Passphrase"),
    ],
    [
        _(u"Current passphrase"),
        u"password",
        u"opw",
        _(u"Enter the current passphrase. \n*** Defalut is opendoor ***"),
        _(u"Manage Passphrase"),
    ],
    [
        _(u"New passphrase"),
        u"password",
        u"npw",
        _(u"Enter a new passphrase."),
        _(u"Manage Passphrase"),
    ],
    [
        _(u"Confirm passphrase"),
        u"password",
        u"cpw",
        _(u"Confirm the new passphrase."),
        _(u"Manage Passphrase"),
    ],
    [
        _(u"Sequential"),
        u"boolean",
        u"seq",
        _(u"Sequential or concurrent running mode."),
        _(u"Station Handling"),
    ],
    [
        _(u"Individual Duration"),
        u"boolean",
        u"idd",
        _(u"Allow each station to have its own run time in programs."),
        _(u"Station Handling"),
    ],
    [
        _(u"Station extensions"),
        u"int",
        u"nbrd",
        _(u"Add 8 stations for each extension."),
        _(u"Station Handling"),
    ],
    [
        _(u"Station delay"),
        u"int",
        u"sdt",
        _(u"Station delay time (in seconds), between 0 and 240."),
        _(u"Station Handling"),
    ],
    [
        _(u"Active-Low Relay"),
        u"boolean",
        u"alr",
        _(u"Using active-low relay boards connected through shift registers"),
        _(u"Station Handling"),
    ],
    [
        _(u"Master station"),
        u"int",
        u"mas",
        _(u"Select master station."),
        _(u"Configure Master"),
    ],
    [
        _(u"Master on adjust"),
        u"int",
        u"mton",
        _(u"Master on delay (in seconds), between +0 and +60."),
        _(u"Configure Master"),
    ],
    [
        _(u"Master off adjust"),
        u"int",
        u"mtoff",
        _(u"Master off delay (in seconds), between -60 and +60."),
        _(u"Configure Master"),
    ],
    [
        _(u"Use rain sensor"),
        u"boolean",
        u"urs",
        _(u"Use rain sensor."),
        _(u"Rain Sensor"),
    ],
    [
        _(u"Normally open"),
        u"boolean",
        u"rst",
        _(u"Rain sensor type."),
        _(u"Rain Sensor"),
    ],
    [
        _(u"Enable logging"),
        u"boolean",
        u"lg",
        _(
            u"Log all events - note that repetitive writing to an SD card can shorten its lifespan."
        ),
        _(u"Logging"),
    ],
    [
        _(u"Max log entries"),
        u"int",
        u"lr",
        _(u"Length of log to keep, 0=no limits."),
        _(u"Logging"),
    ],
]
