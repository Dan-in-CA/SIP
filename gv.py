# !/usr/bin/python
# -*- coding: utf-8 -*-

##############################
#### Revision information ####
import subprocess

major_ver = 2
minor_ver = 1

try:
    revision = int(subprocess.check_output(['git', 'rev-list', '--count', '--first-parent', 'HEAD']))
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

