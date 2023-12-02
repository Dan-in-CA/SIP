# -*- coding: utf-8 -*-

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
import math

# local module imports
from blinker import signal
from gpio_pins import set_output
import gv
import i18n
from web.webapi import seeother
import web
from web import form

try:
    from gpio_pins import GPIO, pin_rain_sense, pin_relay, set_output

    if gv.use_pigpio:
        import pigpio

        pi = pigpio.pi()
except ImportError:
    print("error importing GPIO pins into helpers")
    pass

##############################
#### Function Definitions ####

new_day = signal("new_day")

def report_new_day(txt=None):
    """
    Send blinker signal indicating that a new dy has strted.
    """
    new_day.send()
    

station_completed = signal("station_completed")

def report_station_completed(station):
    """
    Send blinker signal indicating that a station has completed.
    Include the station number as data.
    """
    station_completed.send(station)


stations_scheduled = signal("stations_scheduled")

def report_stations_scheduled(txt=None):
    """
    Send blinker signal indicating that stations had been scheduled.
    """
    stations_scheduled.send("SIP", txt=txt)


rain_changed = signal("rain_changed")


def report_rain_changed(txt=None):
    """
    Send blinker signal indicating that rain sensor changed.
    """
    rain_changed.send()


running_program_change = signal("running_program_change")

def report_running_program_change():
    """
    Send blinker signal indicating that running program changed.
    """
    running_program_change.send()


rain_delay_change = signal("rain_delay_change")

def report_rain_delay_change():
    """
    Send blinker signal indicating that rain delay changed.
    """
    rain_delay_change.send()


restarting = signal("restarting")  #: Signal to send on software restart


def report_restart(txt=None):
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
        gv.srvals = [0] * (gv.sd["nst"])
        set_output()
        if gv.use_pigpio:
            pass
        else:
            GPIO.cleanup()
        time.sleep(wait)
        try:
            print(_("Rebooting..."))
        except Exception:
            pass
        subprocess.Popen(["reboot"])
    else:
        t = Thread(target=reboot, args=(wait, True))
        t.start()


def poweroff(wait=1, block=False):
    """
    Powers off the Raspberry Pi from a new thread.
    Set to True at start of thread (recursive).
    """
    if block:
        gv.srvals = [0] * (gv.sd["nst"])
        set_output()
        if gv.use_pigpio:
            pass
        else:
            GPIO.cleanup()
        time.sleep(wait)
        try:
            print(_("Powering off..."))
        except Exception:
            pass
        subprocess.Popen(["poweroff"])
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
        gv.srvals = [0] * (gv.sd["nst"])
        set_output()
        if gv.use_pigpio:
            pass
        else:
            GPIO.cleanup()
        time.sleep(wait)
        try:
            print(_("Restarting..."))
        except Exception:
            pass
        gv.restarted = 0
        pid = os.getpid()
        command = "systemctl status " + str(pid)
        output = str(subprocess.check_output(command.split()))
        unit_name = output.split()[1]
        command = "systemctl restart " + unit_name
        subprocess.Popen(command.split())
    else:
        t = Thread(target=restart, args=(wait, True))
        t.start()


def uptime():
    """
    Returns UpTime for RPi
    """
    string = "Error 1: uptime"

    with open("/proc/uptime") as f:
        total_sec = float(f.read().split()[0])
        string = str(datetime.timedelta(seconds=total_sec)).split(".")[0]

    return string


def get_ip():
    """
    Returns the IP address of the system if available.
    """
    try:
        arg = "ip route list"
        p = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        data = p.communicate()
        split_data = data[0].decode(encoding="utf-8").split()
        ipaddr = split_data[split_data.index("src") + 1]
        return ipaddr
    except:
        return "No IP Settings"


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

    global pi, rain
    rain_sensor = gv.sd["rs"]
    try:
        if gv.sd["rst"] == 1:  # Rain sensor type normally open (default)
            if gv.use_pigpio:
                if not pi.read(pin_rain_sense):  # Rain detected
                    rain_sensor = 1
                else:
                    rain_sensor = 0
            else:
                if (
                    GPIO.input(pin_rain_sense) == rain_sensor
                ):  #  Rain sensor changed, reading and gv.sd["rs"] are inverse.
                    rain_sensor = 1 - rain_sensor  #  toggle
        elif gv.sd["rst"] == 0:  # Rain sensor type normally closed
            if gv.use_pigpio:
                if pi.read(pin_rain_sense):  # Rain detected
                    rain_sensor = 1
                else:
                    rain_sensor = 0
            else:
                if GPIO.input(pin_rain_sense) != rain_sensor:  # Rain sensor changed
                    rain_sensor = 1 - rain_sensor  #  toggle
    except NameError:
        pass

    if gv.sd["rs"] != rain_sensor:  # Update if rain sensor changed
        gv.sd["rs"] = rain_sensor
        report_rain_changed()


def clear_mm():
    """
    Clear manual mode settings and stop any running stations.
    """
    if gv.sd["mm"]:
        gv.sbits = [0] * (gv.sd["nbrd"] + 1)
        gv.ps = []
        for i in range(gv.sd["nst"]):
            gv.ps.append([0, 0])
        gv.rs = []
        for i in range(gv.sd["nst"]):
            gv.rs.append([0, 0, 0, 0])
        gv.srvals = [0] * (gv.sd["nst"])
        set_output()
    # return


def plugin_adjustment():
    """
    Sums irrigation time (water level) adjustments from multiple plugins.

    The adjustment value output from a plugin must be
    a unique element in the gv.sd dictionary with a key starting with "wl_"
    """
    duration_adjustments = [gv.sd[entry] for entry in gv.sd if entry.startswith("wl_")]
    result = reduce(lambda x, y: x * y / 100.0, duration_adjustments, 1.0)
    return result


def get_cpu_temp():
    """
    Reads and returns the Celsius temperature of the CPU if available.
#     If unit is F, temperature is returned as Fahrenheit otherwise Celsius.
    """
    try:
        if gv.platform == "bo":
            res = os.popen("cat /sys/class/hwmon/hwmon0/device/temp1_input").readline()
            temp = "" + str(int(res / 1000.0))
        elif gv.platform == "pi":
            command = "cat /sys/class/thermal/thermal_zone0/temp"
            output = int(subprocess.check_output(command.split()))
            temp = int(output / 1000.0)
        else:
            return ""
        return temp
    except Exception:
        return ""
    
def total_adjustment():
    duration_adjustments = [gv.sd[entry] for entry in gv.sd if entry.startswith('wl_')]
    result = float(gv.sd["wl"])
    for entry in duration_adjustments:
        result *= entry/100.0
    return '%.0f' % result    


def timestr(t):
    """
    Convert duration in seconds to string in the form h:mm:ss.
    """
    m, s = divmod(t, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"
    

def log_run():
    """
    Add run data to json log file - most recent first.
    If a record limit is specified (gv.sd["lr"]) the number of records is truncated.
    """  
    if gv.sd["lg"]:
        if gv.lrun[1] == 0:  # skip program 0
            return
        elif gv.lrun[1] == 98:
            pgr = _("Run-once")
            adj = "---"
        elif gv.lrun[1] == 99:
            pgr = _("Manual")
            adj = "---"
        elif gv.lrun[1] == 100:
            pgr = "Node-red"  
            adj = "---"          
        else:
            if gv.pd[gv.lrun[1] - 1]["name"] != "":
                pgr = str(gv.pd[gv.lrun[1] - 1]["name"])      
            else:
                pgr = "" + str(gv.lrun[1])               
            pid = gv.lrun[1] - 1
            if not gv.sd["idd"]:
                 pdur = gv.pd[pid]["duration_sec"][0]
            else:
                pdur = gv.pd[pid]["duration_sec"][gv.lrun[0]]
            adj = str(round((gv.lrun[2] / pdur) * 100))
            
        start = time.localtime()
        dur_m, dur_s = divmod(gv.lrun[2], 60)
        dur_h, dur_m = divmod(dur_m, 60)
        start_time = time.localtime(gv.rs[gv.lrun[0]][0]) #  Get start time from run schedule      
        logline = (
            '{"'
            + "program"
            + '": "'
            + pgr
            + '", "'
            + "adjustment"
            + '": "'
            # + total_adjustment()
            + adj
            + '", "'
            + "station"
            + '": '
            + str(gv.lrun[0])
            + ', "'
            + "duration"
            + '": "'
            + timestr(gv.lrun[2])
            + '", "'
            + "start"
            + '": '
            + f'"{start_time.tm_hour:02d}:{start_time.tm_min:02d}:{start_time.tm_sec:02d}"'
            + ', "'
            + "date"
            + '": "'
            + time.strftime('%Y-%m-%d', start_time)
            + '", "'
            + "program_index"
            + '": "'
            + str(gv.lrun[1])
            + '"}'
        )       
        lines = []
        lines.append(logline + "\n")
        log = read_log()
        for r in log:
            lines.append(json.dumps(r) + "\n")
        with codecs.open("./data/log.json", "w", encoding="utf-8") as f:
            if gv.sd["lr"]:
                f.writelines(lines[: gv.sd["lr"]])
            else:
                f.writelines(lines)
    return


def days_since_epoch():
    """ helper function for calculating interval program daystamp, relative to local device time
    """
    epoch = datetime.datetime(1970, 1, 1)   # no timezone info, so we can treat the epoch start in the local timezone instead of utc
    today = datetime.datetime.now()
    current_date = datetime.datetime(today.year, today.month, today.day)
    days = (current_date - epoch).days
    return days

def prog_match(prog):
    """
    Test a program for current date and time match.
    """
    if not prog["enabled"]:
        return 0  # Skip if program is not enabled
    
    lt = time.localtime(gv.now)
    if prog["type"] == "interval":
        if (days_since_epoch() % prog["interval_base_day"]) != prog["day_mask"]:
            return 0
    else:  # Weekday program
        if not prog["day_mask"] - 128 & 1 << lt.tm_wday:
            return 0
        if prog["type"] == "evendays":
            if lt.tm_mday % 2 != 0:
                return 0
        if prog["type"] == "odddays":
            if lt.tm_mday == 31 or ((lt.tm_mon == 2 and lt.tm_mday == 29)):
                return 0
            elif lt.tm_mday % 2 != 1:
                return 0     
    this_minute = (lt.tm_hour * 60) + lt.tm_min  # Check time match in minutes
    if this_minute < prog["start_min"] or this_minute >= prog["stop_min"]:
        return 0
    if prog["cycle_min"] == 0 and (this_minute == prog["start_min"]):
        return 1  # Program matched
    elif (
        prog["cycle_min"] != 0
        and (this_minute - prog["start_min"])
        // prog["cycle_min"]
        * prog["cycle_min"]
        == this_minute - prog["start_min"]
    ):
        return 1  # Program matched
    return 0


def schedule_stations(stations):
    """
    Schedule stations/valves/zones to run.
    """
    if (gv.sd["rd"]   #  If rain delay
        or (gv.sd["urs"]
            and gv.sd["rs"]
            ) #  rain detected by sensor
        ):
        rain = True
    else:
        rain = False               
    accumulate_time = gv.now
    if gv.sd["seq"]:  # sequential mode, stations run one after another
        for b in range(len(stations)):  # stations is a list of bitmasks in the program, one per board
            for s in range(8):
                sid = b * 8 + s  # station index
                if gv.rs[sid][2]:  # if station has a duration value
                    if (
                        not rain
                        or gv.sd["ir"][b] & 1 << s  # if no rain or station ignores rain
                    ):
                        gv.rs[sid][0] = int(accumulate_time)  # start at accumulated time
                        accumulate_time += gv.rs[sid][2]  # add duration
                        gv.rs[sid][1] = int(accumulate_time)  # set new stop time
                        accumulate_time += gv.sd["sdt"]  # add station delay
                        report_stations_scheduled()
                        gv.sd["bsy"] = 1
                    else:
                        gv.sbits[b] &= ~1 << s
                        gv.ps[sid] = [0, 0]
    else:  # concurrent mode, stations allowed to run in parallel
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s  # station index
                if (
                    not stations[b] & 1 << s 
                    or gv.srvals[sid]
                ):
                    continue  # skip stations not in prog or already running
                if gv.rs[sid][2]:  # if station has a duration value
                    if (not rain
                        or gv.sd["ir"][b] & 1 << s
                    ):  # if no rain or station ignores rain
                        gv.rs[sid][0] = gv.now  # set start time
                        gv.rs[sid][1] = gv.now + int(gv.rs[sid][2])  # set stop time
                        report_stations_scheduled()
                        gv.sd["bsy"] = 1
                    else:  # if rain and station does not ignore, clear station from display
                        gv.sbits[b] &= ~1 << s
                        gv.ps[sid] = [0, 0]


def stop_onrain():
    """
    Stop stations that do not ignore rain.
    """
    do_set_output = False
    for b in range(gv.sd["nbrd"]):
        for s in range(8):
            sid = b * 8 + s  # station index
            if gv.sd["ir"][b] & 1 << s:  # if station ignores rain...
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
    prev_srvals =  gv.srvals
    print("prev_srval: ", prev_srvals)  # - test
    print(gv.rs)  # - test
    
    gv.srvals = [0] * (gv.sd["nst"])
    set_output() #  This stops all stations
    gv.ps = []
    for i in range(gv.sd["nst"]):
        gv.ps.append([0, 0])
    gv.sbits = [0] * (gv.sd["nbrd"] + 1)
    
    ### insert log data for halted station
    # i = 0
    # while i < len(prev_srvals):
    #     if prev_srvals[i]:
    #         gv.lrun[0] = i
    #         gv.lrun[1] = gv.rs[i][3]
    #         gv.lrun[2] = gv.now - gv.rs[i][0]
    #         print("gv.lrun: ", gv.lrun)  # - test
    #         log_run()
    #     i += 1   
    ###
    gv.rs = []
    for i in range(gv.sd["nst"]):
        gv.rs.append([0, 0, 0, 0])
    gv.sd["bsy"] = 0
    return


def read_log():
    """
    Read data from irrigation log file.
    """
    result = []
    try:
        with io.open("./data/log.json") as logf:
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
    
def clear_stations():  # - test
    print("clearing stations")  # - test
    # lst = [i for i, e in enumerate(rs) if e != [0, 0, 0, 0]]
    for idx, stn in enumerate(gv.rs):       
        if stn[3] == 100:
            continue # skip stations run by node-red  
        gv.srvals[idx] = 0  # * (gv.sd["nst"])
        # set_output()
        gv.ps[idx] = [0, 0]
        gv.rs[idx] = [0, 0, 0, 0]
        # gv.sd["bsy"] = 0
        # gv.kr = 1  # - test
    # set_output()

def run_program(pid):
    """
    Run a program, pid == program index
    """  
    nr_run = 0
    for stn in gv.rs:  # - test # check for stations run by Node-red
        if stn[3] == 100:
            nr_run = 1
            break
    if nr_run:
        clear_stations()  # - test
    else:
        stop_stations()
    
    p = gv.pd[pid]  # program data
    for b in range(gv.sd["nbrd"]):  # check each station
        for s in range(8):
            sid = b * 8 + s  # station index
            if sid + 1 == gv.sd["mas"]:
                continue  # skip if this is master valve
            if (
                p["station_mask"][b] & 1 << s
            ):  # this station is scheduled in this program
                if gv.sd["idd"]:
                    duration = p["duration_sec"][sid]
                else:
                    duration = p["duration_sec"][0]
                if not gv.sd["iw"][b] & 1 << s:
                    duration = duration * gv.sd["wl"] // 100 * plugin_adjustment()
                gv.rs[sid][2] = duration
                gv.rs[sid][3] = pid + 1  # store program number in schedule
                gv.ps[sid][0] = pid + 1  # store program number for display
                gv.ps[sid][1] = duration  # duration
    schedule_stations(p["station_mask"])  # + gv.sd["nbrd"]])     


def jsave(data, fname):
    """
    Save data to a json file.
    """
    with open("./data/" + fname + ".json", "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def station_names():
    """
    Load station names from /data/stations.json file if it exists
    otherwise create file with defaults.

    Return station names as a list.
    """
    try:
        with open("./data/snames.json", "r") as snf:
            return json.load(snf)
    except IOError as e:
        # print("Error opening file: ", e)
        stations = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"]
        jsave(stations, "snames")
        return stations

def load_programs():
    """
    Load program data into memory from /data/programData.json file if it exists.
    Otherwise create an empty programs data list (gv.pd) or convert from old style format.
    """
    try:
        with open("./data/programData.json", "r") as pf:
            gv.pd = json.load(pf)
            gv.pnames = []
            for idx, p in enumerate(gv.pd):
                if p["name"] == "":
                    gv.pnames.append(idx + 1)
                else:
                    gv.pnames.append(str(p["name"]))
    except IOError:
        #  Check if programs.json file exists (old format) and if so, run conversion
        if os.path.isfile("./data/programs.json"):
            import convert_progs

            gv.pd = convert_progs.convert()
        else:
            gv.pd = []  # A config file -- create empty file if not found.
        with open("./data/programData.json", "w") as pf:
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
        if gv.sd["upas"] == 0:
            return True

        if web.config._session.user == "admin":
            return True
    except KeyError:
        pass

    if "pw" in qdict:
        if gv.sd["passphrase"] == password_hash(qdict["pw"]):
            return True
        if redirect:
            raise web.unauthorized()
        return False

    if redirect:
        raise web.seeother("/login")
    return False


signin_form = form.Form(
    form.Password(
        name='password', description=_("Passphrase") + ":", value=''
        ),

    validators=[
        form.Validator(
            _("Incorrect passphrase, please try again"),
            lambda x: gv.sd["passphrase"] == password_hash(x.password),
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


def convert_temp(temp, from_unit='C', to_unit='F'):
    """
      Convert Temperature
      supported units :
      Celsius, Fahrenheit, Kelvin
     """

    try:
        temp = float(temp)
    except(ValueError, TypeError) as e:
        return float('nan')

    from_unit = from_unit.upper()  # handle lower case input
    to_unit = to_unit.upper()

    if from_unit == to_unit:
        return round(temp, 2)
    if from_unit == 'C':
        if to_unit == 'F':
            temp = (1.8 * temp) + 32
        elif to_unit == 'K':
            temp += 273.15
    elif from_unit == 'F':
        c_temp = (temp - 32) * 5 / 9
        return convert_temp(c_temp, 'C', to_unit)
    elif from_unit == 'K':
        c_temp = temp - 273.15
        return convert_temp(c_temp, 'C', to_unit)

    return round(temp, 2)

def temp_string(temp, unit):
    if math.isnan(temp):
        return "--"
    return str(temp) + "° " + unit
