# -*- coding: utf-8 -*-

import os
import re
import time
import datetime
import web
import io
import ast

import gv
from helpers import *
from gpio_pins import set_output
from sip import template_render
from blinker import signal

loggedin = signal('loggedin')
def report_login():
    loggedin.send()

value_change = signal('value_change')
def report_value_change():
    value_change.send()

option_change = signal('option_change')
def report_option_change():
    option_change.send()

rebooted = signal('rebooted')
def report_rebooted():
    rebooted.send()

station_names = signal('station_names')
def report_station_names():
    station_names.send()

program_change = signal('program_change')
def report_program_change():
    program_change.send()

program_deleted = signal('program_deleted')
def report_program_deleted():
    program_deleted.send()

program_toggled = signal('program_toggled')
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
            web.config._session.user = 'admin'
            report_login()
            raise web.seeother('/')


class logout(WebPage):
    def GET(self):
        web.config._session.user = 'anonymous'
        raise web.seeother('/')

class sw_restart(ProtectedPage):
    """Restart system."""

    def GET(self):
        restart(1)
        return template_render.restarting()

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
        print 'qdict: ', qdict
        if 'rsn' in qdict and qdict['rsn'] == '1':
            stop_stations()
            raise web.seeother('/')
        if 'en' in qdict and qdict['en'] == '':
            qdict['en'] = '1'  # default
        elif 'en' in qdict and qdict['en'] == '0':
            gv.srvals = [0] * (gv.sd['nst'])  # turn off all stations
            set_output()
        if 'mm' in qdict and qdict['mm'] == '0':
            clear_mm()
        if 'rd' in qdict and qdict['rd'] != '0' and qdict['rd'] != '':
            gv.sd['rd'] = int(float(qdict['rd']))
            gv.sd['rdst'] = int(gv.now + gv.sd['rd'] * 3600) # + 1  # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
            stop_onrain()
        elif 'rd' in qdict and qdict['rd'] == '0':
            gv.sd['rdst'] = 0
        for key in qdict.keys():
            try:
                gv.sd[key] = int(qdict[key])
            except Exception:
                pass
        jsave(gv.sd, 'sd')
        report_value_change()
        raise web.seeother('/')  # Send browser back to home page


class view_options(ProtectedPage):
    """Open the options page for viewing and editing."""

    def GET(self):
        qdict = web.input()
        errorCode = "none"
        if 'errorCode' in qdict:
            errorCode = qdict['errorCode']

        return template_render.options(errorCode)


class change_options(ProtectedPage):
    """Save changes to options made on the options page."""

    def GET(self):
        qdict = web.input()
        if 'opw' in qdict and qdict['opw'] != "":
            try:
                if password_hash(qdict['opw'], gv.sd['salt']) == gv.sd['password']:
                    if qdict['npw'] == "":
                        raise web.seeother('/vo?errorCode=pw_blank')
                    elif qdict['cpw'] != '' and qdict['cpw'] == qdict['npw']:
                        gv.sd['salt'] = password_salt()  # Make a new salt
                        gv.sd['password'] = password_hash(qdict['npw'], gv.sd['salt'])
                    else:
                        raise web.seeother('/vo?errorCode=pw_mismatch')
                else:
                    raise web.seeother('/vo?errorCode=pw_wrong')
            except KeyError:
                pass

        for f in ['name']:
            if 'o'+f in qdict:
                gv.sd[f] = qdict['o'+f]

        for f in ['loc', 'lang']:
            if 'o'+f in qdict:
                if f not in gv.sd or gv.sd[f] != qdict['o'+f]:
                    qdict['rstrt'] = '1'  # force restart with change
                gv.sd[f] = qdict['o'+f]

        if 'onbrd' in qdict:
            if int(qdict['onbrd']) + 1 != gv.sd['nbrd']:
                self.update_scount(qdict)
            gv.sd['nbrd'] = int(qdict['onbrd']) + 1
            gv.sd['nst'] = gv.sd['nbrd'] * 8

        if 'ohtp' in qdict:
            if 'htp' not in gv.sd or gv.sd['htp'] != int(qdict['ohtp']):
                qdict['rbt'] = '1'  # force reboot with change in htp
            gv.sd['htp'] = int(qdict['ohtp'])

        for f in ['sdt', 'mas', 'mton', 'mtoff', 'wl', 'lr', 'tz']:
            if 'o'+f in qdict:
                if f == 'mton'  and int(qdict['o'+f])<0: #handle values less than zero (temp fix)
                    raise web.seeother('/vo?errorCode=mton_minus')                 
                gv.sd[f] = int(qdict['o'+f])

        for f in ['ipas', 'tf', 'urs', 'seq', 'rst', 'lg', 'idd', 'pigpio', 'alr']:
            if 'o'+f in qdict and (qdict['o'+f] == 'on' or qdict['o'+f] == '1'):
                gv.sd[f] = 1
            else:
                gv.sd[f] = 0

        jsave(gv.sd, 'sd')
        report_option_change()
        if 'rbt' in qdict and qdict['rbt'] == '1':
            gv.srvals = [0] * (gv.sd['nst'])
            set_output()
            report_rebooted()
#            os.system('reboot')
            reboot()

        if 'rstrt' in qdict and qdict['rstrt'] == '1':
#            restart(2)
            raise web.seeother('/restart')
        raise web.seeother('/')

    def update_scount(self, qdict):
        """Increase or decrease the number of stations displayed when number of expansion boards is changed in options."""
        if int(qdict['onbrd']) + 1 > gv.sd['nbrd']:  # Lengthen lists
            incr = int(qdict['onbrd']) - (gv.sd['nbrd'] - 1)
            for i in range(incr):
                gv.sd['mo'].append(0)
                gv.sd['ir'].append(0)
                gv.sd['iw'].append(0)
                gv.sd['show'].append(255)
            ln = len(gv.snames)
            for i in range(incr*8):
                gv.snames.append("S"+"{:0>2d}".format(i+1+ln))
            for i in range(incr * 8):
                gv.srvals.append(0)
                gv.ps.append([0, 0])
                gv.rs.append([0, 0, 0, 0])
            for i in range(incr):
                gv.sbits.append(0)
        elif int(qdict['onbrd']) + 1 < gv.sd['nbrd']:  # Shorten lists
            onbrd = int(qdict['onbrd'])
            decr = gv.sd['nbrd'] - (onbrd + 1)
            gv.sd['mo'] = gv.sd['mo'][:(onbrd + 1)]
            gv.sd['ir'] = gv.sd['ir'][:(onbrd + 1)]
            gv.sd['iw'] = gv.sd['iw'][:(onbrd + 1)]
            gv.sd['show'] = gv.sd['show'][:(onbrd + 1)]
            # unused variables
            # nlst = gv.snames
            # nlst = nlst[:8+(onbrd*8)]
            newlen = gv.sd['nst'] - decr * 8
            gv.srvals = gv.srvals[:newlen]
            gv.ps = gv.ps[:newlen]
            gv.rs = gv.rs[:newlen]
            gv.snames = gv.snames[:newlen]
            gv.sbits = gv.sbits[:onbrd + 1]
        jsave(gv.snames, 'snames')


class view_stations(ProtectedPage):
    """Open a page to view and edit a run once program."""

    def GET(self):
        return template_render.stations()


class change_stations(ProtectedPage):
    """Save changes to station names, ignore rain and master associations."""

    def GET(self):
        qdict = web.input()
#        print "qdict from change stations: ", qdict
        for i in range(gv.sd['nbrd']):  # capture master associations
            if 'm' + str(i) in qdict:
                try:
                    gv.sd['mo'][i] = int(qdict['m' + str(i)])
                except ValueError:
                    gv.sd['mo'][i] = 0
            if 'i' + str(i) in qdict:
                try:
                    gv.sd['ir'][i] = int(qdict['i' + str(i)])
                except ValueError:
                    gv.sd['ir'][i] = 0
            if 'w' + str(i) in qdict:
                try:
                    gv.sd['iw'][i] = int(qdict['w' + str(i)])
                except ValueError:
                    gv.sd['iw'][i] = 0
            if 'sh' + str(i) in qdict:
                try:
                    gv.sd['show'][i] = int(qdict['sh' + str(i)])
                except ValueError:
                    gv.sd['show'][i] = 255
            if 'd' + str(i) in qdict:
                try:
                    gv.sd['show'][i] = ~int(qdict['d' + str(i)])&255
                except ValueError:
                    gv.sd['show'][i] = 255
        names = []
        for i in range(gv.sd['nst']):
            if 's' + str(i) in qdict:
                names.append(qdict['s'+str(i)])
            else:
                names.append('S'+"{:0>2d}".format(i+1))
        gv.snames = names
        jsave(names, 'snames')
        jsave(gv.sd, 'sd')
        report_station_names()
        raise web.seeother('/')


class get_set_station(ProtectedPage):
    """Return a page containing a number representing the state of a station or all stations if 0 is entered as station number."""

    def GET(self):
        qdict = web.input()

        sid = get_input(qdict, 'sid', 0, int) - 1
        set_to = get_input(qdict, 'set_to', None, int)
        set_time = get_input(qdict, 'set_time', 0, int)

        if set_to is None:
            if sid < 0:
                status = '<!DOCTYPE html>\n'
                status += ''.join(str(x) for x in gv.srvals)
                return status
            elif sid < gv.sd['nbrd'] * 8:
                status = '<!DOCTYPE html>\n'
                status += str(gv.srvals[sid])
                return status
            else:
                return _('Station ') + str(sid+1) + _(' not found.')
        elif gv.sd['mm']:
            if set_to:  # if status is
                gv.rs[sid][0] = gv.now  # set start time to current time
                if set_time > 0:  # if an optional duration time is given
                    gv.rs[sid][2] = set_time
                    gv.rs[sid][1] = gv.rs[sid][0] + set_time  # stop time = start time + duration
                else:
                    gv.rs[sid][1] = float('inf')  # stop time = infinity
                gv.rs[sid][3] = 99  # set program index
                gv.ps[sid][1] = set_time
                gv.sd['bsy'] = 1
                time.sleep(1)
            else:  # If status is off
                gv.rs[sid][1] = gv.now + 2
                time.sleep(2)
            raise web.seeother('/')
        else:
            return _('Manual mode not active.')


class view_runonce(ProtectedPage):
    """Open a page to view and edit a run once program."""

    def GET(self):
        return template_render.runonce()


class change_runonce(ProtectedPage):
    """Start a Run Once program. This will override any running program."""

    def GET(self):
        qdict = web.input()
        if not gv.sd['en']:   # check operation status
            return
        gv.rovals = json.loads(qdict['t'])
        gv.rovals.pop()
        for sid in range(gv.sd['nst']):
            if gv.srvals[sid]:  # if currently on, log result
                gv.lrun[0] = sid
                gv.lrun[1] = gv.rs[sid][3]
                gv.lrun[2] = int(gv.now - gv.rs[sid][0])
                gv.lrun[3] = gv.now     # think this is unused
                log_run()
                report_station_completed(sid + 1)
        stations = [0] * gv.sd['nbrd']
        gv.ps = []  # program schedule (for display)
        gv.rs = []  # run schedule
        for sid in range(gv.sd['nst']):
            gv.ps.append([0, 0])
            gv.rs.append([0, 0, 0, 0])
        for sid, dur in enumerate(gv.rovals):
            if dur:  # if this element has a value
                gv.rs[sid][0] = gv.now
                gv.rs[sid][2] = dur
                gv.rs[sid][3] = 98
                gv.ps[sid][0] = 98
                gv.ps[sid][1] = dur
                stations[sid / 8] += 2 ** (sid % 8)
        schedule_stations(stations)
        raise web.seeother('/')


class view_programs(ProtectedPage):
    """Open programs page."""

    def GET(self):
        return template_render.programs()


class modify_program(ProtectedPage):
    """Open page to allow program modification."""

    def GET(self):
        qdict = web.input()
        pid = int(qdict['pid'])
        prog = []
        if pid != -1:
            mp = gv.pd[pid][:]  # Modified program
            if mp[1] >= 128 and mp[2] > 1:  # If this is an interval program
                dse = int(gv.now / 86400)
                # Convert absolute to relative days remaining for display
                rel_rem = (((mp[1] - 128) + mp[2]) - (dse % mp[2])) % mp[2]
                mp[1] = rel_rem + 128  # Update from saved value.
            prog = str(mp).replace(' ', '')
        return template_render.modify(pid, prog)


class change_program(ProtectedPage):
    """Add a program or modify an existing one."""

    def GET(self):
        qdict = web.input()
        pnum = int(qdict['pid']) + 1  # program number
        cp = json.loads(qdict['v'])
        if cp[0] == 0 and pnum == gv.pon:  # if disabled and program is running
            for i in range(len(gv.ps)):
                if gv.ps[i][0] == pnum:
                    gv.ps[i] = [0, 0]
                if gv.srvals[i]:
                    gv.srvals[i] = 0
            for i in range(len(gv.rs)):
                if gv.rs[i][3] == pnum:
                    gv.rs[i] = [0, 0, 0, 0]
        if cp[1] >= 128 and cp[2] > 1:
            dse = int(gv.now / 86400)
            ref = dse + cp[1] - 128
            cp[1] = (ref % cp[2]) + 128
        if qdict['pid'] == '-1':  # add new program
            gv.pd.append(cp)
        else:
            gv.pd[int(qdict['pid'])] = cp  # replace program
        jsave(gv.pd, 'programs')
        gv.sd['nprogs'] = len(gv.pd)
        report_program_change()
        raise web.seeother('/vp')


class delete_program(ProtectedPage):
    """Delete one or all existing program(s)."""

    def GET(self):
        qdict = web.input()
        if qdict['pid'] == '-1':
            del gv.pd[:]
            jsave(gv.pd, 'programs')
        else:
            del gv.pd[int(qdict['pid'])]
        jsave(gv.pd, 'programs')
        gv.sd['nprogs'] = len(gv.pd)
        report_program_deleted()
        raise web.seeother('/vp')


class enable_program(ProtectedPage):
    """Activate or deactivate an existing program(s)."""

    def GET(self):
        qdict = web.input()
        gv.pd[int(qdict['pid'])][0] = int(qdict['enable'])
        jsave(gv.pd, 'programs')
        report_program_toggle()
        raise web.seeother('/vp')


class view_log(ProtectedPage):
    """View Log"""

    def GET(self):
        records = read_log()
        return template_render.log(records)


class clear_log(ProtectedPage):
    """Delete all log records"""

    def GET(self):
        with io.open('./data/log.json', 'w') as f:
            f.write(u'')
        raise web.seeother('/vl')


class run_now(ProtectedPage):
    """Run a scheduled program now. This will override any running programs."""

    def GET(self):
        qdict = web.input()
        pid = int(qdict['pid'])
        p = gv.pd[int(qdict['pid'])]  # program data
#        if not p[0]:  # if program is disabled
#           Sraise web.seeother('/vp')
        stop_stations()
        extra_adjustment = plugin_adjustment()
        sid = -1
        for b in range(gv.sd['nbrd']):  # check each station
            for s in range(8):
                sid += 1  # station index
                if sid + 1 == gv.sd['mas']:  # skip if this is master valve
                    continue
                if p[7 + b] & 1 << s:  # if this station is scheduled in this program
                    if gv.sd['idd']:
                        duration = p[-1][sid]
                    else:
                        duration = p[6]
                    if not gv.sd['iw'][b] & 1 << s:
                        duration = duration * gv.sd['wl'] / 100 * extra_adjustment
                    gv.rs[sid][2] = duration
                    gv.rs[sid][3] = pid + 1  # store program number in schedule
                    gv.ps[sid][0] = pid + 1  # store program number for display
                    gv.ps[sid][1] = duration  # duration
        schedule_stations(p[7:7 + gv.sd['nbrd']])
        raise web.seeother('/')


class toggle_temp(ProtectedPage):
    """Change units of Raspi's CPU temperature display on home page."""

    def GET(self):
        qdict = web.input()
        if qdict['tunit'] == "C":
            gv.sd['tu'] = "F"
        else:
            gv.sd['tu'] = "C"
        jsave(gv.sd, 'sd')
        raise web.seeother('/')


class api_status(ProtectedPage):
    """Simple Status API"""

    def GET(self):
        statuslist = []
        for bid in range(0, gv.sd['nbrd']):
            for s in range(0, 8):
                if (gv.sd['show'][bid] >> s) & 1 == 1:
                    sid = bid * 8 + s
                    sn = sid + 1
                    sname = gv.snames[sid]
                    sbit = (gv.sbits[bid] >> s) & 1
                    irbit = (gv.sd['ir'][bid] >> s) & 1
                    status = {'station': sid, 'status': 'disabled', 'reason': '', 'master': 0, 'programName': '',
                              'remaining': 0, 'name': sname}
                    if gv.sd['en'] == 1:
                        if sbit:
                            status['status'] = 'on'
                        if not irbit:
                            if gv.sd['rd'] != 0:
                                status['reason'] = 'rain_delay'
                            if gv.sd['urs'] != 0 and gv.sd['rs'] != 0:
                                status['reason'] = 'rain_sensed'
                        if sn == gv.sd['mas']:
                            status['master'] = 1
                            status['reason'] = 'master'
                        else:
                            rem = gv.ps[sid][1]
                            if rem > 65536:
                                rem = 0

                            id_nr = gv.ps[sid][0]
                            pname = 'P' + str(id_nr)
                            if id_nr == 255 or id_nr == 99:
                                pname = 'Manual Mode'
                            if id_nr == 254 or id_nr == 98:
                                pname = 'Run-once Program'

                            if sbit:
                                status['status'] = 'on'
                                status['reason'] = 'program'
                                status['programName'] = pname
                                status['remaining'] = rem
                            else:
                                if gv.ps[sid][0] == 0:
                                    status['status'] = 'off'
                                else:
                                    status['status'] = 'waiting'
                                    status['reason'] = 'program'
                                    status['programName'] = pname
                                    status['remaining'] = rem
                    else:
                        status['reason'] = 'system_off'
                    statuslist.append(status)
        web.header('Content-Type', 'application/json')
        return json.dumps(statuslist)


class api_log(ProtectedPage):
    """Simple Log API"""

    def GET(self):
        qdict = web.input()
        thedate = qdict['date']
        # date parameter filters the log values returned; "yyyy-mm-dd" format
        theday = datetime.date(*map(int, thedate.split('-')))
        prevday = theday - datetime.timedelta(days=1)
        prevdate = prevday.strftime('%Y-%m-%d')

        records = read_log()
        data = []

        for event in records:
            #event = ast.literal_eval(json.loads(r))

            # return any records starting on this date
            if 'date' not in qdict or event['date'] == thedate:
                data.append(event)
                # also return any records starting the day before and completing after midnight
            if event['date'] == prevdate:
                if int(event['start'].split(":")[0]) * 60 + int(event['start'].split(":")[1]) + int(
                        event['duration'].split(":")[0]) > 24 * 60:
                    data.append(event)

        web.header('Content-Type', 'application/json')
        return json.dumps(data)


class water_log(ProtectedPage):
    """Simple Log API"""

    def GET(self):
        records = read_log()
        data = _("Date, Start Time, Zone, Duration, Program") + "\n"
        for r in records:
            event = ast.literal_eval(json.dumps(r))
            data += event["date"] + ", " + event["start"] + ", " + str(event["station"]+1) + ", " + event[
                "duration"] + ", " + event["program"] + "\n"

        web.header('Content-Type', 'text/csv')
        return data
    
class rain_sensor_state(ProtectedPage):
    """Return rain sensor state."""
    def GET(self):
        return gv.sd['rs']
