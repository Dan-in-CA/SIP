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


station_scheduled = signal("station_scheduled")

def report_station_scheduled(station):
    """
    Send blinker signal indicating that a station has been scheduled.
    """
    station_scheduled.send(station)


rain_changed = signal("rain_changed")


def report_rain_changed(txt=None):
    """
    Send blinker signal indicating that rain sensor changed.
    """
    rain_changed.send()


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
    
rs_ready = signal("rs_ready")  #: Signal to send on gv.rs ready


def report_rs_ready(txt=None):
    """
    Send blinker signal indicating run schedule (gv.rs) is ready
    """
    rs_ready.send()    


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
            try:
                GPIO.cleanup()
            except NameError:
                pass
        time.sleep(wait)
        try:
            print(_("Restarting..."))
        except Exception:
            pass
        try:
            command = "systemctl status sip"
            subprocess.check_output(command.split())
            command = "systemctl restart sip"
            subprocess.Popen(command.split())
        except subprocess.CalledProcessError:
            gv.restarted = 0
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
    
    except RuntimeError:
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
    gv.plugin_adj = result
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


def days_since_epoch():
    """ helper function for calculating interval program daystamp, relative to local device time
    """
    epoch = datetime.datetime(1970, 1, 1)   # no timezone info, so we can treat the epoch start in the local timezone instead of utc
    today = datetime.datetime.now()
    current_date = datetime.datetime(today.year, today.month, today.day)
    days = (current_date - epoch).days
    return days

def total_duration(prog): # total duration of all stations in program
    if gv.sd["idd"]:
        return sum(prog["duration_sec"])
    else:
        s_count = 0
        for m in prog["station_mask"]:
            s_count += bin(m).count('1')
            return s_count * prog["duration_sec"][0]

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
    if this_minute < prog["start_min"] or this_minute >= (prog["stop_min"] + prog["cycle_min"]):
        return 0
    dur_mins = -(total_duration(prog) // -60)
    if (this_minute >= prog["start_min"]
        and this_minute <= (prog["stop_min"] + prog["cycle_min"])
        and gv.sd["seq"]   
        ):
        return 1  # Program matched
    
    elif prog["cycle_min"] != 0:
        mins_past_start = this_minute - prog["start_min"]
        prior_cycles = mins_past_start // prog["cycle_min"]
        past_mins = prog["start_min"] + (prior_cycles * prog["cycle_min"])
        if (this_minute >= past_mins
            and this_minute < past_mins + dur_mins
            ):
            return 1
        
    elif (this_minute >= prog["start_min"]
          and gv.sd["seq"] == 0
          and this_minute < prog["start_min"] + (max(prog["duration_sec"]) // 60)
          ):
        return 1
            
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
                if (gv.rs[sid][2]
                    and not gv.halted[sid]  # station has not been halted
                    ):  # if station has a duration value
                    if (
                        not rain
                        or gv.sd["ir"][b] & 1 << s  # if no rain or station ignores rain
                        ):
                        if accumulate_time >= gv.rs[sid][1]: # gv.now is later than run time of station
                            gv.rs[sid] = [0, 0, 0, 0]
                            gv.ps[sid] = [0, 0]
                            continue
                        elif accumulate_time > gv.rs[sid][0] and accumulate_time < gv.rs[sid][1]: # within station run time
                            gv.rs[sid][0] = int(accumulate_time)
                            gv.rs[sid][2] = (gv.rs[sid][1] - accumulate_time)  # set duration to time remaining
                            gv.ps[sid][1] = gv.rs[sid][2]
                            accumulate_time += (gv.rs[sid][1] - accumulate_time)  + gv.sd["sdt"]
                            report_station_scheduled(sid + 1)  # station number
                            gv.sd["bsy"] = 1
                        else:                      
                            gv.rs[sid][0] = int(accumulate_time)
                            accumulate_time += gv.rs[sid][2]  # add duration
                            gv.rs[sid][1] = int(accumulate_time)  # set new stop time
                            accumulate_time += gv.sd["sdt"]  # add station delay
                            report_station_scheduled(sid + 1)  # station number
                            gv.sd["bsy"] = 1
                    else:
                        gv.sbits[b] &= ~1 << s # turn off station sbit
                        gv.ps[sid] = [0, 0]

    # concurrent mode, stations allowed to run in parallel
    elif gv.sd["seq"] == 0:
        for b in range(len(stations)):
            for s in range(8):
                sid = b * 8 + s  # station index
                if not stations[b] & 1 << s:
                    continue  # skip stations not in prog # or already running
                if gv.rs[sid][2]:  # if station has a duration value
                    if (not rain
                        or gv.sd["ir"][b] & 1 << s
                    ):  # if no rain or station ignores rain
                        if gv.now > gv.rs[sid][0] and gv.now < gv.rs[sid][1]: # within station run time
                            gv.rs[sid][0] = int(gv.now)
                            gv.rs[sid][2] = int(gv.rs[sid][1] - gv.now)  # set duration to time remaining
                            gv.ps[sid][1] = int(gv.rs[sid][2])
                            report_station_scheduled(sid + 1)
                            gv.sd["bsy"] = 1                        
                        else:
                            gv.rs[sid][0] = gv.now  # set start time
                            gv.rs[sid][1] = gv.now + int(gv.rs[sid][2])  # set stop time
                            report_station_scheduled(sid + 1)
                            gv.sd["bsy"] = 1
                    else:  # if rain and station does not ignore, clear station from display
                        gv.sbits[b] &= ~1 << s
                        gv.ps[sid] = [0, 0]
                        gv.rs[sid] = [0,0,0,0]
        
        # else:
    report_rs_ready()

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
    gv.halted =  gv.srvals
    gv.srvals = [0] * (gv.sd["nst"])
    set_output() #  This stops all stations
    gv.sbits = [0] * (gv.sd["nbrd"] + 1)
    # log data for halted station
    for i in range(len(gv.halted)):
        if i == gv.sd["mas"] -1:  # skip master:
            continue
        if gv.halted[i]:
            gv.ps[i] = [0, 0]
            gv.lrun[0] = i
            gv.lrun[1] = gv.rs[i][3]
            gv.lrun[2] = gv.now - gv.rs[i][0]            
            log_run()
            gv.rs[i] = [0, 0, 0, 0]
            
            
def preempt_program():
    """
    Stop all running stations, clear schedules.
    """
    if gv.pon:
        pid = gv.pon - 1
        gv.halted =  gv.srvals
        gv.srvals = [0] * gv.sd["nst"]       
        set_output() #  This stops all stations
        gv.sbits = [0] * (gv.sd["nbrd"] + 1)
        
        # log data for halted station
        for i in range(len(gv.halted)):
            if i == gv.sd["mas"] -1:  # skip master:
                continue
            if gv.halted[i]:
                gv.ps[i] = [0, 0]
                gv.lrun[0] = i
                gv.lrun[1] = gv.rs[i][3]
                gv.lrun[2] = gv.now - gv.rs[i][0]            
                log_run()
                gv.rs[i] = [0, 0, 0, 0]
        
        gv.rs = [list([0, 0, 0, 0]) for x in range(gv.sd["nst"])]
        gv.ps = [list([0, 0]) for x in range(gv.sd["nst"])]           
        gv.pon = None
        gv.halted = [0] * gv.sd["nst"]


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

def clear_stations():
    for idx, stn in enumerate(gv.rs):
        if stn[3] == 100:
            continue # skip stations run by node-red
        gv.srvals[idx] = 0
        gv.ps[idx] = [0, 0]
        gv.rs[idx] = [0, 0, 0, 0]

def run_program(pid):
    """
    Run a program, pid == program index
    called from UI (webpages)
    """
    nr_run = 0
    for stn in gv.rs:
        if stn[3] == 100:
            nr_run = 1
            break
    if nr_run:
        clear_stations()
    else:
        preempt_program()
    lt = time.localtime(gv.now)   
    p = gv.pd[pid]  # program data
    next_start = gv.now
    
    # check each station per boards listed in program up to number of boards in Options                           
    for b in range(len(p["station_mask"])):  # len == number of bytes
        for s in range(8):
            sid = b * 8 + s  # station index      
            if sid == gv.sd["mas"] - 1: 
                continue  # skip, this is master station                               
            # station duration conditionally scaled by "water level"
            if gv.sd["iw"][b] & 1 << s: # If ignore water level.
                duration_adj = 1.0
                if gv.sd["idd"]:  # If individual duration per station.
                    duration = p["duration_sec"][sid]
                else:
                    duration = p["duration_sec"][0]
            else:
                duration_adj = (
                    gv.sd["wl"] / 100.0
                ) * plugin_adjustment()
                if gv.sd["idd"]:
                    duration = (
                        p["duration_sec"][sid] * duration_adj
                    )
                else:
                    duration = p["duration_sec"][0] * duration_adj
            duration = round(duration)  # convert to int
            if (p["station_mask"][b] & 1 << s  # if this station is scheduled in this program
                and duration # station has a duration
                ):                                   
                gv.rs[sid][0] = next_start
                next_stop = next_start + duration
                gv.rs[sid][1] = next_stop
                gv.rs[sid][2] = duration
                gv.rs[sid][3] = pid + 1  # program number for scheduling
                gv.ps[sid][0] = pid + 1  # program number for display
                gv.ps[sid][1] = gv.rs[sid][2] # duration
                if gv.sd["seq"]:
                    next_start = next_stop
    schedule_stations(p["station_mask"])  

def run_once(bump = None, pnum = 98):
    """
    Runs a one-time program based on a list of durations. One for each station
    gv.rovals must contain a list of durations in seconds.
    Arguments:
    bump: controls if running program will be stopped (bumped).
    pnum: program number, default 98 (run once). Used in log.

    | bump         | None | None | 0  | 0  | 1   | 1    |
    | Sequential   | 0    | 1    | 0  | 1  | 0   | 1    |
    | Stop running | No   | Yes  | No | No | Yes | Yes  |
    """
    print("starting run once")  # - test
    stations = [0] * gv.sd["nbrd"]
    if(gv.sd["seq"] and bump != 0
        or (not gv.sd["seq"] and bump == 1)
        ):
        stop_stations()
    next_start = gv.now
    for sid, dur in enumerate(gv.rovals):
        if (gv.srvals[sid]  # this station is on
            and not gv.sd["seq"]  # concurrent mode
            and gv.rovals[sid]  # this station has been rescheduled.
            ):
            gv.lrun[0] = sid
            gv.lrun[1] = gv.rs[sid][3]
            gv.lrun[2] = int(gv.now) - gv.rs[sid][0]
            log_run()
        if dur:  # if this element has a value
            gv.rs[sid][0] = next_start  # set start time
            next_stop = next_start + dur
            gv.rs[sid][1] = next_stop
            gv.rs[sid][2] = dur
            gv.rs[sid][3] = pnum
            gv.ps[sid][0] = pnum
            gv.ps[sid][1] = dur
            if gv.sd["seq"]:
                next_start = next_stop            
            stations[sid // 8] += 2 ** (sid % 8)            
    print("gv.rs: ", gv.rs)    
    schedule_stations(stations)


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
