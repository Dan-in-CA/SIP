#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from __future__ import division
from six.moves import range

# standard library imports
import ast
from calendar import timegm
from datetime import date
import i18n
import json
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
    report_running_program_change,
    report_rain_delay_change,
    schedule_stations,
    station_names,
    stop_onrain,
    restart,
    convert_temp,
)
from ReverseProxied import ReverseProxied
from urls import urls  # Provides access to URLs for UI pages
import web  # the Web.py module. See webpy.org (Enables the Python SIP web interface)

sys.path.append(u"./plugins")
gv.restarted = 1

def timing_loop():
    """ ***** Main timing algorithm. Runs in a separate thread.***** """
    try:
        print(_(u"Starting timing loop") + u"\n")
    except Exception:
        pass
    last_min = 0
    while True:  # infinite loop
        cur_ord = (
            date.today().toordinal()  # day of year 
        )
        if cur_ord > gv.day_ord:
            gv.day_ord = cur_ord
            report_new_day()
        gv.nowt = (
            time.localtime()  # Current time as time struct.  Updated once per second.
        )
        gv.now = timegm(  # Current time as timestamp based on local time from the Pi. Updated once per second.
            gv.nowt
        )
        
        if gv.sd[u"mas"]: #  If master is defined
            masid = gv.sd[u"mas"] -1 # master station index
        else:
            masid = None
        
        if (
            gv.sd[u"en"]
            and not gv.sd[u"mm"]
            and (not gv.sd[u"bsy"] or not gv.sd[u"seq"])
        ):
            this_min = int(gv.now // 60)
            if this_min != last_min:  # only check programs once a minute
                last_min = this_min
                for i, p in enumerate(gv.pd):  # get both index and prog item
                    if prog_match(p) and any(p[u"duration_sec"]):
                        # check each station per boards listed in program up to number of boards in Options
                        for b in range(len(p[u"station_mask"])):
                            for s in range(8):
                                sid = b * 8 + s  # station index
                                if (gv.srvals[sid]
                                    and gv.sd[u"seq"]
                                ):
                                    continue  # skip if currently on and sequential mode
                                if sid == masid: 
                                    continue  # skip, this is master station
                                
                                # station duration conditionally scaled by "water level"
                                if gv.sd[u"iw"][b] & 1 << s:
                                    duration_adj = 1.0
                                    if gv.sd[u"idd"]:
                                        duration = p[u"duration_sec"][sid]
                                    else:
                                        duration = p[u"duration_sec"][0]
                                else:
                                    duration_adj = (
                                        gv.sd[u"wl"] / 100.0
                                    ) * plugin_adjustment() # was extra_adjustment
                                    if gv.sd[u"idd"]:
                                        duration = (
                                            p[u"duration_sec"][sid] * duration_adj
                                        )
                                    else:
                                        duration = p[u"duration_sec"][0] * duration_adj
                                    duration = int(round(duration))  # convert to int
                                if (
                                    p[u"station_mask"][b] & 1 << s  # if this station is scheduled in this program
                                ):
                                    gv.rs[sid][2] = duration
                                    gv.rs[sid][3] = i + 1  # program number for scheduling
                                    gv.ps[sid][0] = i + 1  # program number for display
                                    gv.ps[sid][1] = duration
                        schedule_stations(p[u"station_mask"])  # turns on gv.sd["bsy"]

        if gv.sd[u"bsy"]:
            for b in range(gv.sd[u"nbrd"]):  # Check each station once a second
                for s in range(8):
                    sid = b * 8 + s  # station index
                    if gv.srvals[sid]:  # if this station is on
                        if gv.now >= gv.rs[sid][1]:  # check if time is up
                            gv.srvals[sid] = 0
                            set_output()
                            gv.sbits[b] &= ~(1 << s)
                            # if gv.sd[u"mas"] != sid + 1:  # if not master, fill out log
                            if sid != masid:  # if not master, fill out log
                                gv.ps[sid] = [0, 0]
                                gv.lrun[0] = sid
                                gv.lrun[1] = gv.rs[sid][3]
                                gv.lrun[2] = int(gv.now - gv.rs[sid][0])
                                # print(u"logging @ time check")  # - test
                                log_run()
                                report_station_completed(sid + 1)
                            gv.rs[sid] = [0, 0, 0, 0]
                    else:  # if this station is not yet on
                        if (gv.rs[sid][0] <= gv.now 
                           and gv.now < gv.rs[sid][1]
                        ):
                            if sid != masid: # if not master
                                if (gv.sd[u"mo"][b] & (1 << s) # station activates master
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
                                if (gv.sd[u"mas"] # Master is defined
                                    and gv.sd[u"mo"][b] & (1 << s) # this station activates master.
                                ):  # Master settings
                                    if gv.sd[u"mton"] > 0:
                                        gv.rs[masid][0] = gv.rs[sid][0] + gv.sd[u"mton"] # this is where master is scheduled
                                    gv.rs[masid][1] = gv.rs[sid][1] + gv.sd[u"mtoff"]
                                    gv.rs[masid][3] = gv.rs[sid][3]
                            elif sid == masid: # if this is master
                                gv.sbits[b] |= 1 << s
                                gv.srvals[sid] = 1  # this is where master is turned on
                                set_output()

            program_running = False
            pon = None
            for sid in range(gv.sd[u"nst"]):
                if gv.rs[sid][1]:  # if any station is scheduled
                    program_running = True
                    pon = gv.rs[sid][3]
                    break
            if pon != gv.pon:  # Update number of running program
                gv.pon = pon
                report_running_program_change()

            if program_running:
                if (gv.sd[u"urs"] 
                    and gv.sd[u"rs"]  #  Stop stations if use rain sensor and rain detected.
                ):
                    stop_onrain()  # Clear schedule for stations that do not ignore rain.
                for sid in range(len(gv.rs)):  # loop through program schedule (gv.ps)
                    if gv.rs[sid][2] == 0:  # skip stations with no duration
                        continue
                    if gv.srvals[
                        sid
                    ]:  # If station is on, decrement time remaining display
                        if gv.ps[sid][1] > 0:  # if time is left
                            gv.ps[sid][1] -= 1

            if not program_running:
                gv.srvals = [0] * (gv.sd[u"nst"])
                set_output()
                gv.sbits = [0] * (gv.sd[u"nbrd"] + 1)
                gv.ps = []
                for i in range(gv.sd[u"nst"]):
                    gv.ps.append([0, 0])
                gv.rs = []
                for i in range(gv.sd[u"nst"]):
                    gv.rs.append([0, 0, 0, 0])
                gv.sd[u"bsy"] = 0

            if (gv.sd[u"mas"] #  master is defined
                and (gv.sd[u"mm"] or not gv.sd[u"seq"]) #  manual or concurrent mode.
            ):
                for b in range(gv.sd[u"nbrd"]):  # set stop time for master
                    for s in range(8):
                        sid = b * 8 + s
                        if (
                            gv.sd[u"mas"] != sid + 1  # if not master
                            and gv.srvals[sid]  #  station is on
                            and gv.rs[sid][1]
                            >= gv.now  #  station has a stop time >= now
                            and gv.sd[u"mo"][b] & (1 << s)  #  station activates master
                        ):
                            gv.rs[gv.sd[u"mas"] - 1][1] = (
                                gv.rs[sid][1] + gv.sd[u"mtoff"]
                            )  # set to future...
                            break  # first found will do
        else:  # Not busy
            if gv.pon != None:
                gv.pon = None
                report_running_program_change()

        if gv.sd[u"urs"]:
            check_rain()  # in helpers.py

        if gv.sd[u"rd"] and gv.now >= gv.sd[u"rdst"]:  # Check if rain delay time is up
            gv.sd[u"rd"] = 0
            gv.sd[u"rdst"] = 0  # Rain delay stop time
            jsave(gv.sd, u"sd")
            report_rain_delay_change()

        time.sleep(1)
        #### End of timing loop ####


class SIPApp(web.application):
    """Allow program to select HTTP port."""

    def run(
        self, port=gv.sd[u"htp"], ip=gv.sd[u"htip"], *middleware
    ):  # get port number from options settings
        func = self.wsgifunc(*middleware)
        func = ReverseProxied(func)
        return web.httpserver.runsimple(func, (ip, port))


app = SIPApp(urls, globals())
#  disableShiftRegisterOutput()
web.config.debug = False  # Improves page load speed
web.config._session = web.session.Session(
    app, web.session.DiskStore(u"sessions"), initializer={u"user": u"anonymous"}
)
template_globals = {
    "gv": gv,
    u"str": str,
    u"eval": eval,
    u"convert_temp": convert_temp,
    u"session": web.config._session,
    u"json": json,
    u"ast": ast,
    u"_": _,
    u"i18n": i18n,
    u"app_path": lambda p: web.ctx.homepath + p,  # - test
    u"web": web,
    u"round": round,
    u"time": time,
    u"timegm": timegm,
}

template_render = web.template.render(
    u"templates", globals=template_globals, base=u"base"
)

if __name__ == u"__main__":

    #########################################################
    #### Code to import all webpages and plugin webpages ####

    import plugins

    try:
        print(_(u"plugins loaded:"))
    except Exception as e:
        print(u"Import plugins error", e)
        pass
    for name in plugins.__all__:
        print(u" ", name)

    gv.plugin_menu.sort(key=lambda entry: entry[0])

    #  Keep plugin manager at top of menu
    try:
        for i, item in enumerate(gv.plugin_menu):
            if u"/plugins" in item:
                gv.plugin_menu.pop(i)
    except Exception as e:
        print(u"Creating plugins menu", e)
        pass
    tl = Thread(target=timing_loop)
    tl.daemon = True
    tl.start()

    if gv.use_gpio_pins:
        set_output()

    app.notfound = lambda: web.seeother(u"/")

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
            gv.sd[u"htp"] = int(80)
            jsave(gv.sd, u"sd")
            print(u"SSL error", e)
            restart(2)


    app.run()
