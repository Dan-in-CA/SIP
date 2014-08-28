import os
import re
import time
import datetime
import web

import gv
from helpers import *
from gpio_pins import set_output
from ospy import template_render

__author__ = 'Rimco'

class WebPage(object):
    def __init__(self):
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()

class ProtectedPage(WebPage):
    def __init__(self):
        checkLogin()
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
            raise web.seeother('/')


class logout(WebPage):
    def GET(self):
        web.config._session.user = 'anonymous'
        raise web.seeother('/')

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
        if qdict.has_key('rsn') and qdict['rsn'] == '1':
            stop_stations()
            raise web.seeother('/')
        if qdict.has_key('en') and qdict['en'] == '':
            qdict['en'] = '1' # default
        elif qdict.has_key('en') and qdict['en'] == '0':
            gv.srvals = [0] * (gv.sd['nst']) # turn off all stations
            set_output()
        if qdict.has_key('mm') and qdict['mm'] == '0':
            clear_mm()
        if qdict.has_key('rd') and qdict['rd'] != '0' and qdict['rd'] != '':
            gv.sd['rd'] = float(qdict['rd'])
            gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
            stop_onrain()
        elif qdict.has_key('rd') and qdict['rd'] == '0':
            gv.sd['rdst'] = 0
        for key in qdict.keys():
            try:
                gv.sd[key] = int(qdict[key])
            except Exception:
                pass
        jsave(gv.sd, 'sd')
        raise web.seeother('/')# Send browser back to home page


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
        if qdict.has_key('opw') and qdict['opw'] != "":
            try:
                if passwordHash(qdict['opw'], gv.sd['salt']) == gv.sd['password']:
                    if qdict['npw'] == "":
                        raise web.seeother('/vo?errorCode=pw_blank')
                    elif qdict['cpw'] != '' and qdict['cpw'] == qdict['npw']:
                        gv.sd['password'] = passwordHash(qdict['npw'], gv.sd['salt'])
                    else:
                        raise web.seeother('/vo?errorCode=pw_mismatch')
                else:
                    raise web.seeother('/vo?errorCode=pw_wrong')
            except KeyError:
                pass

        try:
            if qdict.has_key('oipas') and (qdict['oipas'] == 'on' or qdict['oipas'] == ''):
                gv.sd['ipas'] = 1
            else:
                gv.sd['ipas'] = 0
        except KeyError:
            pass

        if qdict.has_key('oname'):
            gv.sd['name'] = qdict['oname']
        if qdict.has_key('oloc'):
            gv.sd['loc'] = qdict['oloc']
        if qdict.has_key('otz'):
            gv.sd['tz'] = int(qdict['otz'])
        try:
            if qdict.has_key('otf') and (qdict['otf'] == 'on' or qdict['otf'] == ''):
                gv.sd['tf'] = 1
            else:
                gv.sd['tf'] = 0
        except KeyError:
            pass

        if int(qdict['onbrd']) + 1 != gv.sd['nbrd']: self.update_scount(qdict)
        gv.sd['nbrd'] = int(qdict['onbrd']) + 1

        gv.sd['nst'] = gv.sd['nbrd'] * 8
        if qdict.has_key('ohtp'):
            gv.sd['htp'] = int(qdict['ohtp'])
        if qdict.has_key('osdt'):
            gv.sd['sdt'] = int(qdict['osdt'])

        if qdict.has_key('omas'):
            gv.sd['mas'] = int(qdict['omas'])
        if qdict.has_key('omton'):
            gv.sd['mton'] = int(qdict['omton'])
        if qdict.has_key('omtoff'):
            gv.sd['mtoff'] = int(qdict['omtoff'])
        if qdict.has_key('owl'):
            gv.sd['wl'] = int(qdict['owl'])

        if qdict.has_key('ours') and (qdict['ours'] == 'on' or qdict['ours'] == '1'):
            gv.sd['urs'] = 1
        else:
            gv.sd['urs'] = 0

        if qdict.has_key('oseq') and (qdict['oseq'] == 'on' or qdict['oseq'] == '1'):
            gv.sd['seq'] = 1
        else:
            gv.sd['seq'] = 0

        if qdict.has_key('orst') and (qdict['orst'] == 'on' or qdict['orst'] == '1'):
            gv.sd['rst'] = 1
        else:
            gv.sd['rst'] = 0

        if qdict.has_key('olg') and (qdict['olg'] == 'on' or qdict['olg'] == '1'):
            gv.sd['lg'] = 1
        else:
            gv.sd['lg'] = 0

        if qdict.has_key('olr'):
            gv.sd['lr'] = int(qdict['olr'])

        srvals = [0] * (gv.sd['nst']) # Shift Register values
        rovals = [0] * (gv.sd['nst']) # Run Once Durations
        jsave(gv.sd, 'sd')
        if qdict.has_key('rbt') and qdict['rbt'] == '1':
            gv.srvals = [0] * (gv.sd['nst'])
            set_output()
            os.system('reboot')
        raise web.seeother('/')

    def update_scount(self, qdict):
        """Increase or decrease the number of stations displayed when number of expansion boards is changed in options."""
        if int(qdict['onbrd']) + 1 > gv.sd['nbrd']: # Lengthen lists
            incr = int(qdict['onbrd']) - (gv.sd['nbrd'] - 1)
            for i in range(incr):
                gv.sd['mo'].append(0)
                gv.sd['ir'].append(0)
                gv.sd['show'].append(255)
            snames = data('snames')
            nlst = re.findall('[\'"].*?[\'"]', snames)
            ln = len(nlst)
            nlst.pop()
            for i in range((incr * 8) + 1):
                nlst.append("'S" + ('%d' % (i + ln)) + "'")
            nstr = '[' + ','.join(nlst)
            nstr = nstr.replace("', ", "',") + "]"
            save('snames', nstr)
            for i in range(incr * 8):
                gv.srvals.append(0)
                gv.ps.append([0, 0])
                gv.rs.append([0, 0, 0, 0])
            for i in range(incr):
                gv.sbits.append(0)
        elif int(qdict['onbrd']) + 1 < gv.sd['nbrd']: # Shorten lists
            onbrd = int(qdict['onbrd'])
            decr = gv.sd['nbrd'] - (onbrd + 1)
            gv.sd['mo'] = gv.sd['mo'][:(onbrd + 1)]
            gv.sd['ir'] = gv.sd['ir'][:(onbrd + 1)]
            gv.sd['show'] = gv.sd['show'][:(onbrd + 1)]
            snames = data('snames')
            nlst = re.findall('[\'"].*?[\'"]', snames)
            nstr = '[' + ','.join(nlst[:8 + (onbrd * 8)]) + ']'
            save('snames', nstr)
            newlen = gv.sd['nst'] - decr * 8
            gv.srvals = gv.srvals[:newlen]
            gv.ps = gv.ps[:newlen]
            gv.rs = gv.rs[:newlen]
            gv.sbits = gv.sbits[:onbrd + 1]
        return

class view_stations(ProtectedPage):
    """Open a page to view and edit a run once program."""

    def GET(self):
        return template_render.stations()


class change_stations(ProtectedPage):
    """Save changes to station names, ignore rain and master associations."""

    def GET(self):
        qdict = web.input()
        for i in range(gv.sd['nbrd']): # capture master associations
            if qdict.has_key('m' + str(i)):
                try:
                    gv.sd['mo'][i] = int(qdict['m' + str(i)])
                except ValueError:
                    gv.sd['mo'][i] = 0
            if qdict.has_key('i' + str(i)):
                try:
                    gv.sd['ir'][i] = int(qdict['i' + str(i)])
                except ValueError:
                    gv.sd['ir'][i] = 0
            if qdict.has_key('sh' + str(i)):
                try:
                    gv.sd['show'][i] = int(qdict['sh' + str(i)])
                except ValueError:
                    gv.sd['show'][i] = 255
        names = '['
        for i in range(gv.sd['nst']):
            if qdict.has_key('s' + str(i)):
                names += "'" + qdict['s' + str(i)] + "',"
            else:
                names += "'S" + str(i + 1) + "',"
        names += ']'
        gv.snames = names
        save('snames', names.encode('ascii', 'backslashreplace'))
        jsave(gv.sd, 'sd')
        raise web.seeother('/')


class get_station(ProtectedPage):
    """Return a page containing a number representing the state of a station or all stations if 0 is entered as station number."""

    def GET(self, sn):
        if sn == '0':
            status = '<!DOCTYPE html>\n'
            status += ''.join(str(x) for x in gv.srvals)
            return status
        elif int(sn) - 1 <= gv.sd['nbrd'] * 7:
            status = '<!DOCTYPE html>\n'
            status += str(gv.srvals[int(sn) - 1])
            return status
        else:
            return 'Station ' + sn + ' not found.'


class set_station(ProtectedPage):
    """turn a station (valve/zone) on=1 or off=0 in manual mode."""

    def GET(self, nst, t=None): # nst = station number, status, optional duration
        nstlst = [int(i) for i in re.split('=|&t=', nst)]
        if len(nstlst) == 2:
            nstlst.append(0)
        sid = int(nstlst[0]) - 1 # station index
        b = sid / 8 # board index
        if nstlst[1] == 1 and gv.sd['mm']: # if status is on and manual mode is set
            gv.rs[sid][0] = gv.now # set start time to current time
            if nstlst[2]: # if an optional duration time is given
                gv.rs[sid][2] = nstlst[2]
                gv.rs[sid][1] = gv.rs[sid][0] + nstlst[2] # stop time = start time + duration
            else:
                gv.rs[sid][1] = float('inf') # stop time = infinity
            gv.rs[sid][3] = 99 # set program index
            gv.ps[sid][1] = nstlst[2]
            gv.sd['bsy'] = 1
            time.sleep(1)
        if nstlst[1] == 0 and gv.sd['mm']: # If status is off
            gv.rs[sid][1] = gv.now
            time.sleep(1)
        raise web.seeother('/')


class view_runonce(ProtectedPage):
    """Open a page to view and edit a run once program."""

    def GET(self):
        return template_render.runonce()


class change_runonce(ProtectedPage):
    """Start a Run Once program. This will override any running program."""

    def GET(self):
        qdict = web.input()
        if not gv.sd['en']: return # check operation status
        gv.rovals = json.loads(qdict['t'])
        gv.rovals.pop()
        stations = [0] * gv.sd['nbrd']
        gv.ps = [] # program schedule (for display)
        gv.rs = [] # run schedule
        for i in range(gv.sd['nst']):
            gv.ps.append([0, 0])
            gv.rs.append([0, 0, 0, 0])
        for i, v in enumerate(gv.rovals):
            if v: # if this element has a value
                gv.rs[i][0] = gv.now
                gv.rs[i][2] = v
                gv.rs[i][3] = 98
                gv.ps[i][0] = 98
                gv.ps[i][1] = v
                stations[i / 8] += 2 ** (i % 8)
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
            mp = gv.pd[pid][:] # Modified program
            if mp[1] >= 128 and mp[2] > 1: # If this is an interval program
                dse = int(gv.now / 86400)
                rel_rem = (((mp[1] - 128) + mp[2]) - (dse % mp[2])) % mp[
                    2] # Convert absolute to relative days remaining for display
                mp[1] = rel_rem + 128 # Update from saved value.
            prog = str(mp).replace(' ', '')
        return template_render.modify(pid, prog)


class change_program(ProtectedPage):
    """Add a program or modify an existing one."""

    def GET(self):
        qdict = web.input()
        pnum = int(qdict['pid']) + 1 # program number
        cp = json.loads(qdict['v'])
        if cp[0] == 0 and pnum == gv.pon: # if disabled and program is running
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
        if qdict['pid'] == '-1': # add new program
            gv.pd.append(cp)
        else:
            gv.pd[int(qdict['pid'])] = cp # replace program
        jsave(gv.pd, 'programs')
        gv.sd['nprogs'] = len(gv.pd)
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
        raise web.seeother('/vp')


class enable_program(ProtectedPage):
    """Activate or deactivate an existing program(s)."""
 
    def GET(self):
        qdict = web.input()
        gv.pd[int(qdict['pid'])][0] = int(qdict['enable'])
        jsave(gv.pd, 'programs')
        raise web.seeother('/vp')
     

class view_log(ProtectedPage):
    """View Log"""

    def GET(self):
        records = read_log()
        return template_render.log(records)


class clear_log(ProtectedPage):
    """Delete all log records"""

    def GET(self):
        qdict = web.input()
        with open('./data/log.json', 'w') as f:
            f.write('')
        raise web.seeother('/vl')


class run_now(ProtectedPage):
    """Run a scheduled program now. This will override any running programs."""

    def GET(self):
        qdict = web.input()
        pid = int(qdict['pid'])
        p = gv.pd[int(qdict['pid'])] # program data
        if not p[0]: # if program is disabled
            raise web.seeother('/vp')
        stop_stations()
        extra_adjustment = plugin_adjustment()
        for b in range(len(p[7:7 + gv.sd['nbrd']])): # check each station
            for s in range(8):
                sid = b * 8 + s # station index
                if sid + 1 == gv.sd['mas']: continue # skip if this is master valve
                if p[7 + b] & 1 << s: # if this station is scheduled in this program
                    gv.rs[sid][2] = p[6] * gv.sd['wl'] / 100 * extra_adjustment # duration scaled by water level
                    gv.rs[sid][3] = pid + 1 # store program number in schedule
                    gv.ps[sid][0] = pid + 1 # store program number for display
                    gv.ps[sid][1] = gv.rs[sid][2] # duration
        schedule_stations(p[7:7 + gv.sd['nbrd']])
        raise web.seeother('/')


class show_revision(ProtectedPage):
    """Show revision info to the user. Use: [URL of Pi]/rev."""

    def GET(self):
        revpg = '<!DOCTYPE html>\n'
        revpg += 'Python Interval Program for OpenSprinkler Pi<br/><br/>\n'
        revpg += 'Compatable with OpenSprinkler firmware 1.8.3.<br/><br/>\n'
        revpg += 'Includes plugin architecture\n'
        revpg += 'ospy.py revision: ' + str(gv.rev) + '<br/><br/>\n'
        revpg += 'updated ' + gv.rev_date + '\n'
        return revpg


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
                    sbit = (gv.sbits[bid] >> s) & 1
                    irbit = (gv.sd['ir'][bid] >> s) & 1
                    status = {'station': sid, 'status': 'disabled', 'reason': '', 'master': 0, 'programName': '',
                              'remaining': 0}
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

        for r in records:
            event = json.loads(r)

            # return any records starting on this date
            if not (qdict.has_key('date')) or event['date'] == thedate:
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
        data = "Date, Start Time, Zone, Duration, Program\n"
        for r in records:
            event = json.loads(r)
            data += event["date"] + ", " + event["start"] + ", " + str(event["station"]) + ", " + event[
                "duration"] + ", " + event["program"] + "\n"

        web.header('Content-Type', 'text/csv')
        return data