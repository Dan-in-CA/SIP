import json
import time
import datetime
import string
import calendar

from helpers import get_cpu_temp, check_login, password_hash
import web
import gv  # Gain access to sip's settings
from urls import urls  # Gain access to sip's URL list
from webpages import ProtectedPage, WebPage

##############
## New URLs ##

urls.extend([
    '/jo', 'plugins.mobile_app.options',
    '/jc', 'plugins.mobile_app.cur_settings',
    '/js', 'plugins.mobile_app.station_state',
    '/jp', 'plugins.mobile_app.program_info',
    '/jn', 'plugins.mobile_app.station_info',
    '/jl', 'plugins.mobile_app.get_logs',
    '/sp', 'plugins.mobile_app.set_password'])


#######################
## Class definitions ##

class options(WebPage):  # /jo
    """Returns device options as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')
        if check_login():
            jopts = {
                "fwv": gv.ver_str+'-SIP',
                "tz": gv.sd['tz'],
                "ext": gv.sd['nbrd'] - 1,
                "seq": gv.sd['seq'],
                "sdt": gv.sd['sdt'],
                "mas": gv.sd['mas'],
                "mton": gv.sd['mton'],
                "mtof": gv.sd['mtoff'],
                "urs": gv.sd['urs'],
                "rso": gv.sd['rst'],
                "wl": gv.sd['wl'],
                "ipas": gv.sd['ipas'],
                "reset": gv.sd['rbt'],
                "lg": gv.sd['lg']
            }
        else:
            jopts = {
                "fwv": gv.ver_str+'-SIP',
            }

        return json.dumps(jopts)

class cur_settings(ProtectedPage):  # /jc
    """Returns current settings as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')
        jsettings = {
            "devt": gv.now,
            "nbrd": gv.sd['nbrd'],
            "en": gv.sd['en'],
            "rd": gv.sd['rd'],
            "rs": gv.sd['rs'],
            "mm": gv.sd['mm'],
            "rdst": gv.sd['rdst'],
            "loc": gv.sd['loc'],
            "sbits": gv.sbits,
            "ps": gv.ps,
            "lrun": gv.lrun,
            "ct": get_cpu_temp(gv.sd['tu']),
            "tu": gv.sd['tu']
        }

        return json.dumps(jsettings)


class station_state(ProtectedPage):  # /js
    """Returns station status and total number of stations as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')
        jstate = {
            "sn": gv.srvals,
            "nstations": gv.sd['nst']
        }

        return json.dumps(jstate)


class program_info(ProtectedPage):  # /jp
    """Returns program data as json."""
    def GET(self):
        lpd = []  # Local program data
        dse = int((time.time()+((gv.sd['tz']/4)-12)*3600)/86400)  # days since epoch
        for p in gv.pd:
            op = p[:]  # Make local copy of each program
            if op[1] >= 128 and op[2] > 1:
                rel_rem = (((op[1]-128) + op[2])-(dse % op[2])) % op[2]
                op[1] = rel_rem + 128
            lpd.append(op)
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')
        jpinfo = {
            "nprogs": gv.sd['nprogs']-1,
            "nboards": gv.sd['nbrd'],
            "mnp": 9999,
            'pd': lpd
        }

        return json.dumps(jpinfo)


class station_info(ProtectedPage):  # /jn
    """Returns station information as json."""
    def GET(self):
        disable = []

        for byte in gv.sd['show']:
            disable.append(~byte&255)

        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')
        jpinfo = {
            "snames": gv.snames,
            "ignore_rain": gv.sd['ir'],
            "masop": gv.sd['mo'],
            "stn_dis": disable,
            "maxlen": gv.sd['snlen']
        }

        return json.dumps(jpinfo)


class get_logs(ProtectedPage):  # /jl
    """Returns log information for specified date range."""
    def GET(self):
        records = self.read_log()
        data = []
        qdict = web.input()

        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')

        if 'start' not in qdict or 'end' not in qdict:
            return []

        for r in records:
            event = json.loads(r)
            date = time.mktime(datetime.datetime.strptime(event["date"], "%Y-%m-%d").timetuple())
            if int(qdict["start"]) <= int(date) <= int(qdict["end"]):
                pid = event["program"]
                if pid == "Run-once":
                    pid = 98
                if pid == "Manual":
                    pid = 99

                pid = int(pid)
                station = int(event["station"])
                duration = string.split(event["duration"], ":")
                duration = (int(duration[0]) * 60) + int(duration[1])
                timestamp = int(time.mktime(utc_to_local(datetime.datetime.strptime(event["date"] + " " + event["start"], "%Y-%m-%d %H:%M:%S")).timetuple())) + duration

                data.append([pid, station, duration, timestamp])

        return json.dumps(data)

    def read_log(self):
        try:
            with open('./data/log.json') as logf:
                records = logf.readlines()
            return records
        except IOError:
            return []


class set_password():
    """Save changes to device password"""
    def GET(self):
        qdict = web.input()
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        web.header('Cache-Control', 'no-cache')

        if not(qdict.has_key('pw')) or not(qdict.has_key('npw')) or not(qdict.has_key('cpw')):
            return json.dumps({"result":3})

        if password_hash(qdict['pw'], gv.sd['salt']) == gv.sd['password']:
            if qdict['npw'] == "":
                return json.dumps({"result":3})
            elif qdict['cpw'] !='' and qdict['cpw'] == qdict['npw']:
                gv.sd['password'] = password_hash(qdict['npw'], gv.sd['salt'])
            else:
                return json.dumps({"result":4})
        else:
            return json.dumps({"result":2})

        return json.dumps({"result":1})


def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= datetime.timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)
