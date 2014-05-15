import sys
sys.path.insert(0, './plugins')
import web, json, time, io, re
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs
import auto_program 

urls.extend(['/zone', 'plugins.zone_settings.zone_settings', '/uzone', 'plugins.zone_settings.update_zone_settings']) # Add a new url to open the data entry page


def zone_names(snames):
    # station name string contains ['name','name2',]
    zones=re.findall(r"\'(.*?)\'",gv.snames)                                        
    return zones

class zone_settings:
    """Load an html page for entering extra zone data"""
    def __init__(self):
        self.render = web.template.render('templates/', globals={'json':json})
    
    def GET(self):
        # start by setting up our json dictionary with blank station data
        # if we ever see 'bad station' we know there was an error somewhere
        data = json.loads(u'{"station": [{"auto": 0, "Pr": 0.0, "ET": 0.0, "type": "rotor", "max": 0.0, "name": "bad station"}], "station_count": 1}')
        try:
            # read station settings from the file, if it exists
            with io.open(r'./data/zone_settings.json', 'r') as data_file: # read zone data
                data = json.load(data_file)
            data_file.close()
            
            # update station names from global variables assuming they have changed
            station_names = zone_names(gv.snames)
            for i in range(0,data['station_count']):
                data['station'][i]['name']=station_names[i]
            
            # has the number of expansion boards changed, and thus the number of stations changed?
            # Note: this doesn't seem well written - I feel there is some way to integrate setting the names with 
            # increasing or decreasing the station count but I'm not feeling clever enough
            diff = (gv.sd['nbrd']*8)-data['station_count']
            if diff>0:
            # we need to add stations from data dictionary
                for i in range(0,diff):
                    dict = {"auto": 0, "Pr": 0.0, "ET": 0.0, "max": 0.0, "type": "rotor", "name": station_names[i+data['station_count']]}
                    data['station'].append(dict)
            elif diff<0:
            # we need to remove stations from data dictionary
                for i in range(data['station_count'],gv.sd['nbrd']*8+8):
                    data['station'][i].remove()
            # set station count for use in HTMl file
            data['station_count']=gv.sd['nbrd']*8
        except IOError:
        # if the file doesn't exist, then create it with blank data
            station_names = zone_names(gv.snames)
            data['station_count']=gv.sd['nbrd']*8
            data['station'][0]['name']=station_names[0]
            # current station names are written to the file but not used when read in (instead they are updated from the global variable)
            # an optimization could to remove station names to save disk space and memory
            for i in range(1,data['station_count']):
                dict = {"auto": 0, "Pr": 0.0, "ET": 0.0, "max": 0.0, "type": "rotor", "name": station_names[i]}
                #print "dict=",i,dict
                data['station'].append(dict)
            #print "data=", data['station']
            with io.open('./data/zone_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))
        zone_history = auto_program.getZoneHistory(auto_program.daysWatched)
        # get rainfall total for past 7 days
        rainfall_total = 0
        try:
            # read data from the file, if it exists
            with io.open(r'./data/wx_settings.json', 'r') as wxdata_file: 
                wxdata = json.load(wxdata_file)
            wxdata_file.close()  
            for k in sorted(wxdata['rainfall'], reverse=1):
                rainfall_total += wxdata['rainfall'][str(k)]
            # print "rainfall_total=", rainfall_total
        except IOError:
        # if no rainfall total, skip and keep going (assuming 0 rainfall)
            "ERROR: auto_program: unable to access wx_settings.json file"
            pass        
        return self.render.zone_settings(data,zone_history, rainfall_total, auto_program.metrics, auto_program.daysWatched)

class update_zone_settings:
    """Save user input to zone_settings.json file """
    def GET(self):
        qdict=web.input()

        try:
            #read existing station settings from the file, if it exists
            with io.open(r'./data/zone_settings.json', 'r') as data_file: # read zone data
                data = json.load(data_file)
            data_file.close()
        
            for i in range(0,data['station_count']):
                if ('auto'+str(i)) in qdict: data['station'][i]['auto']=qdict["auto"+str(i)]
                else: data['station'][i]['auto']=0
                data['station'][i]['ET']=qdict["ET"+str(i)]
                data['station'][i]['Pr']=qdict["Pr"+str(i)]
                data['station'][i]['max']=qdict["max"+str(i)]
                data['station'][i]['type']=qdict["type"+str(i)]
        
            #write file back out with updated data
            with io.open('./data/zone_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))

        except IOError:
            return

        raise web.seeother('/auto')
