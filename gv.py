# !/usr/bin/python
# -*- coding: utf-8 -*-

#####################
#### Global vars ####

# Settings Dictionary. A set of vars kept in memory and persisted in a file.
# Edit this default dictionary definition to add or remove "key": "value" pairs or change defaults.
# note old passwords stored in the "pwd" option will be lost - reverts to default password.
from calendar import timegm
import json
import time

platform = '' # must be done before the following import because gpio_pins will try to set it

from helpers import passwordSalt, passwordHash, load_programs, data, station_names

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
    u"salt": u"",
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
    u"salt": passwordSalt()
}

sd['password'] = passwordHash('opendoor', sd['salt'])

try:
    with open('./data/sd.json', 'r') as sdf: ## A config file ##
        sd_temp = json.load(sdf)
    for key in sd: # If file loaded, replce default values in sd with values from file
        if key in sd_temp:
            sd[key] = sd_temp[key]
except IOError: # If file does not exist, it will be created using defaults.
    with open('./data/sd.json', 'w') as sdf: # save file
        json.dump(sd, sdf)


now = timegm(time.localtime())
gmtnow = time.time()
plugin_menu = [] # Empty list of lists for plugin links (e.g. ['name', 'URL'])

srvals = [0] * (sd['nst']) # Shift Register values
rovals = [0] * sd['nbrd'] * 7 # Run Once durations
snames = station_names()
pd = load_programs() # Load program data from file

ps = [] # Program schedule (used for UI display)
for i in range(sd['nst']):
    ps.append([0, 0])

pon = None # Program on (Holds program number of a running program)
sbits = [0] * (sd['nbrd'] + 1) # Used to display stations that are on in UI

rs = [] # run schedule
for _ in range(sd['nst']):
    rs.append([0, 0, 0, 0]) # scheduled start time, scheduled stop time, duration, program index

lrun = [0, 0, 0, 0] # station index, program number, duration, end time (Used in UI)
scount = 0 # Station count, used in set station to track on stations with master association.
