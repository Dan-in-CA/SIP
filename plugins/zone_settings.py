import web, json, time, io, re
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs
<<<<<<< HEAD

urls.extend(['/zone', 'plugins.zone_settings.zone_settings', '/uzone', 'plugins.zone_settings.update_zone_settings']) # Add a new url to open the data entry page

=======
try:
    from apscheduler.scheduler import Scheduler #This is a non-standard module. Needs to be installed in order for this feature to work.
except:
    pass    

urls.extend(['/zone', 'plugins.zone_settings.zone_settings', '/uzone', 'plugins.zone_settings.update_zone_settings']) # Add a new url to open the data entry page.
#sched = Scheduler()
#sched.start() # Start the scheduler
>>>>>>> first commit
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
<<<<<<< HEAD
        # if we ever see 'bad station' we know there was an error somewhere
		data = json.loads(u'{"station": [{"auto": 0, "Pr": 0.0, "ET": 0.0, "type": "rotor", "max": 0.0, "name": "bad station"}], "station_count": 1}')
		try:
            # read station settings from the file, if it exists
			with io.open(r'./data/zone_settings.json', 'r') as data_file: # read zone data
				data = json.load(data_file)
			data_file.close()
			
            # update station names from global variables assuming they have changed
			station_names = zone_names(gv.snames)
=======
		#raw_data = u'{"station": [{"Pr": 0.0, "ET": 0.0, "name": "bad station"}], "station_count": 1}'
		data = json.loads(u'{"station": [{"Pr": 0.0, "ET": 0.0, "name": "bad station"}], "station_count": 1}')
		try:
		# read station settings from the file, if it exists
			with io.open(r'./data/zone_settings.json', 'r') as data_file: # read zone data
				data = json.load(data_file)
			data_file.close()
			# update station names from global in case they have changed
			# data['station_count']=gv.sd['nbrd']*8+8  ## we don't want to use this, we want to use the value from the file here
			station_names = zone_names(gv.snames)
			print "station_count=", data['station_count']
			print station_names
>>>>>>> first commit
			for i in range(0,data['station_count']):
				data['station'][i]['name']=station_names[i]
			
			# has the number of expansion boards changed, and thus the number of stations changed?
			# Note: this doesn't seem well written - I feel there is some way to integrate setting the names with 
<<<<<<< HEAD
			# increasing or decreasing the station count but I'm not feeling clever enough
=======
			# increasing or decreasing the station count
>>>>>>> first commit
			diff = (gv.sd['nbrd']*8)-data['station_count']
			if diff>0:
			# we need to add stations from data dictionary
				for i in range(0,diff):
<<<<<<< HEAD
					dict = {"auto": 0, "Pr": 0.0, "ET": 0.0, "max": 0.0, "type": "rotor", "name": station_names[i+data['station_count']]}
=======
					dict = {"Pr": 0.0, "ET": 0.0, "name": station_names[i+data['station_count']]}
>>>>>>> first commit
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
<<<<<<< HEAD
			# current station names are written to the file but not used when read in (instead they are updated from the global variable)
			# an optimization could to remove station names to save disk space and memory
			for i in range(1,data['station_count']):
				dict = {"auto": 0, "Pr": 0.0, "ET": 0.0, "max": 0.0, "type": "rotor", "name": station_names[i]}
=======
			# current station names are written to the file but not used in current code
			# an optimization could to remove station names to save space
			for i in range(1,data['station_count']):
				dict = {"Pr": 0.0, "ET": 0.0, "name": station_names[i]}
>>>>>>> first commit
				#print "dict=",i,dict
				data['station'].append(dict)
			#print "data=", data['station']
			with io.open('./data/zone_settings.json', 'w', encoding='utf-8') as data_file:
				data_file.write(unicode(json.dumps(data, ensure_ascii=False)))
		return self.render.zone_settings(data)

class update_zone_settings:
    """Save user input to zone_settings.json file """
    def GET(self):
        qdict=web.input()
<<<<<<< HEAD

=======
        #print qdict
        #print qdict["ET1"]
>>>>>>> first commit
        try:
            #read existing station settings from the file, if it exists
            with io.open(r'./data/zone_settings.json', 'r') as data_file: # read zone data
                data = json.load(data_file)
            data_file.close()
        
            for i in range(0,data['station_count']):
<<<<<<< HEAD
                if ('auto'+str(i)) in qdict: data['station'][i]['auto']=qdict["auto"+str(i)]
                else: data['station'][i]['auto']=0
                data['station'][i]['ET']=qdict["ET"+str(i)]
                data['station'][i]['Pr']=qdict["Pr"+str(i)]
                data['station'][i]['max']=qdict["max"+str(i)]
                data['station'][i]['type']=qdict["type"+str(i)]
=======
                data['station'][i]['ET']=qdict["ET"+str(i)]
                data['station'][i]['Pr']=qdict["Pr"+str(i)]
>>>>>>> first commit
		
            #write file back out with updated data
            with io.open('./data/zone_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))

        except IOError:
            return

<<<<<<< HEAD
        raise web.seeother('/auto')
=======
        raise web.seeother('/')

#set_wl() # Runs the function once at load.
#try:
#    sched.add_cron_job(set_wl, day=1) # Run the plugin's function the first day of each month.
#except:
#    pass    
>>>>>>> first commit
