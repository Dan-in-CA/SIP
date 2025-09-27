#!/usr/bin/env python
# -*- coding: utf-8 -*-

# standard library imports
import ast
from datetime import date, datetime, timedelta ### changed
from datetime import time as d_time ### changed
import i18n
import json
import math #  check for infinity: math.isinf(math.inf)
import os
import subprocess
import sys
from threading import Thread
import time

sip_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(sip_path)

# local module imports
import gv
from gpio_pins import set_output
from helpers import (
    check_rain,
    get_rpi_revision,
    jsave,
    log_run,
    plugin_adjustment,
    prog_match,
    report_new_day,
    report_station_completed,
    report_rain_delay_change,
    schedule_stations,
    station_names,
    stop_onrain,
    restart,
    convert_temp,
    total_duration,
    temp_string,
    days_since_epoch
)
from ReverseProxied import ReverseProxied
from urls import urls  # Provides access to URLs for UI pages
import web  # the Web.py module. See webpy.org (Enables the Python SIP web interface)

sys.path.append("./plugins")
gv.restarted = 1
start_min_hold = 0

def timing_loop():
    """ ***** Main timing algorithm. Runs in a separate thread.***** """
    print(_("Starting timing loop") + "\n")
    prior_min = 0
    # next_start = 0
    while True:  # infinite loop
        next_start = 0
        cur_ord = (date.today().toordinal())  # day of year
        if cur_ord > gv.day_ord:
            gv.day_ord = cur_ord
            report_new_day()         
            gv.dse = days_since_epoch()
            today = datetime.now().date()
            midnight = datetime.combine(today, d_time.min)
            gv.lm = round(midnight.timestamp())
        
        gv.now = round(time.time()) # Current time as seconds since the epoch, in UTC. Updated once per second.
        lt = time.localtime(gv.now)  # Current time as time struct.
        
        if gv.sd["mas"]: #  If master is defined
            masid = gv.sd["mas"] -1 # master station index
        else:
            masid = None
        
        if (gv.sd["en"]
            and not gv.sd["mm"]
            and (not gv.sd["bsy"])
            ):
            this_min = (lt.tm_hour * 60) + lt.tm_min  # minutes past midnight
            if this_min != prior_min:  # only check programs once a minute
                prior_min = this_min
                for i, p in enumerate(gv.pd):  # get both index and program item
                    if gv.phold[0] == i:
                        if gv.phold[1] >= gv.now:
                            continue  # skip suspended program during run time
                        else:
                            gv.phold = [0, 0]                  
                    if (p["enabled"]
                          and gv.sd["seq"]
                          and this_min >= p["start_min"]
                          and this_min <= p["stop_min"]
                        ):
                        # schedule regular program or first iteration of recurring program 
                        next_start = gv.lm + (p["start_min"] * 60) # next_start is a timestamp (seconds)
                            
                        if p["cycle_min"]:  # a recurring program
                            start_times = []
                            recurring_start = p["start_min"]
                            while recurring_start < p["stop_min"] - p["cycle_min"]:
                                recurring_start += p["cycle_min"]
                                start_times.append(recurring_start)
                            for j, a_start in enumerate(start_times):
                                if (this_min >= a_start
                                    and gv.now < gv.lm + (a_start * 60) + total_duration(p)
                                    ):                        
                                    next_start = gv.lm + ((p["start_min"] + (p["cycle_min"] * (j + 1))) * 60)
                                    break
                    
                    elif (p["enabled"]
                        and gv.sd["seq"] == 0 # concurrent mode
                        and this_min >= p["start_min"]
                        and this_min <= p["stop_min"]
                        ):
                        next_start = gv.lm + (p["start_min"] * 60)
                    
                    
                    if (next_start
                        and prog_match(p) 
                        and any(p["duration_sec"])                      
                        ):        
                        # check each station per boards listed in program up to number of boards in Options                           
                        for b in range(len(p["station_mask"])):  # len == number of bytes
                            for s in range(8):
                                sid = b * 8 + s  # station index
                                if (gv.srvals[sid]
                                    and gv.sd["seq"]
                                ):
                                    continue  # skip if currently on and sequential mode
                                if sid == masid: 
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
                                    gv.rs[sid][3] = i + 1  # program number for scheduling
                                    gv.ps[sid][0] = i + 1  # program number for display
                                    gv.ps[sid][1] = gv.rs[sid][2] # duration
                                    if gv.sd["seq"]:
                                        next_start = next_stop
                        schedule_stations(p["station_mask"])  # -> helpers, turns on gv.sd["bsy"]

        if gv.sd["bsy"]:
            for b in range(gv.sd["nbrd"]):  # Check each station once a second
                for s in range(8):
                    sid = b * 8 + s  # station index
                    if gv.srvals[sid]:  # if this station is on
                        if gv.now >= gv.rs[sid][1]:  # if time is up
                            gv.srvals[sid] = 0  # set station off
                            set_output()
                            gv.sbits[b] &= ~(1 << s)
                            if sid != masid:  # if not master, fill out log
                                gv.ps[sid] = [0, 0]
                                gv.lrun[0] = sid
                                gv.lrun[1] = gv.rs[sid][3]
                                gv.lrun[2] = int(gv.now - gv.rs[sid][0])
                                log_run()
                                report_station_completed(sid + 1)
                            gv.rs[sid] = [0, 0, 0, 0]
                    else:  # if this station is not yet on
                        if (gv.now >= gv.rs[sid][0]
                            and gv.now < gv.rs[sid][1]
                            and not gv.halted[sid]
                           ):
                            if sid != masid: # if not master
                                if (gv.sd["mo"][b] & (1 << s) # station activates master
                                    and gv.sd["mton"] < 0 # master has a negative delay
                                    and not gv.srvals[masid] # master is not on
                                    ):
                                    # advance remaining stations start and stop times by master negative delay
                                    for stn in range(sid, len(gv.rs)):
                                        if gv.rs[stn][3]:  # If station has a duration  
                                            gv.rs[stn][0] += abs(gv.sd["mton"])
                                            gv.rs[stn][1] += abs(gv.sd["mton"])                                      
                                    brd = masid // 8
                                    gv.sbits[brd] |= 1 << (masid - (brd * 8))  # start master
                                    gv.srvals[masid] = 1
                                    set_output()                                
                                else:
                                    gv.srvals[sid] = 1  # station is turned on
                                    set_output()
                                    gv.sbits[b] |= 1 << s  # Set display to on
                                    gv.ps[sid][0] = gv.rs[sid][3]
                                    gv.ps[sid][1] = gv.rs[sid][2]
                                if (gv.sd["mas"] # Master is defined
                                    and gv.sd["mo"][b] & (1 << s) # this station activates master.
                                    ):  # Master settings
                                    if gv.sd["mton"] > 0:
                                        gv.rs[masid][0] = gv.rs[sid][0] + gv.sd["mton"] # this is where master is scheduled
                                    gv.rs[masid][1] = gv.rs[sid][1] + gv.sd["mtoff"]
                                    gv.rs[masid][3] = gv.rs[sid][3]
                            elif sid == masid: # if this is master
                                gv.sbits[b] |= 1 << s
                                gv.srvals[sid] = 1  # this is where master is turned on
                                set_output()

            else:  # for loop ended
                program_running = False
                pon = None
                gv.halted = [0] * gv.sd["nst"]  # clear gv.halted
            
            for sid in range(gv.sd["nst"]):
                if gv.rs[sid][1]:  # if any station is scheduled
                    program_running = True
                    pon = gv.rs[sid][3]
                    break
            if pon != gv.pon:  # Update number of running program
                gv.pon = pon

            if program_running:
                if (gv.sd["urs"] 
                    and gv.sd["rs"]  #  Stop stations if use rain sensor and rain detected.
                ):
                    stop_onrain()  # Clear schedule for stations that do not ignore rain.
                for sid in range(len(gv.rs)):  # loop through program schedule (gv.ps)
                    if gv.rs[sid][2] == 0:  # skip stations with no duration
                        continue
                    if gv.srvals[sid]:
                      # If station is on, decrement time remaining display
                        if gv.ps[sid][1] > 0:  # if time is left
                            gv.ps[sid][1] -= 1

            if not program_running:
                gv.srvals = [0] * (gv.sd["nst"])
                set_output()
                gv.rovals = [0] * gv.sd["nst"]
                gv.sbits = [0] * (gv.sd["nbrd"] + 1)
                for i in range(gv.sd["nst"]):
                    gv.ps.append([0, 0])
                gv.halted = [0] * gv.sd["nst"]  # clear gv.halted
                gv.sd["bsy"] = 0

            if (gv.sd["mas"] #  master is defined
                and (gv.sd["mm"] or not gv.sd["seq"]) #  manual or concurrent mode.
            ):
                for b in range(gv.sd["nbrd"]):  # set stop time for master
                    for s in range(8):
                        sid = b * 8 + s
                        if (
                            gv.sd["mas"] != sid + 1  # if not master
                            and gv.srvals[sid]  #  station is on
                            and gv.rs[sid][1]
                            >= gv.now  #  station has a stop time >= now
                            and gv.sd["mo"][b] & (1 << s)  #  station activates master
                        ):
                            gv.rs[gv.sd["mas"] - 1][1] = (
                                gv.rs[sid][1] + gv.sd["mtoff"]
                            )  # set to future...
                            break  # first found will do
        else:  # Not busy
            if gv.pon != None:
                gv.pon = None

        if gv.sd["urs"]:
            check_rain()  # in helpers.py

        if gv.sd["rd"] and gv.now >= gv.sd["rdst"]:  # Check if rain delay time is up
            gv.sd["rd"] = 0
            gv.sd["rdst"] = 0  # Rain delay stop time
            jsave(gv.sd, "sd")
            report_rain_delay_change()

        time.sleep(1)
        #### End of timing loop ####


class SIPApp(web.application):
    """Allow program to select HTTP port."""

    def run(
        self, port=gv.sd["htp"], ip=gv.sd["htip"], *middleware
    ):  # get port number from options settings
        func = self.wsgifunc(*middleware)
        func = ReverseProxied(func)
        return web.httpserver.runsimple(func, (ip, port))


app = SIPApp(urls, globals())
web.config.debug = False  # Improves page load speed
web.config._session = web.session.Session(
    app, web.session.DiskStore("sessions"), initializer={"user": "anonymous"}
)
template_globals = {
    "gv": gv,
    "str": str,
    "eval": eval,
    "convert_temp": convert_temp,
    "temp_string" : temp_string,
    "session": web.config._session,
    "json": json,
    "ast": ast,
    "_": _,
    "i18n": i18n,
    "app_path": lambda p: web.ctx.homepath + p,
    "web": web,
    "round": round,
    "time": time,
    # "timegm": timegm,
}

template_render = web.template.render(
    "templates", globals=template_globals, base="base"
)

if __name__ == "__main__":

    #########################################################
    #### Code to import all webpages and plugin webpages ####

    import plugins

    try:
        print(_("plugins loaded:"))
    except Exception as e:
        print("Import plugins error", e)
        pass
    for name in plugins.__all__:
        print(" ", name)
    
    gv.plugin_menu.sort(key=lambda entry: entry[0])

    #  Keep plugin manager at top of menu
    try:
        for i, item in enumerate(gv.plugin_menu):
            if "/plugins" in item:
                gv.plugin_menu.pop(i)
    except Exception as e:
        print("Creating plugins menu", e)
        pass
    tl = Thread(target=timing_loop)
    tl.daemon = True
    tl.start()

    if gv.use_gpio_pins:
        set_output()

    app.notfound = lambda: web.seeother("/")

    ###########################
    #### For HTTPS (SSL):  ####

    if gv.sd["htp"] == 443:
        try:
            from cheroot.server import HTTPServer
            from cheroot.ssl.builtin import BuiltinSSLAdapter
            HTTPServer.ssl_adapter = BuiltinSSLAdapter(
                certificate='/usr/lib/ssl/certs/SIP.crt',
                private_key='/usr/lib/ssl/private/SIP.key'
            )
        except IOError as e:
            gv.sd["htp"] = int(80)
            jsave(gv.sd, "sd")
            print("SSL error", e)
            restart()

    app.run()

