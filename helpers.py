# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
import six
from six.moves import range

# standard library imports
import ast
import codecs
import datetime
import errno
from functools import reduce
from hashlib import sha256
import io
import json
import os
import subprocess
import sys
from threading import Thread
import time

# local module imports
from blinker import signal
import gv
import i18n
from web.webapi import seeother
import web
from web import form
try:
    from gpio_pins import GPIO, pin_rain_sense, pin_relay
    if gv.use_pigpio:
        import pigpio
        pi = pigpio.pi()
except ImportError:
    print(u"error importing GPIO pins into helpers")
    pass

##############################
#### Function Definitions ####

station_completed = signal(u"station_completed")


def report_station_completed(station):
    """
    Send blinker signal indicating that a station has completed.
    Include the station number as data.
    """
    station_completed.send(station)


stations_scheduled = signal(u"stations_scheduled")


def report_stations_scheduled(txt=None):
    """
    Send blinker signal indicating that stations had been scheduled.
    """
    stations_scheduled.send(u"SIP", txt = txt)


rain_changed = signal(u"rain_changed")


def report_rain_changed(txt=None):
    """
    Send blinker signal indicating that rain sensor changed.
    """
    rain_changed.send()


restarting = signal(u"restart")  #: Signal to send on software restart


def report_restart():
    """
    Send blinker signal indicating system will restart.
    """
    restarting.send()


def reboot(wait=1, block=False):
    """
    Reboots the Raspberry Pi from a new thread.
    Set to True at start of thread (recursive).
    """
    if block:
        from gpio_pins import set_output

        gv.srvals = [0] * (gv.sd[u"nst"])
        set_output()
        if gv.use_pigpio:
            pass
        else:
            GPIO.cleanup()
        time.sleep(wait)
        try:
            print(_(u"Rebooting..."))
        except Exception:
            pass
        subprocess.Popen([u"reboot"])
    else:
        t = Thread(target=reboot, args=(wait, True))
        t.start()


def poweroff(wait=1, block=False):
    """
    Powers off the Raspberry Pi from a new thread.
    Set to True at start of thread (recursive).
    """
    if block:
        from gpio_pins import set_output

        gv.srvals = [0] * (gv.sd[u"nst"])
        set_output()
        if gv.use_pigpio:
            pass
        else:
            GPIO.cleanup()
        time.sleep(wait)
        try:
            print(_(u"Powering off..."))
        except Exception:
            pass
        subprocess.Popen([u"poweroff"])
    else:
        t = Thread(target=poweroff, args=(wait, True))
        t.start()


def restart(wait=1, block=False):
    """
    Restarts the software from a new thread.
    Set to True at start of thread (recursive).
    """
    if block:
        report_restart()
        from gpio_pins import set_output

        gv.srvals = [0] * (gv.sd[u"nst"])
        set_output()
        if gv.use_pigpio:
            pass
        else:
            GPIO.cleanup()
        time.sleep(wait)
        try:
            print(_(u"Restarting..."))
        except Exception:
            pass
        gv.restarted = 0
        pid = os.getpid()
        command = u"systemctl status " + str(pid)
        output = str(subprocess.check_output(command.split()))
        unit_name = output.split()[1]
        command = u"systemctl restart " + unit_name    
        subprocess.Popen(command.split())
    else:
        t = Thread(target=restart, args=(wait, True))
        t.start()


def uptime():
    """
    Returns UpTime for RPi
    """
    string = u"Error 1: uptime"

    with open(u"/proc/uptime") as f:
        total_sec = float(f.read().split()[0])
        string = str(datetime.timedelta(seconds=total_sec)).split(u".")[0]

    return string


def get_ip():
    """
    Returns the IP address of the system if available.
    """
    try:
        arg = u"ip route list"
        p = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        data = p.communicate()
        split_data = data[0].split()
        ipaddr = split_data[split_data.index(u"src") + 1]
        return ipaddr
    except:
        return u"No IP Settings"


def get_rpi_revision():
    """
    Returns the hardware revision of the Raspberry Pi
    using the RPI_REVISION method from RPi.GPIO.
    """
    try:
        import RPi.GPIO as GPIO

        return GPIO.RPI_REVISION
    except ImportError:
        return 0


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def check_rain():
    """
    Checks status of an installed rain sensor.
    Handles normally open and normally closed rain sensors
    Sets gv.sd["rs"] to 1 if rain is detected otherwise 0.
    """

    global pi
    try:
        if gv.sd[u"rst"] == 1:  # Rain sensor type normally open (default)
            if gv.use_pigpio:
                if not pi.read(pin_rain_sense):  # Rain detected
                    gv.sd[u"rs"] = 1
                else:
                    gv.sd[u"rs"] = 0
            else:
                if (
                    GPIO.input(pin_rain_sense) == gv.sd[u"rs"]
                ):  #  Rain sensor changed, reading and gv.sd["rs"] are inverse.
                    report_rain_changed()
                    gv.sd[u"rs"] = 1 - gv.sd[u"rs"]  #  toggle
        elif gv.sd[u"rst"] == 0:  # Rain sensor type normally closed
            if gv.use_pigpio:
                if pi.read(pin_rain_sense):  # Rain detected
                    gv.sd[u"rs"] = 1
                else:
                    gv.sd[u"rs"] = 0
            else:
                if GPIO.input(pin_rain_sense) != gv.sd[u"rs"]:  # Rain sensor changed
                    report_rain_changed()
                    gv.sd[u"rs"] = 1 - gv.sd[u"rs"]  #  toggle
    except NameError:
        pass


def clear_mm():
    """
    Clear manual mode settings and stop any running zones.
    """
    from gpio_pins import set_output

    if gv.sd[u"mm"]:
        gv.sbits = [0] * (gv.sd[u"nbrd"] + 1)
        gv.ps = []
        for i in range(gv.sd[u"nst"]):
            gv.ps.append([0, 0])
        gv.rs = []
        for i in range(gv.sd[u"nst"]):
            gv.rs.append([0, 0, 0, 0])
        gv.srvals = [0] * (gv.sd[u"nst"])
        set_output()
    return


def plugin_adjustment():
    """
    Sums irrigation time (water level) adjustments from multiple plugins.

    The adjustment value output from a plugin must be
    a unique element in the gv.sd dictionary with a key starting with "wl_"
    """
    duration_adjustments = [gv.sd[entry] for entry in gv.sd if entry.startswith(u"wl_")]
    result = reduce(lambda x, y: x * y / 100.0, duration_adjustments, 1.0)
    return result


def get_cpu_temp():
    """
    Reads and returns the Celsius temperature of the CPU if available.
#     If unit is F, temperature is returned as Fahrenheit otherwise Celsius.
    """
    try:
        if gv.platform == u"bo":
            res = os.popen(u"cat /sys/class/hwmon/hwmon0/device/temp1_input").readline()
            temp = u"" + str(int(res / 1000.0))
        elif gv.platform == u"pi":
            command = u"cat /sys/class/thermal/thermal_zone0/temp"
            output = int(subprocess.check_output(command.split()))
            temp = int(output / 1000.0)
        else:
            return u""
        return temp
    except Exception:
        return u""


def timestr(t):
    """
    Convert duration in seconds to string in the form mm:ss.
    """
    return (
        str((t // 60 >> 0) // 10 >> 0)
        + str((t // 60 >> 0) % 10)
        + u":"
        + str((t % 60 >> 0) // 10 >> 0)
        + str((t % 60 >> 0) % 10)
    )


def log_run():
    """
    Add run data to json log file - most recent first.
    If a record limit is specified (gv.sd["lr"]) the number of records is truncated.
    """

    if gv.sd[u"lg"]:
        program = "program" #  _(u"program")
        station = "station" #  _(u"station")
        duration = "duration" #  _(u"duration")
        strt = "start" #  _(u"start")
        date = "date" #  _(u"date")
        if gv.lrun[1] == 0:  # skip program 0
            return
        elif gv.lrun[1] == 98:
            pgr = _(u"Run-once")
        elif gv.lrun[1] == 99:
            pgr = _(u"Manual")
        else:
            pgr = u"" + str(gv.lrun[1])
        start = time.gmtime(gv.now - gv.lrun[2])
        logline = (
            u'{"'
            + program
            + u'":"'
            + pgr
            + u'","'
            + station
            + u'":'
            + str(gv.lrun[0])
            + u',"'
            + duration
            + u'":"'
            + timestr(gv.lrun[2])
            + u'","'
            + strt
            + u'":"'
            + time.strftime(u'%H:%M:%S","' + date + u'":"%Y-%m-%d"', start)
            + u"}"
        )
        lines = []
        lines.append(logline + u"\n")
        log = read_log()
        for r in log:
            lines.append(json.dumps(r) + u"\n")
        with codecs.open(u"./data/log.json", u"w", encoding=u"utf-8") as f:
            if gv.sd[u"lr"]:
                f.writelines(lines[: gv.sd[u"lr"]])
            else:
                f.writelines(lines)
    return


def prog_match(prog):
    """
    Test a program for current date and time match.
    """
    if not prog[u"enabled"]:
        return 0  # Skip if program is not enabled
    devday = int(gv.now // 86400)  # Check day match
    lt = time.gmtime(gv.now)
    if prog[u"type"] == u"interval":
        if (devday % prog[u"interval_base_day"]) != prog[u"day_mask"]:
            return 0
    else:  # Weekday program
        if not prog[u"day_mask"] - 128 & 1 << lt.tm_wday:
            return 0
        if prog[u"type"] == u"evendays":
            if lt.tm_mday % 2 != 0:
                return 0
        if prog[u"type"] == u"odddays":
            if lt.tm_mday == 31 or ((lt.tm_mon == 2 and lt.tm_mday == 29)):
                return 0
            elif lt.tm_mday % 2 != 1:
                return 0
    this_minute = (lt.tm_hour * 60) + lt.tm_min  # Check time match
    if this_minute < prog[u"start_min"] or this_minute >= prog[u"stop_min"]:
        return 0
    if (
        prog[u"cycle_min"] == 0
        and (this_minute == prog[u"start_min"])
    ):
        return 1  # Program matched
    elif (
        prog[u"cycle_min"] != 0
        and (this_minute - prog[u"start_min"]) // prog[u"cycle_min"]
     * prog[u"cycle_min"] == this_minute - prog[u"start_min"]
    ):
        return 1  # Program matched
    return 0


def schedule_stations(stations):
    """
    Schedule stations/valves/zones to run.
    """
    if (gv.sd[u"rd"]   #  If rain delay or rain detected by sensor
        or (gv.sd[u"urs"]
            and gv.sd[u"rs"]
            )
        ):
        rain = True
    else:
        rain = False
    accumulate_time = gv.now
    if gv.sd[u"seq"]:  # sequential mode, stations run one after another
        for b in range(len(stations)): # stations is a list of bitmasks
            for s in range(8):
                sid = b * 8 + s  # station index
                if gv.rs[sid][2]:  # if station has a duration value
                    if (
                        not rain
                        or gv.sd[u"ir"][b] & 1 << s
                    ):  # if no rain or station ignores rain
                        gv.rs[sid][0] = accumulate_time  # start at accumulated time
                        accumulate_time += gv.rs[sid][2]  # add duration
                        gv.rs[sid][1] = accumulate_time  # set new stop time
                        accumulate_time += gv.sd[u"sdt"]  # add station delay
                        report_stations_scheduled()
                        gv.sd[u"bsy"] = 1
                    else:
                        gv.sbits[b] &= ~1 << s
                        gv.ps[s] = [0, 0]
    else:  # concurrent mode, stations allowed to run in parallel
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s  # station index
                if (not stations[b] & 1 << s
                    or gv.srvals[sid]  # - test
                    ):  # skip stations not in prog or already running
                    continue
                if gv.rs[sid][2]:  # if station has a duration value
                    if (not rain
                        or gv.sd[u"ir"][b] & 1 << s
                    ):  # if no rain or station ignores rain
                        gv.rs[sid][0] = gv.now  # set start time
                        gv.rs[sid][1] = gv.now + gv.rs[sid][2]  # set stop time
                        report_stations_scheduled()
                        gv.sd[u"bsy"] = 1
                    else:  # if rain and station does not ignore, clear station from display
                        gv.sbits[b] &= ~1 << s
                        gv.ps[s] = [0, 0]
    report_stations_scheduled()  # - test
    gv.sd[u"bsy"] = 1  # - test
    return


def stop_onrain():
    """
    Stop stations that do not ignore rain.
    """

    from gpio_pins import set_output

    do_set_output = False
    for b in range(gv.sd[u"nbrd"]):
        for s in range(8):
            sid = b * 8 + s  # station index
            if gv.sd[u"ir"][b] & 1 << s:  # if station ignores rain...
                continue
            elif not all(v == 0 for v in gv.rs[sid]):
                gv.srvals[sid] = 0
                do_set_output = True
                gv.sbits[b] &= ~1 << s  # Clears stopped stations from display
                gv.ps[sid] = [0, 0]
                gv.rs[sid] = [0, 0, 0, 0]

    if do_set_output:
        set_output()
    return


def stop_stations():
    """
    Stop all running stations, clear schedules.
    """
    from gpio_pins import set_output

    gv.srvals = [0] * (gv.sd[u"nst"])
    set_output()
    gv.ps = []
    for i in range(gv.sd[u"nst"]):
        gv.ps.append([0, 0])
    gv.sbits = [0] * (gv.sd[u"nbrd"] + 1)
    gv.rs = []
    for i in range(gv.sd[u"nst"]):
        gv.rs.append([0, 0, 0, 0])
    gv.sd[u"bsy"] = 0
    return


def read_log():
    """
    Read data from irrigation log file.
    """
    result = []
    try:
        with io.open(u"./data/log.json") as logf:
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
    """
    Save data to a json file.
    """
    with open(u"./data/" + fname + u".json", u"w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def station_names():
    """
    Load station names from /data/stations.json file if it exists
    otherwise create file with defaults.

    Return station names as a list.
    """
    try:
        with open(u"./data/snames.json", u"r") as snf:
            return json.load(snf)
    except IOError as e:
        report_error(u"station_names function", e)
        stations = [u"S01", u"S02", u"S03", u"S04", u"S05", u"S06", u"S07", u"S08"]
        jsave(stations, u"snames")
        return stations


def load_programs():
    """
    Load program data into memory from /data/programData.json file if it exists.
    Otherwise create an empty programs data list (gv.pd) or convert from old style format.
    """
    try:
        with open(u"./data/programData.json", u"r") as pf:
            gv.pd = json.load(pf)
    except IOError:
        #  Check if programs.json file exists (old format) and if so, run conversion
        if os.path.isfile(u"./data/programs.json"):
            import convert_progs

            gv.pd = convert_progs.convert()
        else:
            gv.pd = []  # A config file -- create empty file if not found.
        with open(u"./data/programData.json", u"w") as pf:
            json.dump(gv.pd, pf, indent=4, sort_keys=True)
    return gv.pd


def password_hash(passphrase):
    """
    Generate passphrase hash using sha256.
    """
    pwd_hash = sha256(passphrase.encode()).hexdigest()
    return pwd_hash


########################
#### Login Handling ####


def check_login(redirect=False):
    """
    Check login.
    """
    qdict = web.input()
    try:
        if gv.sd[u"upas"] == 0:
            return True

        if web.config._session.user == u"admin":
            return True
    except KeyError:
        pass

    if u"pw" in qdict:
        if gv.sd[u"passphrase"] == password_hash(qdict[u"pw"]):
            return True
        if redirect:
            raise web.unauthorized()
        return False

    if redirect:
        raise web.seeother(u"/login")
    return False


signin_form = form.Form(
    form.Password(
        name=u'password', description=_(u"Passphrase") + u":", value=u''
        ),

    validators=[
        form.Validator(
            _(u"Incorrect passphrase, please try again"),
            lambda x: gv.sd[u"passphrase"] == password_hash(x.password),
        )
    ],
)


def get_input(qdict, key, default=None, cast=None):
    """
    Checks data returned from a UI web page.
    """
    result = default
    if key in qdict:
        result = qdict[key]
        if cast is not None:
            result = cast(result)
    return result


def report_error(title, message=None):
    """
    All errors are reported here
    """

    print('SIP error: --------------')
    print(title, message)
    return
