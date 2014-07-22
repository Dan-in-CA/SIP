from helpers import checkLogin, CPU_temperature
import web, json, re, os
import ast, time, datetime, string
import gv # Gain access to ospy's settings
from urls import urls # Gain access to ospy's URL list

##############
## New URLs ##

urls.extend(['/jo', 'plugins.mobile_app.options', '/jc', 'plugins.mobile_app.cur_settings', '/js', 'plugins.mobile_app.station_state','/jp', 'plugins.mobile_app.program_info', '/jn', 'plugins.mobile_app.station_info', '/jl', 'plugins.mobile_app.get_logs'])

#######################
## Class definitions ##

class options(object): # /jo
    """Returns device options as json."""
    def GET(self):
        checkLogin()
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jopts = {"fwv":'1.9.0-OSPy',"tz":gv.sd['tz'], "ext":gv.sd['nbrd']-1,"seq":gv.sd['seq'],"sdt":gv.sd['sdt'],"mas":gv.sd['mas'],"mton":gv.sd['mton'],"mtof":gv.sd['mtoff'],"urs":gv.sd['urs'],"rso":gv.sd['rst'],"wl":gv.sd['wl'],"ipas":gv.sd['ipas'],"reset":gv.sd['rbt']}
        return json.dumps(jopts)

class cur_settings(object): # /jc
    """Returns current settings as json."""
    def GET(self):
        checkLogin()
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jsettings = {"devt":gv.now,"nbrd":gv.sd['nbrd'],"en":gv.sd['en'],"rd":gv.sd['rd'],"rs":gv.sd['rs'],"mm":gv.sd['mm'],"rdst":gv.sd['rdst'],"loc":gv.sd['loc'],"sbits":gv.sbits,"ps":gv.ps,"lrun":gv.lrun,"ct":CPU_temperature(gv.sd['tu']),"tu":gv.sd['tu']}
        return json.dumps(jsettings)

class station_state(object): # /js
    """Returns station status and total number of stations as json."""
    def GET(self):
        checkLogin()
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jstate = {"sn":gv.srvals, "nstations":gv.sd['nst']}
        return json.dumps(jstate)

class program_info(object): # /jp
    """Returns program data as json."""
    def GET(self):
        checkLogin()
        lpd = [] # Local program data
        dse = int((time.time()+((gv.sd['tz']/4)-12)*3600)/86400) # days since epoch
        for p in gv.pd:
            op = p[:] # Make local copy of each program
            if op[1] >= 128 and op[2] > 1:
                rel_rem = (((op[1]-128) + op[2])-(dse%op[2]))%op[2]
                op[1] = rel_rem + 128
            lpd.append(op)
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jpinfo = {"nprogs":gv.sd['nprogs']-1,"nboards":gv.sd['nbrd'],"mnp":9999, 'pd': lpd}
        return json.dumps(jpinfo)

class station_info(object): # /jn
    """Returns station information as json."""
    def GET(self):
        checkLogin()
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        names = data('snames')
        nlst = re.findall('[\'|"](.*?)[\'|"]', names) # Convert names var to string
        jpinfo = {"snames":nlst,"ignore_rain":gv.sd['ir'],"masop":gv.sd['mo'],"maxlen":gv.sd['snlen']}
        return json.dumps(jpinfo)

class get_logs(object): # /jl
    """Returns log information for specified date range."""
    def GET(self):
        checkLogin()
        records = self.read_log()
        data = []
        qdict = web.input()

        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')

        if not(qdict.has_key('start')) or not(qdict.has_key('end')):
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
                duration = string.split(event["duration"],":")
                duration = (int(duration[0]) * 60) + int(duration[1])
                timestamp = int(time.mktime(datetime.datetime.strptime(event["date"] + " " + event["start"], "%Y-%m-%d %H:%M:%S").timetuple()))

                data.append([pid,station,duration,timestamp])

        return json.dumps(data)

    def read_log(self):
        try:
            with open('./data/log.json') as logf:
                records = logf.readlines()
            return records
        except IOError:
            return []
##############################
#### Function Definitions ####

def data(dataf):
    """Return contents of requested text file as string or create file if a missing config file."""
    try:
        with open('./data/'+dataf+'.txt', 'r') as f:
            data = f.read()
    except IOError:
        if dataf == 'snames': ## A config file -- return defaults and create file if not found. ##
            data = "['S1','S2','S3','S4','S5','S6','S7','S8',]"
            with open('./data/'+dataf+'.txt', 'w') as f:
                f.write(data)
        else:
            return None
    return data
