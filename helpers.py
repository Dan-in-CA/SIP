# -*- coding: utf-8 -*-

import os
import random
import sys
import time
from gpio_pins import set_output

try:
    from gpio_pins import pin_rain_sense, GPIO
except ImportError:
    pass

import web
from web import form


import gv
from web.session import sha1

__author__ = 'Rimco'

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print "Error: json module not found"
        sys.exit()

##############################
#### Function Definitions ####

def baseurl():
    """Return URL app is running under."""
    result = web.ctx['home']
    return result


def check_rain():
    try:
        if gv.sd['rst'] == 0:
            if GPIO.input(pin_rain_sense): # Rain detected
                gv.sd['rs'] = 1
            else:
                gv.sd['rs'] = 0
        elif gv.sd['rst'] == 1:
            if not GPIO.input(pin_rain_sense):
                gv.sd['rs'] = 1
            else:
                gv.sd['rs'] = 0
    except NameError:
        pass


def clear_mm():
    """Clear manual mode settings."""
    if gv.sd['mm']:
        gv.sbits = [0] * (gv.sd['nbrd'] + 1)
        gv.ps = []
        for i in range(gv.sd['nst']):
            gv.ps.append([0, 0])
        gv.rs = []
        for i in range(gv.sd['nst']):
            gv.rs.append([0, 0, 0, 0])
        gv.srvals = [0] * (gv.sd['nst'])
        set_output()
    return


def plugin_adjustment():
    duration_adjustments = [gv.sd[entry] for entry in gv.sd if entry.startswith('wl_')]
    result = reduce(lambda x, y: x * y / 100, duration_adjustments, 1.0)
    return result


def CPU_temperature(unit=None):
    """Returns the temperature of the CPU if available."""
    try:
        if gv.platform == 'bo':
            res = os.popen('cat /sys/class/hwmon/hwmon0/device/temp1_input').readline()
            temp = str(int(float(res) / 1000))
        elif gv.platform == 'pi':
            res = os.popen('vcgencmd measure_temp').readline()
            temp = res.replace("temp=", "").replace("'C\n", "")
        else:
            temp = str(0)

        if unit == 'F':
            return str(9.0/5.0*float(temp)+32)
        elif unit is not None:
            return str(float(temp))
        else:
            return temp
    except Exception:
        return '!!'


def timestr(t):
    return str((t / 60 >> 0) / 10 >> 0) + str((t / 60 >> 0) % 10) + ":" + str((t % 60 >> 0) / 10 >> 0) + str(
        (t % 60 >> 0) % 10)


def log_run():
    """add run data to csv file - most recent first."""
    if gv.sd['lg']:
        if gv.lrun[1] == 98:
            pgr = 'Run-once'
        elif gv.lrun[1] == 99:
            pgr = 'Manual'
        else:
            pgr = str(gv.lrun[1])

        start = time.gmtime(gv.now - gv.lrun[2])
        logline = '{"program":"' + pgr + '","station":' + str(gv.lrun[0]) + ',"duration":"' + timestr(
            gv.lrun[2]) + '","start":"' + time.strftime('%H:%M:%S","date":"%Y-%m-%d"', start) + '}\n'
        log = read_log()
        log.insert(0, logline)
        with open('./data/log.json', 'w') as f:
            if gv.sd['lr']:
                f.writelines(log[:gv.sd['lr']])
            else:
                f.writelines(log)
    return


def prog_match(prog):
    """Test a program for current date and time match."""
    if not prog[0]: return 0 # Skip if program is not enabled
    devday = int(gv.now / 86400) # Check day match
    lt = time.gmtime(gv.now)
    if (prog[1] >= 128) and (prog[2] > 1): # Inverval program
        if (devday % prog[2]) != (prog[1] - 128): return 0
    else: # Weekday program
        if not prog[1] - 128 & 1 << lt[6]: return 0
        if prog[1] >= 128 and prog[2] == 0: # even days
            if lt[2] % 2 != 0: return 0
        if prog[1] >= 128 and prog[2] == 1: # Odd days
            if lt[2] == 31 or (lt[1] == 2 and lt[2] == 29):
                return 0
            elif lt[2] % 2 != 1:
                return 0
    this_minute = (lt[3] * 60) + lt[4] # Check time match
    if this_minute < prog[3] or this_minute >= prog[4]: return 0
    if prog[5] == 0: return 0
    if ((this_minute - prog[3]) / prog[5]) * prog[5] == this_minute - prog[3]:
        return 1 # Program matched
    return 0


def schedule_stations(stations):
    """Schedule stations/valves/zones to run."""
    if gv.sd['rd'] or (gv.sd['urs'] and gv.sd['rs']): # If rain delay or rain detected by sensor
        rain = True
    else:
        rain = False
    accumulate_time = gv.now
    if gv.sd['seq']: # sequential mode, stations run one after another
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s # station index
                if gv.rs[sid][2]: # if station has a duration value
                    if not rain or gv.sd['ir'][b] & 1 << s: # if no rain or station ignores rain
                        gv.rs[sid][0] = accumulate_time # start at accumulated time
                        accumulate_time += gv.rs[sid][2] # add duration
                        gv.rs[sid][1] = accumulate_time # set new stop time
                        accumulate_time += gv.sd['sdt'] # add station delay
                    else:
                        gv.sbits[b] &= ~1 << s
                        gv.ps[s] = [0, 0]

    else: # concurrent mode, stations allowed to run in parallel
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s # station index
                if not stations[b] & 1 << s: # skip stations not in prog
                    continue
                if gv.rs[sid][2]: # if station has a duration value
                    if not rain or gv.sd['ir'][b] & 1 << s: # if no rain or station ignores rain
                        gv.rs[sid][0] = gv.now # accumulate_time # set start time
                        gv.rs[sid][1] = (gv.now + gv.rs[sid][2]) # set stop time
                    else: # if rain and station does not ignore, clear station from display
                        gv.sbits[b] &= ~1 << s
                        gv.ps[s] = [0, 0]
    gv.sd['bsy'] = 1
    return


def stop_onrain():
    """Stop stations that do not ignore rain."""
    for b in range(gv.sd['nbrd']):
        for s in range(8):
            sid = b * 8 + s # station index
            if gv.sd['ir'][b] & 1 << s: # if station ignores rain...
                continue
            elif not all(v == 0 for v in gv.rs[sid]):
                gv.srvals[sid] = 0
                set_output()
                gv.sbits[b] &= ~1 << s# Clears stopped stations from display
                gv.ps[sid] = [0, 0]
                gv.rs[sid] = [0, 0, 0, 0]
    return


def stop_stations():
    """Stop all running stations, clear schedules."""
    gv.srvals = [0] * (gv.sd['nst'])
    set_output()
    gv.ps = []
    for i in range(gv.sd['nst']):
        gv.ps.append([0, 0])
    gv.sbits = [0] * (gv.sd['nbrd'] + 1)
    gv.rs = []
    for i in range(gv.sd['nst']):
        gv.rs.append([0, 0, 0, 0])
    gv.sd['bsy'] = 0
    return


def data(dataf):
    """Return contents of requested text file as string or create file if a missing config file."""
    try:
        with open('./data/' + dataf + '.txt', 'r') as f:
            data = f.read()
            return data
    except IOError:
        return None


def save(dataf, datastr):
    """Save data to text file. dataf = file to save to, datastr = data string to save."""
    with open('./data/' + dataf + '.txt', 'w') as f:
        f.write(datastr)
    return


def read_log():
    try:
        with open('./data/log.json') as logf:
            records = logf.readlines()
        return records
    except IOError:
        return []


def jsave(data, fname):
    """Save data to a json file."""
    with open('./data/' + fname + '.json', 'w') as f:
        json.dump(data, f)


def station_names():
    """Load station names from file if it exists otherwise create file with defaults."""
    try:
        with open('./data/snames.json', 'r') as snf:
#             stations = json.load(snf)
#             return stations
            return json.load(snf)
    except IOError:
        stations = [u"S01", u"S02", u"S03", u"S04", u"S05", u"S06", u"S07", u"S08" ]
        jsave(stations, 'snames')
        return stations


def load_programs():
    """Load program data from json file, if it exists, into memory, otherwise create an empty programs var."""
    try:
        with open('./data/programs.json', 'r') as pf:
            gv.pd = json.load(pf)
    except IOError:
        gv.pd = [] # A config file -- return default and create file if not found.
        with open('./data/programs.json', 'w') as pf:
            json.dump(gv.pd, pf)
    return gv.pd

def passwordSalt():
    return "".join(chr(random.randint(33, 127)) for _ in xrange(64))


def passwordHash(password, salt):
    return sha1(password + salt).hexdigest()


########################
#### Login Handling ####

def checkLogin():
    qdict = web.input()

    try:
        if gv.sd['ipas'] == 1:
            return True

        if web.config._session.user == 'admin':
            return True
    except KeyError:
        pass

    if qdict.has_key('pw'):
        if gv.sd['password'] == passwordHash(qdict['pw'], gv.sd['salt']):
            return True
        raise web.unauthorized()

    raise web.seeother('/login')


signin_form = form.Form(
    form.Password('password', description='Password:'),
    validators=[
        form.Validator(
            "Incorrect password, please try again",
            lambda x: gv.sd['password'] == passwordHash(x.password, gv.sd['salt'])
        )
    ]
)

