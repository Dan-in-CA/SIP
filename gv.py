#!/usr/bin/python
# -*- coding: utf-8 -*-

# standard library imports
from calendar import timegm
from collections import OrderedDict
import json
import subprocess
from threading import RLock
import time

##############################
#### Revision information ####
major_ver = 5
minor_ver = 0
old_count = 1035 #  update this to reset revision number.

try:
    revision = int(subprocess.check_output(["git", "rev-list", "--count", "HEAD"]))
    ver_str = "{}.{}.{}".format(major_ver, minor_ver, (revision - old_count))
except Exception as e:
    print(_("Could not use git to determine version!"), e)
    revision = 999
    ver_str = "{}.{}.{}".format(major_ver, minor_ver, revision)   
# ver_str = f"{major_ver}.{minor_ver}" # .format(major_ver, minor_ver)    

try:
    ver_date = subprocess.check_output(
        ["git", "log", "-1", "--format=%cd", "--date=short"]
    ).strip()
    ver_date = ver_date.decode('utf-8')
except Exception as e:
    print(_("Could not use git to determine date of last commit!"), e)
    ver_date = "2015-01-09"

#####################
#### Global vars ####

# Settings Dictionary. A set of vars kept in memory and persisted in a file.
# Edit this default dictionary definition to add or remove "key": "value" pairs or change defaults.
# note old passphrases stored in the "pwd" option will be lost - reverts to default passphrase.

sd = {
    "en": 1,
    "seq": 1,
    "ir": [0],
    "iw": [0],
    "rsn": 0,
    "htp": 80,
    "htip": "::",
    "nst": 8,
   "rdst": 0,
    "loc": "",
    "tz": 48,
    "tf": 1,
    "rs": 0,
    "rd": 0,
    "mton": 0,
    "lr": 100,
    "sdt": 0,
    "mas": 0,
    "wl": 100,
    "bsy": 0,
    "lg": 1,
    "urs": 0,
    "nopts": 13,
    "upas": 0,
    "rst": 1,
    "mm": 0,
    "mo": [0],
    "rbt": 0,
    "mtoff": 0,
    "nbrd": 1,
    "tu": "C",
    "snlen": 32,
    "name": "SIP",
    "theme": "basic",
    "show": [255],
    "passphrase": "12d4e6fc471fbe073df5a0678fcffb9f75b12161e4e3f6d1e1bd81ffb22163bf",
    "lang": "default",
    "idd": 0,
    "pigpio": 0,
    "alr": 0
}

try:
    with open("./data/sd.json", "r") as sdf:  # A config file
        sd_temp = json.load(sdf)
    for key in sd:  # If file loaded, replce default values in sd with values from file
        if key in sd_temp:
            sd[key] = sd_temp[key]
except IOError:  # If file does not exist, it will be created using defaults.
    with open("./data/sd.json", "w") as sdf:  # save file
        json.dump(sd, sdf, indent=4, sort_keys=True)

if sd["pigpio"]:
    try:
        subprocess.check_output("pigpiod", stderr=subprocess.STDOUT)
        use_pigpio = True
    except Exception as e:
        use_pigpio = False
        print(_("pigpio not found. Using RPi.GPIO"), e)
else:
    use_pigpio = False

from helpers import load_programs, station_names

day_ord = 0
node_runs = {}
now = time.time()
nowt = time.localtime(now)

tz_offset = round(now - timegm(nowt)
)  # compatible with Javascript (negative tz shown as positive value)

plugin_menu = []  # Empty list of lists for plugin links (e.g. ["name", "URL"])
srvals = [0] * (sd["nst"])  # Shift Register values
output_srvals = [0] * (sd["nst"])  # Shift Register values last set by set_output()
output_srvals_lock = RLock()
rovals = [0] * sd["nbrd"] * 7  # Run Once durations
snames = station_names()  # Load station names from file
pd = load_programs()  # Load program data from file
plugin_data = {}  # Empty dictionary to hold plugin based global data
pluginFtr = []  # Empty list to hold plugin data for display in footer
pluginStn = []  # Empty list to hold plugin data for display on timeline

ps = []  # Program schedule (used for UI display)
for i in range(sd["nst"]):
    ps.append([0, 0])

bsy = 0 # A program is running
pon = None  # Program on (Holds program number of a running program)
sbits = [0] * (sd["nbrd"] + 1)  # Used to display stations that are on in UI

rs = []  # run schedule
for j in range(sd["nst"]):
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
        _("System name"),
        "string",
        "name",
        _("Unique name of this SIP system."),
        _("System"),
    ],
    [
        _("Location"),
        "string",
        "loc",
        _("City name or zip code. Use comma or + in place of space."),
        _("System"),
    ],
    [_("Language"), "list", "lang", _("Select language."), _("System")],
    [
        _("24-hour clock"),
        "boolean",
        "tf",
        _("Display times in 24 hour format (as opposed to AM/PM style.)"),
        _("System"),
    ],
    [_("HTTP port"), "int", "htp", _("HTTP port."), _("System")],
    [
        _("HTTP IP addr"),
        "string",
        "htip",
        _("IP Address used for HTTP server socket.  IPv4 or IPv6 address"),
        _("System"),
    ],
    [
        _("Use pigpio"),
        "boolean",
        "pigpio",
        _("GPIO Library to use. Default is RPi.GPIO"),
        _("System"),
    ],
    [
        _("Water Scaling"),
        "int",
        "wl",
        _("Water scaling (as %), between 0 and 100."),
        _("System"),
    ],
    [
        _("Enable passphrase"),
        "boolean",
        "upas",
        _("Minimal security. \nPrevent unauthorized users from accessing the system without a passphrase. \n*** Default is opendoor ***"),
        _("Manage Passphrase"),
    ],
    [
        _("Current passphrase"),
        "password",
        "opw",
        _("Enter the current passphrase. \n*** Defalut is opendoor ***"),
        _("Manage Passphrase"),
    ],
    [
        _("New passphrase"),
        "password",
        "npw",
        _("Enter a new passphrase."),
        _("Manage Passphrase"),
    ],
    [
        _("Confirm passphrase"),
        "password",
        "cpw",
        _("Confirm the new passphrase."),
        _("Manage Passphrase"),
    ],
    [
        _("Sequential"),
        "boolean",
        "seq",
        _("Sequential or concurrent running mode."),
        _("Station Handling"),
    ],
    [
        _("Individual Duration"),
        "boolean",
        "idd",
        _("Allow each station to have its own run time in programs."),
        _("Station Handling"),
    ],
    [
        _("Station extensions"),
        "int",
        "nbrd",
        _("Add 8 stations for each extension."),
        _("Station Handling"),
    ],
    [
        _("Station delay"),
        "int",
        "sdt",
        _("Station delay time (in seconds), between 0 and 240."),
        _("Station Handling"),
    ],
    [
        _("Active-Low Relay"),
        "boolean",
        "alr",
        _("Using active-low relay boards connected through shift registers"),
        _("Station Handling"),
    ],
    [
        _("Master station"),
        "int",
        "mas",
        _("Select master station."),
        _("Configure Master"),
    ],
    [
        _("Master on delay"),
        "int",
        "mton",
        _("Master on delay (in seconds), between -60 and +60."),
        _("Configure Master"),
    ],
    [
        _("Master off delay"),
        "int",
        "mtoff",
        _("Master off delay (in seconds), between -60 and +60."),
        _("Configure Master"),
    ],
    [
        _("Use rain sensor"),
        "boolean",
        "urs",
        _("Use rain sensor."),
        _("Rain Sensor"),
    ],
    [
        _("Normally open"),
        "boolean",
        "rst",
        _("Rain sensor type."),
        _("Rain Sensor"),
    ],
    [
        _("Enable logging"),
        "boolean",
        "lg",
        _(
            "Log all events - note that repetitive writing to an SD card can shorten its lifespan."
        ),
        _("Logging"),
    ],
    [
        _("Max log entries"),
        "int",
        "lr",
        _("Length of log to keep, 0=no limits."),
        _("Logging"),
    ],
]
