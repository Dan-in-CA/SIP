import web, json, time, io, re, urllib2, datetime
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs
try:
    from apscheduler.scheduler import Scheduler #This is a non-standard module. Needs to be installed in order for this feature to work.
except ImportError:
    pass

urls.extend(['/wx', 'plugins.wx_settings.wx_settings', '/uwx', 'plugins.wx_settings.update_wx_settings']) # Add a new url to open the data entry page
try:
    sched = Scheduler()
    sched.start() # Start the scheduler
except NameError:
    pass    
    
@sched.cron_schedule(hour=1)
def getDailyRainfall():
    #do we have yesterdays rainfall data already?
    print "Getting rainfall history..."
    try:
        # read data from the file, if it exists
        with io.open(r'./data/wx_settings.json', 'r') as data_file: 
            data = json.load(data_file)
        data_file.close()  
#        print data
    except IOError:
    # if the data file doesn't exist, then create it with the blank data
        data = json.loads(u'{"wx": {"apikey": "1234", "useWU": 0, "pws":"KTXSPRIN55"}, "rainfall": {"2000-01-01": 0.0}, "startTimeHour": 0, "startTimeMin": 0, "enabled": 0}')
        for i in range(1,8):
            d = datetime.date.today() - datetime.timedelta(days=i)
            if data['wx']['useWU']:
                data['rainfall'][str(d)] = getWUHistoryRain(d, data['wx']['apikey'],data['wx']['pws'])
            else: data['rainfall'][str(d)]=0.0
        with io.open('./data/wx_settings.json', 'w', encoding='utf-8') as data_file:
            data_file.write(unicode(json.dumps(data, ensure_ascii=False)))

    t = datetime.date.today()
    y = t-datetime.timedelta(days=1)

    if str(y) not in data['rainfall']: 
        # if not, recreate past 7 days rainfall data
        for i in range(1,8):
            d = datetime.date.today() - datetime.timedelta(days=i)
            if data['wx']['useWU']:
                data['rainfall'][str(d)] = getWUHistoryRain(d, data['wx']['apikey'],data['wx']['pws'])
            else: data['rainfall'][str(d)]=0.0
        with io.open('./data/wx_settings.json', 'w', encoding='utf-8') as data_file:
            data_file.write(unicode(json.dumps(data, ensure_ascii=False)))
    
    # delete entries older than 14 days from memory, we're only using 2nd week for display
    oldest = t-datetime.timedelta(days=14)
    for k, val in data['rainfall'].items():
        if datetime.datetime.strptime(k,"%Y-%m-%d").date() < oldest:
            del data['rainfall'][k]
    return

class wx_settings:
    """Load an html page for entering extra wx settings"""
    def __init__(self):
        self.render = web.template.render('templates/', globals={'json':json,'sorted':sorted})
    
    def GET(self):
        # start by setting up our json dictionary with blank weather data
        #data = json.loads(u'{"wx": {"apikey": "1234", "useWU": 0, "pws":"KTXSPRIN55"}, "rainfall": {"2000-01-01": 0.0}}')
        try:
            # read wx settings from the file, if it exists
            with io.open(r'./data/wx_settings.json', 'r') as data_file: 
                data = json.load(data_file)
            data_file.close()  
        except IOError:
        # if the file doesn't exist, then create it with the blank data - this should never happen!
            data = json.loads(u'{"wx": {"apikey": "1234", "useWU": 0, "pws":"KTXSPRIN55"}, "rainfall": {"2000-01-01": 0.0}, "startTimeHour": 0, "startTimeMin": 0, "enabled": 0}')
            with io.open('./data/wx_settings.json', 'w', encoding='utf-8') as data_file:
                    data_file.write(unicode(json.dumps(data, ensure_ascii=False)))
        
        return self.render.wx_settings(data)

class update_wx_settings:
    """Save user input to wx_settings.json file """
    def GET(self):
        qdict=web.input()
        try:
            #write file back out with updated data
            #data = json.loads(u'{"wx": {"apikey": "1234", "useWU": 0, "pws": "KTXSPRING55"}, "rainfall": {"05/01/14": 0.0}}')
            # read wx settings from the file, if it exists, that way we keep field settings even if WU use is disabled
            with io.open(r'./data/wx_settings.json', 'r') as data_file: 
                data = json.load(data_file)
            data_file.close()    
            if 'useWU' in qdict: 
                data['wx']['useWU'] = 1
                data['wx']['apikey']=str(qdict['apikey'])
                data['wx']['pws']=str(qdict['pws'])
            else: data['wx']['useWU'] = 0
            with io.open('./data/wx_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))

        except IOError:
            return

        raise web.seeother('/auto')

## Version that uses try/except to print an error message if the
## urlopen() fails.
def wget(url):
    #proxy = urllib2.ProxyHandler({'http': 'proxy.houston.hp.com:8080'})
    #opener = urllib2.build_opener(proxy)
    #urllib2.install_opener(opener)
    try:
        ufile = urllib2.urlopen(url)
    except IOError:
        # print 'problem reading url:', url
        return 0
    return ufile

# ------------------------------------------------------------------
# getWUHistoryRain
#  - returns a floating point value that represents the total rainfall from specified date
#
def getWUHistoryRain(d, apikey, pws):
    # if we are using wunderground.com as a data source, then pull from their api using the configured key
    url = r'http://api.wunderground.com/api/'+str(apikey)+r'/history_'+ str(d) + r'/q/pws:' + pws + r'.json'
    json_data = wget(url)
    if (json_data): data = json.load(json_data)
    else: return 0.0

    return float(data['history']['dailysummary'][0]['precipi'])

# ------------------------------------------------------------------
# getYesterdayRain
#  - returns a floating point value that represents the total rainfall from yesterday
#
def getWUYesterdayRain(apikey, pws):

    # if we are using wunderground.com as a data source, then pull from their api using the configured key
    url = r'http://api.wunderground.com/api/' + apikey + r'/yesterday/q/pws:' + pws + r'.json'
    json_data = wget(url)
    if (json_data): data = json.load(json_data)
    else: return 0.0
#   print 'hour:', hr, 'date:', data['history']['observations'][hr]['date']['pretty'], 'data:', data['history']['observations'][hr]['precip_totali']
#	day = parseDay(data['history']['observations'][23]['date']['pretty'])
#	print day, ':', rainfall, 'in'
	
    return float(data['history']['observations'][23]['precip_totali'])

# call once on load
getDailyRainfall()
