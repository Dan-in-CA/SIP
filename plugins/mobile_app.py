import web, json, re, os, time
import gv # Gain access to ospi's settings
from urls import urls # Gain access to ospi's URL list

##############
## New URLs ##

urls.extend(['/jo', 'plugins.mobile_app.options', '/jc', 'plugins.mobile_app.cur_settings', '/js', 'plugins.mobile_app.station_state','/jp', 'plugins.mobile_app.program_info', '/jn', 'plugins.mobile_app.station_info'])

##############################
#### Function Definitions ####

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

#######################
## Class definitions ##

class options: # /jo
    """Returns device options as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jopts = {"fwv":'1.8.3-OSPi',"tz":gv.sd['tz'], "ext":gv.sd['nbrd']-1,"seq":gv.sd['seq'],"sdt":gv.sd['sdt'],"mas":gv.sd['mas'],"mton":gv.sd['mton'],"mtof":gv.sd['mtoff'],"urs":gv.sd['urs'],"rso":gv.sd['rst'],"wl":gv.sd['wl'],"ipas":gv.sd['ipas'],"reset":gv.sd['rbt']}
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
        f = open('./data/snames.txt', 'r')
        names = f.read()
        f.close()
        nlst = re.findall('[\'|"](.*?)[\'|"]', names) # Convert names var to string
        jpinfo = {"snames":nlst,"ignore_rain":gv.sd['ir'],"masop":gv.sd['mo'],"maxlen":gv.sd['snlen']}
        return json.dumps(jpinfo)