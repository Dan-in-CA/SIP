# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from six.moves import map
from six.moves import range

# standard library imports
import ast
import datetime
import io
import time

# local module imports
from blinker import signal
from gpio_pins import set_output
import gv
from helpers import *
from sip import template_render
import web

loggedin = signal(u"loggedin")
def report_login():
    loggedin.send()


value_change = signal(u"value_change")
def report_value_change():
    value_change.send()


option_change = signal(u"option_change")
def report_option_change():
    option_change.send()


rebooted = signal(u"rebooted")
def report_rebooted():
    rebooted.send()


station_names = signal(u"station_names")
def report_station_names():
    station_names.send()


program_change = signal(u"program_change")
def report_program_change():
    program_change.send()


program_deleted = signal(u"program_deleted")
def report_program_deleted():
    program_deleted.send()


program_toggled = signal(u"program_toggled")
def report_program_toggle():
    program_toggled.send()


### Web pages ######################

class WebPage(object):
    def __init__(self):
        gv.cputemp = get_cpu_temp()


class ProtectedPage(WebPage):
    def __init__(self):
        check_login(True)
        WebPage.__init__(self)


class login(WebPage):
    """Login page"""

    def GET(self):
        return template_render.login(signin_form())

    def POST(self):
        my_signin = signin_form()

        if not my_signin.validates():
            return template_render.login(my_signin)
        else:
            web.config._session.user = u"admin"
            report_login()
            raise web.seeother(u"/")


class logout(WebPage):
    def GET(self):
        web.config._session.user = u"anonymous"
        web.session.Session.kill(web.config._session)
        raise web.seeother(u"/")


class sw_restart(ProtectedPage):
    """Restart system."""

    def GET(self):
        restart(1)
        #referer = web.ctx.env.get('HTTP_REFERER', u"/")
        referer = u"/"
        return template_render.restarting(referer)


###########################
#### Class Definitions ####


class home(ProtectedPage):
    """Open Home page."""

    def GET(self):
        return template_render.home()


class change_values(ProtectedPage):
    """Save controller values, return browser to home page."""

    def GET(self):
        qdict = web.input()
        if u"rsn" in qdict and qdict[u"rsn"] == u"1":
            stop_stations()
            raise web.seeother(u"/")
        if u"en" in qdict and qdict[u"en"] == u"":
            qdict[u"en"] = u"1"  # default
        elif u"en" in qdict and qdict[u"en"] == u"0":
            gv.srvals = [0] * (gv.sd[u"nst"])  # turn off all stations
            set_output()
        if u"mm" in qdict and qdict[u"mm"] == u"0":
            clear_mm()
        if u"rd" in qdict and qdict[u"rd"] != u"0" and qdict[u"rd"] != "":
            gv.sd[u"rd"] = int(float(qdict[u"rd"]))
            gv.sd[u"rdst"] = int(
                gv.now + gv.sd[u"rd"] * 3600
            )  # + 1  # +1 adds a smidge just so after a round trip the display hasn"t already counted down by a minute.
            stop_onrain()
        elif u"rd" in qdict and qdict[u"rd"] == u"0":
            gv.sd[u"rdst"] = 0
        for key in list(qdict.keys()):
            try:
                gv.sd[key] = int(qdict[key])
            except Exception as e:
                report_error(u"change_values Exception", e)
                pass
        jsave(gv.sd, u"sd")
        report_value_change()
        raise web.seeother(u"/")  # Send browser back to home page


class view_options(ProtectedPage):
    """Open the options page for viewing and editing."""

    def GET(self):
        qdict = web.input()
        errorCode = u"none"
        if u"errorCode" in qdict:
            errorCode = qdict[u"errorCode"]

        return template_render.options(errorCode)


class change_options(ProtectedPage):
    """Save changes to options made on the options page."""

    def GET(self):
        qdict = web.input()
        if u"opw" in qdict and qdict[u"opw"] != u"":
            try:
                if password_hash(qdict[u"opw"]) == gv.sd[u"passphrase"]:
                    if qdict[u"npw"] == u"":
                        raise web.seeother(u"/vo?errorCode=pw_blank")
                    elif qdict[u"cpw"] != u"" and qdict[u"cpw"] == qdict[u"npw"]:
                        gv.sd[u"passphrase"] = password_hash( #  Set new passphrase.
                            qdict[u"npw"]
                        )
                    else:
                        raise web.seeother(u"/vo?errorCode=pw_mismatch")
                else:
                    raise web.seeother(u"/vo?errorCode=pw_wrong")
            except KeyError:
                pass

        for f in [u"name"]:
            if u"o" + f in qdict:
                gv.sd[f] = qdict[u"o" + f]

        for f in [u"loc", u"lang"]:
            if u"o" + f in qdict:
                if f not in gv.sd or gv.sd[f] != qdict[u"o" + f]:
                    qdict[u"rstrt"] = u"1"  # force restart with change
                gv.sd[f] = qdict[u"o" + f]

        if u"onbrd" in qdict:
            if int(qdict[u"onbrd"]) + 1 != gv.sd[u"nbrd"]:
                self.update_scount(qdict)
            gv.sd[u"nbrd"] = int(qdict[u"onbrd"]) + 1
            gv.sd[u"nst"] = gv.sd[u"nbrd"] * 8
            self.update_prog_lists(u"nbrd")

        if u"ohtp" in qdict:
            if u"htp" not in gv.sd or gv.sd[u"htp"] != int(qdict[u"ohtp"]):
                qdict[u"rstrt"] = u"1"  # force restart with change in htp
            gv.sd[u"htp"] = int(qdict[u"ohtp"])

        if u"oidd" in qdict:
            idd_int = 1
        else:
            idd_int = 0
        if idd_int != gv.sd[u"idd"]:
            gv.sd[u"idd"] = idd_int
            self.update_prog_lists(u"idd")

        if u"ohtip" in qdict:
            if u"htip" not in gv.sd or gv.sd[u"htip"] != qdict[u"ohtip"]:
                qdict[u"rstrt"] = u"1"  # force restart with change in htip
            gv.sd[u"htip"] = qdict[u"ohtip"]

        for f in [u"sdt", u"mas", u"mton", u"mtoff", u"wl", u"lr", u"tz"]:
            if u"o" + f in qdict:
                if (
                    f == u"mton"
                    and int(qdict[u"o" + f]) < 0
                ):  # handle values less than zero (temp fix)
                    raise web.seeother(u"/vo?errorCode=mton_minus")
                gv.sd[f] = int(qdict[u"o" + f])

        for f in [
            u"upas",
            u"tf",
            u"urs",
            u"seq",
            u"rst",
            u"lg",
            u"pigpio",
            u"alr",
        ]:
            if u"o" + f in qdict and (
                qdict[u"o" + f] == u"on" or qdict[u"o" + f] == u"1"
            ):
                gv.sd[f] = 1
            else:
                gv.sd[f] = 0

        jsave(gv.sd, u"sd")
        report_option_change()
        if u"rbt" in qdict and qdict[u"rbt"] == u"1":
            gv.srvals = [0] * (gv.sd[u"nst"])
            set_output()
            report_rebooted()
            reboot()

        if u"rstrt" in qdict and qdict[u"rstrt"] == u"1":
            restart(2)
            raise web.seeother(u"/restart")
        raise web.seeother(u"/")

    def update_scount(self, qdict):
        """
        Increase or decrease the number of stations displayed when
        number of expansion boards is changed in options.

        Increase or decrase the lengths of program "duration_sec" and "station_mask"
        when number of expansion boards is changed
        """
        if int(qdict[u"onbrd"]) + 1 > gv.sd[u"nbrd"]:  # Lengthen lists
            incr = int(qdict[u"onbrd"]) - (gv.sd[u"nbrd"] - 1)
            for i in range(incr):
                gv.sd[u"mo"].append(0)
                gv.sd[u"ir"].append(0)
                gv.sd[u"iw"].append(0)
                gv.sd[u"show"].append(255)
            ln = len(gv.snames)
            for i in range(incr * 8):
                gv.snames.append(u"S" + u"{:0>2d}".format(i + 1 + ln))
            for i in range(incr * 8):
                gv.srvals.append(0)
                gv.ps.append([0, 0])
                gv.rs.append([0, 0, 0, 0])
            for i in range(incr):
                gv.sbits.append(0)
        elif int(qdict[u"onbrd"]) + 1 < gv.sd[u"nbrd"]:  # Shorten lists
            onbrd = int(qdict[u"onbrd"])
            decr = gv.sd[u"nbrd"] - (onbrd + 1)
            gv.sd[u"mo"] = gv.sd[u"mo"][: (onbrd + 1)]
            gv.sd[u"ir"] = gv.sd[u"ir"][: (onbrd + 1)]
            gv.sd[u"iw"] = gv.sd[u"iw"][: (onbrd + 1)]
            gv.sd[u"show"] = gv.sd[u"show"][: (onbrd + 1)]
            newlen = gv.sd[u"nst"] - decr * 8
            gv.srvals = gv.srvals[:newlen]
            gv.ps = gv.ps[:newlen]
            gv.rs = gv.rs[:newlen]
            gv.snames = gv.snames[:newlen]
            gv.sbits = gv.sbits[: onbrd + 1]
        jsave(gv.snames, u"snames")

    def update_prog_lists(self, change):
        for p in gv.pd:
            if (
                change == u"idd"
                or change == u"nbrd"
            ):  #  change length of p["duration_sec"]
                if not gv.sd[u"idd"]:
                    p[u"duration_sec"] = p[u"duration_sec"][:1]
                    if p[u"duration_sec"][0] == 0:
                        p[u"enabled"] = 0

                else:
                    old_dur = None
                    if (
                        change == u"idd"
                        and gv.sd[u"idd"]
                        and len(p[u"duration_sec"]) == 1  #  changed from !idd -> idd
                    ):
                        old_dur = p[u"duration_sec"][0]
                        p[u"duration_sec"][0] = 0
                    if gv.sd[u"nst"] > len(p[u"duration_sec"]):
                        p[u"duration_sec"].extend(
                            [0] * (gv.sd[u"nst"] - len(p[u"duration_sec"]))
                        )
                        if old_dur:
                            for b in range(
                                len(p[u"station_mask"])
                            ):  # set duration to old_dur for each active station.
                                for s in range(8):
                                    if p[u"station_mask"][b] & 1 << s:
                                        p[u"duration_sec"][b * 8 + s] = old_dur
                    elif gv.sd["nst"] < len(p[u"duration_sec"]):
                        p[u"duration_sec"] = p[u"duration_sec"][: gv.sd[u"nst"]]

            if change == u"nbrd":  #  change length of p["station_mask"]
                if gv.sd[u"nbrd"] > len(p[u"station_mask"]):
                    p[u"station_mask"].extend(
                        [0] * (gv.sd[u"nbrd"] - len(p[u"station_mask"]))
                    )
                elif gv.sd[u"nbrd"] < len(p[u"station_mask"]):
                    p[u"station_mask"] = p[u"station_mask"][: gv.sd[u"nbrd"]]
        jsave(gv.pd, u"programData")


class view_stations(ProtectedPage):
    """Open a page to view and edit a run once program."""

    def GET(self):
        return template_render.stations()


class change_stations(ProtectedPage):
    """Save changes to station names, ignore rain and master associations."""

    def GET(self):
        qdict = web.input()
        for i in range(gv.sd[u"nbrd"]):  # capture master associations
            if u"m" + str(i) in qdict:
                try:
                    gv.sd[u"mo"][i] = int(qdict[u"m" + str(i)])
                except ValueError:
                    gv.sd[u"mo"][i] = 0
            if u"i" + str(i) in qdict:
                try:
                    gv.sd[u"ir"][i] = int(qdict[u"i" + str(i)])
                except ValueError:
                    gv.sd[u"ir"][i] = 0
            if u"w" + str(i) in qdict:
                try:
                    gv.sd[u"iw"][i] = int(qdict[u"w" + str(i)])
                except ValueError:
                    gv.sd[u"iw"][i] = 0
            if u"sh" + str(i) in qdict:
                try:
                    gv.sd[u"show"][i] = int(qdict[u"sh" + str(i)])
                except ValueError:
                    gv.sd[u"show"][i] = 255
            if u"d" + str(i) in qdict:
                try:
                    gv.sd[u"show"][i] = ~int(qdict[u"d" + str(i)]) & 255
                except ValueError:
                    gv.sd[u"show"][i] = 255
        names = []
        for i in range(gv.sd[u"nst"]):
            if u"s" + str(i) in qdict:
                names.append(qdict[u"s" + str(i)])
            else:
                names.append(u"S" + u"{:0>2d}".format(iu + 1))
        gv.snames = names
        jsave(names, u"snames")
        jsave(gv.sd, u"sd")
        report_station_names()
        raise web.seeother(u"/")


class get_set_station(ProtectedPage):
    """Return a page containing a number representing the state of a station or all stations if 0 is entered as station number."""

    def GET(self):
        qdict = web.input()

        sid = get_input(qdict, u"sid", 0, int) - 1
        set_to = get_input(qdict, u"set_to", None, int)
        set_time = get_input(qdict, u"set_time", 0, int)

        if set_to is None:
            if sid < 0:
                status = u"<!DOCTYPE html>\n"
                status += u"".join(str(x) for x in gv.srvals)
                return status
            elif sid < gv.sd[u"nbrd"] * 8:
                status = u"<!DOCTYPE html>\n"
                status += str(gv.srvals[sid])
                return status
            else:
                return _(u"Station ") + str(sid + 1) + _(u" not found.")
        elif gv.sd[u"mm"]:
            if set_to:  # if status is on
                if gv.sd[u"seq"]:
                    if gv.sd["mas"]: # if a master is set
                        for i in range(gv.sd[u"nst"]):
                            if i != gv.sd["mas"] - 1:
                                gv.srvals[i] = 0
                                gv.rs[i] = [0, 0, 0, 0]
                                gv.ps[i] = [0, 0]
                        set_output()
                        sb_byte = (gv.sd["mas"] - 1) // 8
                        gv.sbits[sb_byte] = 1 << (gv.sd["mas"] - 1) % 8
                        for b in range(len(gv.sbits)):
                            if b != sb_byte:
                                gv.sbits[b] = 0
                    else:
                      stop_stations()
                gv.rs[sid][0] = gv.now  # set start time to current time
                if set_time > 0:  # if an optional duration time is given
                    gv.rs[sid][2] = set_time
                    gv.rs[sid][1] = (
                        gv.rs[sid][0] + set_time
                    )  # stop time = start time + duration
                else:
                    gv.rs[sid][1] = float(u"inf")  # stop time = infinity
                gv.rs[sid][3] = 99  # set program index
                gv.ps[sid][1] = set_time
                gv.sd[u"bsy"] = 1
                time.sleep(1)
            else:  # If status is off
                gv.rs[sid][1] = gv.now + 2
                time.sleep(2)
            raise web.seeother(u"/")
        else:
            return _(u"Manual mode not active.")


class view_runonce(ProtectedPage):
    """Open a page to view and edit a run once program."""

    def GET(self):
        return template_render.runonce()


class change_runonce(ProtectedPage):
    """Start a Run Once program. This will override any running program."""

    def GET(self):
        qdict = web.input()
        if not gv.sd[u"en"]:  # check operation status
            return
        gv.rovals = json.loads(qdict[u"t"])
        gv.rovals.pop()
        for sid in range(gv.sd[u"nst"]):
            if gv.srvals[sid]:  # if currently on, log result
                gv.lrun[0] = sid
                gv.lrun[1] = gv.rs[sid][3]
                gv.lrun[2] = int(gv.now - gv.rs[sid][0])
                gv.lrun[3] = gv.now #  start time
                log_run()
                report_station_completed(sid + 1)
        stations = [0] * gv.sd[u"nbrd"]
        gv.ps = []  # program schedule (for display)
        gv.rs = []  # run schedule
        for sid in range(gv.sd[u"nst"]):
            gv.ps.append([0, 0])
            gv.rs.append([0, 0, 0, 0])
        for sid, dur in enumerate(gv.rovals):
            if dur:  # if this element has a value
                gv.rs[sid][0] = gv.now
                gv.rs[sid][2] = dur
                gv.rs[sid][3] = 98
                gv.ps[sid][0] = 98
                gv.ps[sid][1] = dur
                stations[sid // 8] += 2 ** (sid % 8)
        schedule_stations(stations)
        raise web.seeother(u"/")


class view_programs(ProtectedPage):
    """Open programs page."""

    def GET(self):
        return template_render.programs()


class modify_program(ProtectedPage):
    """Open page to allow program modification."""

    def GET(self):
        qdict = web.input()
        pid = int(qdict[u"pid"])
        prog = []
        if pid != -1:
            mp = gv.pd[pid]  # Modified program
            if mp[u"type"] == u"interval":
                dse = int(gv.now // 86400)
                # Convert absolute to relative days remaining for display
                rel_rem = (
                    ((mp[u"day_mask"]) + mp[u"interval_base_day"])
                    - (dse % mp[u"interval_base_day"])
                ) % mp[u"interval_base_day"]
            prog = str(mp).replace(u" ", u"")
        return template_render.modify(pid, prog)


class change_program(ProtectedPage):
    """Add a program or modify an existing one."""

    def GET(self):
        qdict = web.input()
        pnum = int(qdict[u"pid"]) + 1  # program number
        cp = json.loads(qdict[u"v"])
        if cp[u"enabled"] == 0 and pnum == gv.pon:  # if disabled and program is running
            for i in range(len(gv.ps)):
                if gv.ps[i][0] == pnum:
                    gv.ps[i] = [0, 0]
                if gv.srvals[i]:
                    gv.srvals[i] = 0
            for i in range(len(gv.rs)):
                if gv.rs[i][3] == pnum:
                    gv.rs[i] = [0, 0, 0, 0]
        if cp[u"type"] == u"interval":
            dse = int(gv.now // 86400)
            ref = dse + cp[u"day_mask"]  # - 128
            cp[u"day_mask"] = ref % cp[u"interval_base_day"]  # + 128
        if qdict[u"pid"] == u"-1":  # add new program
            gv.pd.append(cp)
        else:
            gv.pd[int(qdict[u"pid"])] = cp  # replace program
        jsave(gv.pd, u"programData")
        report_program_change()
        raise web.seeother(u"/vp")


class delete_program(ProtectedPage):
    """Delete one or all existing program(s)."""

    def GET(self):
        qdict = web.input()
        if qdict[u"pid"] == u"-1":
            del gv.pd[:]
            jsave(gv.pd, u"programData")
        else:
            del gv.pd[int(qdict[u"pid"])]
        jsave(gv.pd, u"programData")
        report_program_deleted()
        raise web.seeother(u"/vp")


class enable_program(ProtectedPage):
    """Activate or deactivate an existing program(s)."""

    def GET(self):
        qdict = web.input()
        gv.pd[int(qdict[u"pid"])][u"enabled"] = int(qdict[u"enable"])
        jsave(gv.pd, u"programData")
        report_program_toggle()
        raise web.seeother(u"/vp")


class view_log(ProtectedPage):
    """View Log"""

    def GET(self):
        records = read_log()
        return template_render.log(records)


class clear_log(ProtectedPage):
    """Delete all log records"""

    def GET(self):
        with io.open(u"./data/log.json", u"w") as f:
            f.write(u"")
        raise web.seeother(u"/vl")


class run_now(ProtectedPage):
    """Run a scheduled program now. This will override any running programs."""

    def GET(self):
        qdict = web.input()
        pid = int(qdict[u"pid"])
        p = gv.pd[int(qdict[u"pid"])]  # program data
        stop_stations()
        extra_adjustment = plugin_adjustment()
        sid = -1
        for b in range(gv.sd[u"nbrd"]):  # check each station
            for s in range(8):
                sid += 1  # station index
                if sid + 1 == gv.sd[u"mas"]:  # skip if this is master valve
                    continue
                if (
                    p[u"station_mask"][b] & 1 << s
                ):  # if this station is scheduled in this program
                    if gv.sd[u"idd"]:
                        duration = p[u"duration_sec"][sid]
                    else:
                        duration = p[u"duration_sec"][0]
                    if not gv.sd[u"iw"][b] & 1 << s:
                        duration = duration * gv.sd[u"wl"] // 100 * extra_adjustment
                    gv.rs[sid][2] = duration
                    gv.rs[sid][3] = pid + 1  # store program number in schedule
                    gv.ps[sid][0] = pid + 1  # store program number for display
                    gv.ps[sid][1] = duration  # duration
        schedule_stations(p[u"station_mask"])  # + gv.sd["nbrd"]])
        raise web.seeother(u"/")


class toggle_temp(ProtectedPage):
    """Change units of Raspi"s CPU temperature display on home page."""

    def GET(self):
        qdict = web.input()
        if qdict[u"tunit"] == u"C":
            gv.sd[u"tu"] = u"F"
        else:
            gv.sd[u"tu"] = u"C"
        jsave(gv.sd, u"sd")
        raise web.seeother(u"/")


class api_status(ProtectedPage):
    """Simple Status API"""

    def GET(self):
        statuslist = []
        for bid in range(0, gv.sd[u"nbrd"]):
            for s in range(0, 8):
                if (gv.sd[u"show"][bid] >> s) & 1 == 1:
                    sid = bid * 8 + s
                    sn = sid + 1
                    sname = gv.snames[sid]
                    sbit = (gv.sbits[bid] >> s) & 1
                    irbit = (gv.sd[u"ir"][bid] >> s) & 1
                    status = {
                        u"station": sid,
                        u"status": u"disabled",
                        u"reason": u"",
                        u"master": 0,
                        u"programName": u"",
                        u"remaining": 0,
                        u"name": sname,
                    }
                    if gv.sd[u"en"] == 1:
                        if sbit:
                            status[u"status"] = u"on"
                        if not irbit:
                            if gv.sd[u"rd"] != 0:
                                status[u"reason"] = u"rain_delay"
                            if gv.sd[u"urs"] != 0 and gv.sd[u"rs"] != 0:
                                status[u"reason"] = u"rain_sensed"
                        if sn == gv.sd[u"mas"]:
                            status[u"master"] = 1
                            status[u"reason"] = u"master"
                        else:
                            rem = gv.ps[sid][1]
                            if rem > 65536:
                                rem = 0

                            id_nr = gv.ps[sid][0]
                            pname = u"P" + str(id_nr)
                            if id_nr == 255 or id_nr == 99:
                                pname = u"Manual Mode"
                            if id_nr == 254 or id_nr == 98:
                                pname = u"Run-once Program"

                            if sbit:
                                status[u"status"] = u"on"
                                status[u"reason"] = u"program"
                                status[u"programName"] = pname
                                status[u"remaining"] = rem
                            else:
                                if gv.ps[sid][0] == 0:
                                    status[u"status"] = u"off"
                                else:
                                    status[u"status"] = u"waiting"
                                    status[u"reason"] = u"program"
                                    status[u"programName"] = pname
                                    status[u"remaining"] = rem
                    else:
                        status[u"reason"] = u"system_off"
                    statuslist.append(status)
        web.header(u"Content-Type", u"application/json")
        return json.dumps(statuslist)


class api_log(ProtectedPage):
    """Simple Log API"""

    def GET(self):
        qdict = web.input()
        thedate = qdict[u"date"]
        # date parameter filters the log values returned; "yyyy-mm-dd" format
        theday = datetime.date(*map(int, thedate.split(u"-")))
        prevday = theday - datetime.timedelta(days=1)
        prevdate = prevday.strftime(u"%Y-%m-%d")

        records = read_log()
        data = []

        for event in records:
            # return any records starting on this date
            if u"date" not in qdict or event[u"date"] == thedate:
                data.append(event)
                # also return any records starting the day before and completing after midnight
            if event[u"date"] == prevdate:
                if (
                    int(event[u"start"].split(":")[0]) * 60
                    + int(event[u"start"].split(u":")[1])
                    + int(event[u"duration"].split(u":")[0])
                    > 24 * 60
                ):
                    data.append(event)

        web.header(u"Content-Type", u"application/json")
        return json.dumps(data)


class water_log(ProtectedPage):
    """Simple Log API"""

    def GET(self):
        records = read_log()
        data = _(u"Date, Start Time, Zone, Duration, Program") + u"\n"
        for r in records:
            event = ast.literal_eval(json.dumps(r))
            data += (
                event[u"date"]
                + u", "
                + event[u"start"]
                + u", "
                + str(event[u"station"] + 1)
                + u", "
                + event[u"duration"]
                + ", "
                + event[u"program"]
                + u"\n"
            )

        web.header(u"Content-Type", u"text/csv")
        return data


class rain_sensor_state(ProtectedPage):
    """Return rain sensor state."""

    def GET(self):
        return gv.sd[u"rs"]
