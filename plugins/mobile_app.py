import web, json
import gv # Get access to ospi's settings
from urls import urls

##############
## New URLs ##

urls.extend(['/jo', 'plugins.mobile_app.options', '/jc', 'plugins.mobile_app.cur_settings', '/js', 'plugins.mobile_app.station_state','/jp', 'plugins.mobile_app.program_info', '/jn', 'plugins.mobile_app.station_info'])

#######################
## Class definitions ##

class options: # /jo
    """Returns device options as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jopts = {"fwv":203,"tz":gv.sd['tz'],"ntp":1,"dhcp":1,"ip1":192,"ip2":168,"ip3":1,"ip4":22,"gw1":192,"gw2":168,"gw3":1,"gw4":1,"hp0":gv.sd['htp'],"hp1":0,"ar":1,"ext":1,"seq":gv.sd['seq'],"sdt":gv.sd['sdt'],"mas":gv.sd['mas'],"mton":gv.sd['mton'],"mtof":gv.sd['mtoff'],"urs":gv.sd['urs'],"rso":0,"wl":gv.sd['wl'],"stt":10,"ipas":gv.sd['ipas'],"devid":0,"con":110,"lit":100,"ntp1":204,"ntp2":9,"ntp3":54,"ntp4":119,"reset":gv.sd['rbt']}
        return json.dumps(jopts)
    
class cur_settings: # /jc
    """Returns current settings as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jsettings = {"devt":gv.now,"nbrd":gv.sd['nbrd'],"en":gv.sd['en'],"rd":gv.sd['rd'],"rs":gv.sd['rs'],"mm":gv.sd['mm'],"rdst":gv.sd['rdst'],"loc":gv.sd['loc'],"sbits":gv.sbits,"ps":gv.ps,"lrun":gv.lrun}
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
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jpinfo = {"nprogs":gv.sd['nprogs'],"nboards":gv.sd['nbrd'],"mnp":gv.sd['mnp'],"pd":gv.pd}
        return json.dumps(jpinfo)
    
class station_info: # /jn
    """Returns station information as json."""
    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        jpinfo = {"snames":gv.snames,"masop":[255,255],"maxlen":gv.sd['snlen']}
        return json.dumps(jpinfo)