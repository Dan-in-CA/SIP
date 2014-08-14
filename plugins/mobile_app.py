import web, json, re, os
import ast, time, datetime, string
import gv # Gain access to ospi's settings
from urls import urls # Gain access to ospi's URL list

##############
## New URLs ##

urls.extend(['/jo', 'plugins.mobile_app.options', '/jc', 'plugins.mobile_app.cur_settings', '/js', 'plugins.mobile_app.station_state','/jp', 'plugins.mobile_app.program_info', '/jn', 'plugins.mobile_app.station_info', '/jl', 'plugins.mobile_app.get_logs'])

#######################
## Class definitions ##

class options: # /jo
    """Returns device options as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jopts = {"fwv":".".join(list(str(gv.ver)))+"-OSPi","tz":gv.sd['tz'], "ext":gv.sd['nbrd']-1,"seq":gv.sd['seq'],"sdt":gv.sd['sdt'],"mas":gv.sd['mas'],"mton":gv.sd['mton'],"mtof":gv.sd['mtoff'],"urs":gv.sd['urs'],"rso":gv.sd['rst'],"wl":gv.sd['wl'],"ipas":gv.sd['ipas'],"reset":gv.sd['rbt']}
        return json.dumps(jopts)

class cur_settings: # /jc
    """Returns current settings as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jsettings = {"devt":gv.now,"nbrd":gv.sd['nbrd'],"en":gv.sd['en'],"rd":gv.sd['rd'],"rs":gv.sd['rs'],"mm":gv.sd['mm'],"rdst":gv.sd['rdst'],"loc":gv.sd['loc'],"sbits":gv.sbits,"ps":gv.ps,"lrun":gv.lrun,"ct":CPU_temperature(gv.sd['tu']),"tu":gv.sd['tu']}
        return json.dumps(jsettings)

class station_state: # /js
    """Returns station status and total number of stations as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jstate = {"sn":gv.srvals, "nstations":gv.sd['nst']}
        return json.dumps(jstate)

class program_info: # /jp
    """Returns program data as json."""
    def GET(self):
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
        jpinfo = {"nprogs":gv.sd['nprogs']-1,"nboards":gv.sd['nbrd'],"mnp":gv.sd['mnp'], 'pd': lpd}
        return json.dumps(jpinfo)

class station_info: # /jn
    """Returns station information as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        names = data('snames')
        nlst = re.findall('[\'|"](.*?)[\'|"]', names) # Convert names var to string
        jpinfo = {"snames":nlst,"ignore_rain":gv.sd['ir'],"masop":gv.sd['mo'],"maxlen":gv.sd['snlen']}
        return json.dumps(jpinfo)

class get_logs: # /jl
    """Returns log information for specified date range."""
    def GET(self):
        records = self.read_log()
        data = []
        qdict = web.input()

        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')

        if not(qdict.has_key('start')) or not(qdict.has_key('end')):
            return []

        for r in records:
            event = json.loads(r)
            date = totimestamp(datetime.datetime.strptime(event["date"], "%Y-%m-%d"))
            if int(qdict["start"]) <= int(date) <= int(qdict["end"]):
                pid = event["program"]
                if (pid == "Run-once"):
                    pid = 98
                if (pid == "Manual"):
                    pid = 99

                pid = int(pid)
                station = int(event["station"])
                duration = string.split(event["duration"],":")
                duration = (int(duration[0]) * 60) + int(duration[1])
                timestamp = int(totimestamp(datetime.datetime.strptime(event["date"] + " " + event["start"], "%Y-%m-%d %H:%M:%S")))

                data.append([pid,station,duration,timestamp])

        return json.dumps(data)

    def read_log(self):
        try:
            logf = open('./data/log.json')
            records = logf.readlines()
            logf.close()
            return records
        except IOError:
            return []
##############################
#### Function Definitions ####

def totimestamp(dt, epoch=datetime.datetime(1970,1,1)):
    td = dt - epoch
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 1e6

def CPU_temperature(format):
    """Returns the temperature of the Raspberry Pi's CPU."""
    try:
        if gv.platform == '':
            return str(0)
        if gv.platform == 'bo':
            res = os.popen('cat /sys/class/hwmon/hwmon0/device/temp1_input').readline()
            temp = (str(int(float(res)/1000)))
        if gv.platform == 'pi':
            res = os.popen('vcgencmd measure_temp').readline()
            temp =(res.replace("temp=","").replace("'C\n",""))

        if format == 'F':
            return str(9.0/5.0*float(temp)+32)
        else:
            return str(float(temp))
    except:
        pass

def data(dataf):
    """Return contents of requested text file as string or create file if a missing config file."""
    try:
        f = open('./data/'+dataf+'.txt', 'r')
        data = f.read()
        f.close()
    except IOError:
        if dataf == 'snames': ## A config file -- return defaults and create file if not found. ##
            data = "['S1','S2','S3','S4','S5','S6','S7','S8',]"
            f = open('./data/'+dataf+'.txt', 'w')
            f.write(data)
            f.close()
        else:
            return None
    return data
