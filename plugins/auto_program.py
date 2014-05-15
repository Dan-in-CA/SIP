import sys
sys.path.insert(0, './plugins')
import web, json, time, io, re, urllib2, datetime
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs

# Constants #
DAY_ODDEVEN = 0x80
DAYS_OFWEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ZONE_SLOP = .10     # consolidate zones into a single program if they need within ZONE_SLOP inches/week of water
MIN_DURATION = 60   # minimum duration to run a zone, in seconds

# GV.xx - indices for program definition (rs = run schedule - drives the actual valves; ps = program scheduled, used for UI display)
RS_STARTTIME = 0
RS_STOPTIME  = 1
RS_DURATION = 2
RS_PROGID   = 3
PS_PROGID   = 0
PS_DURATION = 1

englishmetrics=['in/hr', 'gal/hr', 'inches']
metricmetrics=['mm/hr', 'l/hr', 'mm']

# global variables #
auto_job = 0        # cron job that executes daily
daysWatched = 7     # number of days to consider when calculating water usage and rainfall data
metrics=englishmetrics

# allows other modules to update settings
def updateSettings(m, d):
    global daysWatched
    global metrics
    # print "updateSettings:", d, m
    daysWatched = d
    metrics=m
    return
    
try:
    from apscheduler.scheduler import Scheduler #This is a non-standard module. Needs to be installed in order for this feature to work.
except ImportError:
    pass

try:
    sched = Scheduler()
    sched.start() # Start the scheduler
except NameError:
    pass    

urls.extend(['/auto', 'plugins.auto_program.auto_program', '/uap', 'plugins.auto_program.update_auto_program', '/rap', 'plugins.auto_program.start_auto_program']) # Add a new url to open the data entry page
    
def runAutoProgram():
    global daysWatched
    global metrics
    days=[0,0]
    zone_history=[]

    wx_settings.checkRain()
    if not gv.sd['en']: return # check operation status
    if gv.sd['rd'] or (gv.sd['urs'] and gv.sd['rs']): # If rain delay or rain detected by sensor then exit
        return

    # this routine will create a new program for today based on historical rainfall total and last 7 day watering
    try:
        # read data from the file, if it exists
        with io.open(r'./data/auto_settings.json', 'r') as data_file: 
            data = json.load(data_file)
        data_file.close()  
        daysWatched = data['daysWatched']
        if data['metrics'] == 'english': metrics=englishmetrics
        elif data['metrics'] == 'metric': metrics=metricmetrics       
    except IOError:
        # if the data file doesn't exist, then create it with the blank data
        print "auto_program: no auto_settings.json file found, creating defaults"
        data = json.loads(u'{"days": ["Mon"], "restrict": "none", "startTimeHour": 0, "startTimeMin": 0, "enabled": 0, "simulate": "0"}')
        data['daysWatched'] = daysWatched
        if metrics==englishmetrics: data['metrics']="english"
        elif metrics==metricmetrics: data['metrics']="metric"
        with io.open('./data/auto_settings.json', 'w', encoding='utf-8') as data_file:
            data_file.write(unicode(json.dumps(data, ensure_ascii=False)))
        pass
        
    #only execute if auto_programming is enabled
    if data['enabled']==0: 
        "auto_program: disabled, exiting"
        return

    # get rainfall total for past 7 days
    rainfall_total = 0
    try:
        # read data from the file, if it exists
        with io.open(r'./data/wx_settings.json', 'r') as wxdata_file: 
            wxdata = json.load(wxdata_file)
        wxdata_file.close()  
        for k in sorted(wxdata['rainfall'], reverse=1):
            rainfall_total += wxdata['rainfall'][str(k)]
    except IOError:
    # if no rainfall total, skip and keep going (assuming 0 rainfall)
        "ERROR: auto_program: unable to access wx_settings.json file"
        pass

    zone_history = getZoneHistory(daysWatched)
    
    # the program will be created with pid (program ID) of one more than the maximum # of programs
    #autoPid = gv.sd['mnp']+1
    autoPid=97  # probably should be a constant?

    t=datetime.date.today()

    # do we water today?
    if data['restrict'] != 'none':
        if (t.day()%2)==0:
        # even day
            if data['odd']: return
            elif data['even']: return
    if not t.strftime("%a") in data['days']: return

#    if t.strftime("%a") == "Mon": days[0] |= 1
#    elif t.strftime("%a") == "Tue": days[0] |= 2
#    elif t.strftime("%a") == "Wed": days[0] |= 4
#    elif t.strftime("%a") == "Thu": days[0] |= 8
#    elif t.strftime("%a") == "Fri": days[0] |= 16
#    elif t.strftime("%a") == "Sat": days[0] |= 32
#    elif t.strftime("%a") == "Sun": days[0] |= 64

    gv.ps = [] # program schedule (for display)
    gv.rs = [] # run schedule
    for i in range(gv.sd['nst']):
        gv.ps.append([0,0])
        gv.rs.append([0,0,0,0])   
    
    try:
        #read existing station settings from the file, if it exists
        with io.open(r'./data/zone_settings.json', 'r') as zonedata_file: # read zone data
            zonedata = json.load(zonedata_file)
        zonedata_file.close()
        print "auto_program starting automatic program loop"
        accumulate_time = gv.now
        for z in range(0, zonedata['station_count']):
            if z+1 == gv.sd['mas']: continue            # skip master station
            if zonedata['station'][z]['auto']:          # only work on zones that are automated
                #print "ap - zone", str(z)," auto state=", str(zonedata['station'][z]['auto'])
                # Pr = in/hour; zone_history = time in seconds zone was on last 7 days
                # Pr / 60 = in/minute; zone_history/60 = time in minutes
                # water_placed  = (Pr/60 in/min) * (history/60 in/min) + rainfall_total (as long as rainfall doesn't exceed the runoff limit!)
                water_placed = ((float(zonedata['station'][z]['Pr'])/60) * (zone_history[z]/60)) + min(rainfall_total, zonedata['station'][z]['max'])
                #print "ap - zone", str(z)," water_placed = ", water_placed
                # print "auto_program: ", z, water_placed, "in placed", zonedata['station'][z]['ET'], 'in needed per week'
                if water_placed > float(zonedata['station'][z]['ET']): continue     # zone has enough water, so skip
                water_needed= float(zonedata['station'][z]['ET'])-water_placed      # water_needed in inches
                # cap water_needed at max before runoff
                if water_needed>float(zonedata['station'][z]['max']): water_needed = float(zonedata['station'][z]['max'])
                if water_needed<0: water_needed = 0
                if float(zonedata['station'][z]['Pr']):           # if Pr set, then use it
                    duration = (water_needed / float(zonedata['station'][z]['Pr'])) * 3600 # (in_needed / in/hour) * 3600 = duration in seconds
                else:
                    duration = 0
                #print "ap zone", str(z)," needs ", water_needed, " - duration ", duration,"s"
                if duration < MIN_DURATION: continue            # don't water too little
                duration *= gv.sd['wl']/100                     # modify duration by water level if set
                if gv.sd['seq']: # sequential mode
                    gv.rs[z][RS_STARTTIME] = accumulate_time
                    gv.rs[z][RS_DURATION] = int(duration)   # store duration scaled by water level
                    accumulate_time += int(duration)
                    gv.rs[z][RS_STOPTIME] = accumulate_time
                    accumulate_time += gv.sd['sdt']         # add station delay
                    gv.rs[z][RS_PROGID] = autoPid           # store program number for scheduling                                 
                    gv.ps[z][PS_PROGID] = autoPid           # store program number for display
                    gv.ps[z][PS_DURATION] = int(duration)
                else: # concurrent mode
                    if duration < gv.rs[z][RS_DURATION]:    # If duration is shorter than any already set for this station
                        continue
                    else:    
                        gv.rs[z][RS_DURATION] = int(duration)
                        gv.rs[z][RS_PROGID] = autoPid # store program number
                        gv.ps[z][PS_PROGID] = autoPid # store program number for display
                        gv.ps[z][PS_DURATION] = int(duration)

            #else: print "auto_program: zone ", x, " not automated"

        gv.sd['bsy'] = 1
            
    except IOError:
        # if we can't find the zone file, get out!
        # FIXME: need to write an error or something?
        print "ERROR: auto_program: unable to load zone_settings.json file"
        return
    #
    #jsave(gv.pd, 'programs') # save programs file
    #gv.sd['nprogs'] = len(gv.pd) # set the length correctly
    return

class auto_program:
    """Load an html page for entering extra wx settings"""
    def __init__(self):
        self.render = web.template.render('templates/', globals={'json':json,'sorted':sorted})
    
    def GET(self):
        try:
            # read data from the file, if it exists
            with io.open(r'./data/auto_settings.json', 'r') as data_file: 
                data = json.load(data_file)
            data_file.close()  
    #        print data
        except IOError:
        # if the data file doesn't exist, then create it with the blank data
            data = json.loads(u'{"days": ["Mon"], "restrict": "none", "startTimeHour": 0, "startTimeMin": 0, "enabled": 0, "simulate": "0"}')
            with io.open('./data/auto_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))

        return self.render.auto_program(data)

class start_auto_program:
    def GET(self):
        qdict=web.input()
        runAutoProgram()
        raise web.seeother('/')
        
class update_auto_program:
    """Save user input to wx_settings.json file """
    def GET(self):
        qdict=web.input()
#        print qdict
        try:
            # read data from the file, if it exists
            with io.open(r'./data/auto_settings.json', 'r') as data_file: 
                data = json.load(data_file)
            data_file.close()  
            data['startTimeHour']=qdict['startTimeHour']
            data['startTimeMin']=qdict['startTimeMin']
            data['restrict']=qdict['restrict']
            data['simulate']=qdict['simulate']
            data['daysWatched'] = daysWatched
            data['metrics'] = metrics
            if qdict['enabled']=='1': data['enabled']= 1
            else: data['enabled']= 0
            data['days']=[]
            for x in DAYS_OFWEEK:
                if x in qdict: data['days'].append(x)
            with io.open('./data/auto_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))
            data_file.close()
            # if asked, turn on simulation mode which will stop all GPIO
            if data['simulate']=='1': gv.simulate = True
            else: gv.simulate = False
        except IOError:
            return

        global auto_job
        if auto_job: 
            sched.unschedule_job(auto_job)
            auto_job=0
        auto_job=sched.add_cron_job(runAutoProgram, hour=data['startTimeHour'], minute=data['startTimeMin']) # Run the plugin's function daily per setting
            
        raise web.seeother('/auto')

def getZoneHistory(limit):
    zh = []
    for x in range(0, gv.sd['nbrd']*8): zh.append(0) # setup zone history list to have 0 in all locations
    try:
        logf = open('static/log/water_log.csv')
        for line in logf:
            log_line = line.strip().split(',') # parse log entry line
            
            if log_line[0]=='Program': continue # skip first line
            
            #check date and break out if we're past our limit
            end_date=log_line[5] # date program ended
            delta = datetime.datetime.today()-datetime.datetime.strptime(end_date, " %a. %d %B %Y")
            if delta.days > limit: break
            z = int(log_line[1])-1 # zone number in log is 1-based
            # otherwise, pull out the run duration and modify the zone list to include the seconds of run time
            m= re.search(r'(\d+)(?=m)', log_line[3])
            s= re.search(r'(\d+)(?=s)', log_line[3])
            if m: zh[z]+=int(m.group())*60
            if s: zh[z]+=int(s.group())
        logf.close()
    except IOError:
        # return the list with all 0 - assume no usage
        pass
    return zh

import wx_settings
    
# call once on load for testing only
#with io.open('./data/gv.json', 'w', encoding='utf-8') as data_file:
#    data_file.write(unicode(json.dumps(gv.rs, ensure_ascii=False)))
#    data_file.write(unicode(json.dumps(gv.ps, ensure_ascii=False)))
#data_file.close()
#runAutoProgram()
with io.open(r'./data/auto_settings.json', 'r') as apdata_file: 
    apdata = json.load(apdata_file)
apdata_file.close()  
auto_job=sched.add_cron_job(runAutoProgram, hour=apdata['startTimeHour'], minute=apdata['startTimeMin']) # Run the plugin's function daily per setting
print "auto_program: job scheduled", auto_job