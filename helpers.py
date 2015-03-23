# -*- coding: utf-8 -*-


import i18n

import datetime
from threading import Thread
import os
import random
import sys
import time
import subprocess
import io
import ast
from web.webapi import seeother

try:
    from gpio_pins import GPIO, pin_rain_sense
except ImportError:
    print 'error importing GPIO pins into helpers'
    pass

import web
from web import form

import gv
from web.session import sha1

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print _("Error: json module not found")
        sys.exit()


##############################
#### Function Definitions ####

def reboot(wait=1, block=False):
    if block:
        from gpio_pins import set_output
        gv.srvals = [0] * (gv.sd['nst'])
        set_output()
        GPIO.cleanup()
        time.sleep(wait)
        try:
            print _('Rebooting...')
        except Exception:
            pass
        subprocess.Popen(['reboot'])
    else:
        t = Thread(target=reboot, args=(wait, True))
        t.start()


def poweroff(wait=1, block=False):
    if block:
        from gpio_pins import set_output
        gv.srvals = [0] * (gv.sd['nst'])
        set_output()
        GPIO.cleanup()
        time.sleep(wait)
        try:
            print _('Powering off...')
        except Exception:
            pass
        subprocess.Popen(['poweroff'])
    else:
        t = Thread(target=poweroff, args=(wait, True))
        t.start()


def restart(wait=1, block=False):
    if block:
        from gpio_pins import set_output
        gv.srvals = [0] * (gv.sd['nst'])
        set_output()
        try:
            GPIO.cleanup()
        except Exception:
            pass
        time.sleep(wait)
        try:
            print _('Restarting...')
        except Exception:
            pass
        subprocess.Popen('service ospi restart'.split())
    else:
        t = Thread(target=restart, args=(wait, True))
        t.start()


def uptime():
    """Returns UpTime for RPi"""
    string = 'Error 1: uptime'

    with open("/proc/uptime") as f:
        total_sec = float(f.read().split()[0])
        string = str(datetime.timedelta(seconds=total_sec)).split('.')[0]

    return string


def get_ip():
    """Returns the IP adress if available."""
    try:
        arg = 'ip route list'
        p = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        data = p.communicate()
        split_data = data[0].split()
        ipaddr = split_data[split_data.index('src') + 1]
        return ipaddr
    except:
        return "No IP Settings"


def get_rpi_revision():
    try:
        import RPi.GPIO as GPIO

        return GPIO.RPI_REVISION
    except ImportError:
        return 0


def check_rain():
    try:
        if gv.sd['rst'] == 1:  # Rain sensor type normally open (default)
            if not GPIO.input(pin_rain_sense):  # Rain detected
                gv.sd['rs'] = 1
            else:
                gv.sd['rs'] = 0
        elif gv.sd['rst'] == 0:  # Rain sensor type normally closed
            if GPIO.input(pin_rain_sense):  # Rain detected
                gv.sd['rs'] = 1
            else:
                gv.sd['rs'] = 0
    except NameError:
        pass



def clear_mm():
    """Clear manual mode settings."""
    from gpio_pins import set_output
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


def get_cpu_temp(unit=None):
    """Returns the temperature of the CPU if available."""

    try:
        if gv.platform == 'bo':
            res = os.popen('cat /sys/class/hwmon/hwmon0/device/temp1_input').readline()
            temp = str(int(float(res) / 1000))
        elif gv.platform == 'pi':
            command = "cat /sys/class/thermal/thermal_zone0/temp"
            output = subprocess.check_output(command.split())
            temp = str(int(float(output) / 1000))
        else:
            temp = str(0)

        if unit == 'F':
            return str(1.8 * float(temp) + 32)
#            return str(9.0 / 5.0 * float(temp) + 32)
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
            pgr = _('Run-once')
        elif gv.lrun[1] == 99:
            pgr = _('Manual')
        else:
            pgr = str(gv.lrun[1])
        start = time.gmtime(gv.now - gv.lrun[2])
        logline = '{"program":"' + pgr + '","station":' + str(gv.lrun[0]) + ',"duration":"' + timestr(
            gv.lrun[2]) + '","start":"' + time.strftime('%H:%M:%S","date":"%Y-%m-%d"', start) + '}'
        lines = []
        lines.append(logline + '\n')
        log = read_log()
        for r in log:
            lines.append(json.dumps(r) + '\n')
        with open('./data/log.json', 'w') as f:
            if gv.sd['lr']:
                f.writelines(lines[:gv.sd['lr']])
            else:
                f.writelines(lines)
    return


def prog_match(prog):
    """Test a program for current date and time match."""
    if not prog[0]:
        return 0  # Skip if program is not enabled
    devday = int(gv.now / 86400)  # Check day match
    lt = time.gmtime(gv.now)
    if (prog[1] >= 128) and (prog[2] > 1):  # Interval program
        if (devday % prog[2]) != (prog[1] - 128):
            return 0
    else:  # Weekday program
        if not prog[1] - 128 & 1 << lt[6]:
            return 0
        if prog[1] >= 128 and prog[2] == 0:  # even days
            if lt[2] % 2 != 0:
                return 0
        if prog[1] >= 128 and prog[2] == 1:  # Odd days
            if lt[2] == 31 or (lt[1] == 2 and lt[2] == 29):
                return 0
            elif lt[2] % 2 != 1:
                return 0
    this_minute = (lt[3] * 60) + lt[4]  # Check time match
    if this_minute < prog[3] or this_minute >= prog[4]:
        return 0
    if prog[5] == 0:
        return 0
    if ((this_minute - prog[3]) / prog[5]) * prog[5] == this_minute - prog[3]:
        return 1  # Program matched
    return 0


def schedule_stations(stations):
    """Schedule stations/valves/zones to run."""
    if gv.sd['rd'] or (gv.sd['urs'] and gv.sd['rs']):  # If rain delay or rain detected by sensor
        rain = True
    else:
        rain = False
    accumulate_time = gv.now
    if gv.sd['seq']:  # sequential mode, stations run one after another
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s  # station index
                if gv.rs[sid][2]:  # if station has a duration value
                    if not rain or gv.sd['ir'][b] & 1 << s:  # if no rain or station ignores rain
                        gv.rs[sid][0] = accumulate_time  # start at accumulated time
                        accumulate_time += gv.rs[sid][2]  # add duration
                        gv.rs[sid][1] = accumulate_time  # set new stop time
                        accumulate_time += gv.sd['sdt']  # add station delay
                    else:
                        gv.sbits[b] &= ~1 << s
                        gv.ps[s] = [0, 0]
    else:  # concurrent mode, stations allowed to run in parallel
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s  # station index
                if not stations[b] & 1 << s:  # skip stations not in prog
                    continue
                if gv.rs[sid][2]:  # if station has a duration value
                    if not rain or gv.sd['ir'][b] & 1 << s:  # if no rain or station ignores rain
                        gv.rs[sid][0] = gv.now  # accumulate_time # set start time
                        gv.rs[sid][1] = (gv.now + gv.rs[sid][2])  # set stop time
                    else:  # if rain and station does not ignore, clear station from display
                        gv.sbits[b] &= ~1 << s
                        gv.ps[s] = [0, 0]
    gv.sd['bsy'] = 1
    return


def stop_onrain():
    """Stop stations that do not ignore rain."""

    from gpio_pins import set_output
    for b in range(gv.sd['nbrd']):
        for s in range(8):
            sid = b * 8 + s  # station index
            if gv.sd['ir'][b] & 1 << s:  # if station ignores rain...
                continue
            elif not all(v == 0 for v in gv.rs[sid]):
                gv.srvals[sid] = 0
                set_output()
                gv.sbits[b] &= ~1 << s  # Clears stopped stations from display
                gv.ps[sid] = [0, 0]
                gv.rs[sid] = [0, 0, 0, 0]
    return


def stop_stations():
    """Stop all running stations, clear schedules."""
    from gpio_pins import set_output
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


def read_log():
      result = []
      try:
          with io.open('./data/log.json') as logf:
              records = logf.readlines()
              for i in records:
                  try:
                      rec = ast.literal_eval(json.loads(i))
                  except ValueError:
                      rec = json.loads(i)
                  result.append(rec)
          return result
      except IOError:
          return result


def jsave(data, fname):
    """Save data to a json file."""
    with open('./data/' + fname + '.json', 'w') as f:
        json.dump(data, f)


def station_names():
    """Load station names from file if it exists otherwise create file with defaults."""
    try:
        with open('./data/snames.json', 'r') as snf:
            return json.load(snf)
    except IOError:
        stations = [u"S01", u"S02", u"S03", u"S04", u"S05", u"S06", u"S07", u"S08"]
        jsave(stations, 'snames')
        return stations


def load_programs():
    """Load program data from json file, if it exists, into memory, otherwise create an empty programs var."""
    try:
        with open('./data/programs.json', 'r') as pf:
            gv.pd = json.load(pf)
    except IOError:
        gv.pd = []  # A config file -- return default and create file if not found.
        with open('./data/programs.json', 'w') as pf:
            json.dump(gv.pd, pf)
    return gv.pd


def password_salt():
    return "".join(chr(random.randint(33, 127)) for _ in xrange(64))


def password_hash(password, salt):
    return sha1(password + salt).hexdigest()


########################
#### Login Handling ####

def check_login(redirect=False):
    qdict = web.input()

    try:
        if gv.sd['ipas'] == 1:
            return True

        if web.config._session.user == 'admin':
            return True
    except KeyError:
        pass

    if 'pw' in qdict:
        if gv.sd['password'] == password_hash(qdict['pw'], gv.sd['salt']):
            return True
        if redirect:
            raise web.unauthorized()
        return False

    if redirect:
        raise web.seeother('/login')
    return False


signin_form = form.Form(
    form.Password('password', description = _('Password') + ':'),
    validators=[
        form.Validator(
            _("Incorrect password, please try again"),
            lambda x: gv.sd['password'] == password_hash(x.password, gv.sd['salt'])
        )
    ]
)


def get_input(qdict, key, default=None, cast=None):
    result = default
    if key in qdict:
        result = qdict[key]
        if cast is not None:
            result = cast(result)
    return result
