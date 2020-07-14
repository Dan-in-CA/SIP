#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from __future__ import division
from six.moves import range
# from future import standard_library
# standard_library.install_aliases()

# standard library imports
import ast
from calendar import timegm
import i18n
import json
import subprocess
import sys
from threading import Thread
import time

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
    report_station_completed,
    schedule_stations,
    station_names,
    stop_onrain,
    report_error,
    restart,
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
        gv.nowt = (
            time.localtime()
        )  # Current time as time struct.  Updated once per second.
        gv.now = timegm(
            gv.nowt
        )  # Current time as timestamp based on local time from the Pi. Updated once per second.
        if (
            gv.sd[u"en"]
            and not gv.sd[u"mm"]
            and (not gv.sd[u"bsy"] or not gv.sd[u"seq"])
        ):
            if int(gv.now // 60) != last_min:  # only check programs once a minute
                last_min = int(gv.now // 60)
                extra_adjustment = plugin_adjustment()
                for i, p in enumerate(gv.pd):  # get both index and prog item
                    if prog_match(p) and any(p[u"duration_sec"]):
                        # check each station per boards listed in program up to number of boards in Options
                        for b in range(len(p[u"station_mask"])):
                            for s in range(8):
                                sid = b * 8 + s  # station index
                                if gv.sd[u"mas"] == sid + 1:
                                    continue  # skip, this is master station
                                if (
                                    gv.srvals[sid]
                                    and gv.sd[u"seq"]
                                ):  # skip if currently on and sequential mode
                                    continue

                                # station duration conditionally scaled by "water level"
                                if gv.sd[u"iw"][b] & 1 << s:
                                    duration_adj = 1.0
                                    if gv.sd[u"idd"]:
                                        duration = p[u"duration_sec"][sid]
                                    else:
                                        duration = p[u"duration_sec"][0]
                                else:
                                    duration_adj = (
                                        gv.sd[u"wl"] // 100.0
                                    ) * extra_adjustment
                                    if gv.sd[u"idd"]:
                                        duration = (
                                            p[u"duration_sec"][sid] * duration_adj
                                        )
                                    else:
                                        duration = p[u"duration_sec"][0] * duration_adj
                                    duration = int(round(duration))  # convert to int
                                if (
                                    p[u"station_mask"][b] & 1 << s
                                ):  # if this station is scheduled in this program
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
                            if gv.sd[u"mas"] != sid + 1:  # if not master, fill out log
                                gv.ps[sid] = [0, 0]
                                gv.lrun[0] = sid
                                gv.lrun[1] = gv.rs[sid][3]
                                gv.lrun[2] = int(gv.now - gv.rs[sid][0])
                                gv.lrun[3] = gv.now #  test
                                print(u"logging @ time check")
                                log_run()
                                report_station_completed(sid + 1)
                                gv.pon = None  # Program has ended
                            gv.rs[sid] = [0, 0, 0, 0]
                    else:  # if this station is not yet on
                        if gv.rs[sid][0] <= gv.now < gv.rs[sid][1]:
                            if gv.sd[u"mas"] != sid + 1:  # if not master
                                gv.srvals[sid] = 1  # station is turned on
                                set_output()
                                gv.sbits[b] |= 1 << s  # Set display to on
                                gv.ps[sid][0] = gv.rs[sid][3]
                                gv.ps[sid][1] = gv.rs[sid][2]
                                if gv.sd[u"mas"] and gv.sd[u"mo"][b] & (
                                    1 << s
                                ):  # Master settings
                                    masid = gv.sd[u"mas"] - 1  # master index
                                    gv.rs[masid][0] = gv.rs[sid][0] + gv.sd[u"mton"]
                                    gv.rs[masid][1] = gv.rs[sid][1] + gv.sd[u"mtoff"]
                                    gv.rs[masid][3] = gv.rs[sid][3]
                            elif gv.sd[u"mas"] == sid + 1: # if this is master
                                masid = gv.sd[u"mas"] - 1  # master index
                                gv.sbits[b] |= 1 << sid
                                gv.srvals[masid] = 1
                                set_output()

            for s in range(gv.sd[u"nst"]):
                if gv.rs[s][1]:  # if any station is scheduled
                    program_running = True
                    gv.pon = gv.rs[s][3]  # Store number of running program
                    break
                program_running = False
                gv.pon = None

            if program_running:
                if (
                    gv.sd[u"urs"] and gv.sd[u"rs"]
                ):  #  Stop stations if use rain sensor and rain detected.
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

            if gv.sd[u"mas"] and (  #  master is defined
                gv.sd[u"mm"] or not gv.sd[u"seq"]
            ):  #  manual or concurrent mode.
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

        if gv.sd[u"urs"]:
            check_rain()  # in helpers.py

        if gv.sd[u"rd"] and gv.now >= gv.sd[u"rdst"]:  # Check if rain delay time is up
            gv.sd[u"rd"] = 0
            gv.sd[u"rdst"] = 0  # Rain delay stop time
            jsave(gv.sd, u"sd")

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
    u"session": web.config._session,
    u"json": json,
    u"ast": ast,
    u"_": _,
    u"i18n": i18n,
    u"app_path": lambda p: web.ctx.homepath + p,
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
        report_error(u"Import plugins error", e)
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
        report_error(u"Creating plugins menu", e)
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
            report_error(u"SSL error", e)
            restart(2)


    app.run()
