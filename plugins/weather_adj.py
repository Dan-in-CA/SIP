#!/usr/bin/env python

import web, json, time, re
import gv # Get access to ospi's settings
import urllib, urllib2
from urls import urls # Get access to ospi's URLs
try:
    from apscheduler.scheduler import Scheduler #Depends on APScheduler 2.x (does not work with 1.x or 3.x)
except ImportError:
    print "The Python module apscheduler could not be found."
    pass

urls.extend(['/wa', 'plugins.weather_adj.settings', '/wj', 'plugins.weather_adj.settings_json', '/uwa', 'plugins.weather_adj.update']) # Add a new url to open the data entry page.

gv.plugin_menu.append(['Weather Adjust Settings', '/wa']) # Add this plugin to the home page plugins menu

try:
    sched = Scheduler()
    sched.start() # Start the scheduler
except NameError:
    pass

def weather_to_delay():
    data = get_weather_options()
    if data["auto_delay"] == "off":
        return
    print("Checking rain status...")
    weather = get_weather_data() if data['weather_provider'] == "yahoo" else get_wunderground_weather_data()
    delay = code_to_delay(weather["code"])
    if delay == False:
        print("No rain detected")
        return
    print("Rain detected. Adding delay of "+delay)
    gv.sd['rd'] = float(delay)
    gv.sd['rdst'] = gv.now + gv.sd['rd']*3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
    stop_onrain()

def get_weather_options():
    try:
        f = open('./data/weather_adj.json', 'r') # Read the monthly percentages from file
        data = json.load(f)
        f.close()
    except Exception, e:
        data = {'auto_delay': 'off', 'delay_duration': 24, 'weather_provider': 'yahoo', 'wapikey': ''}

    return data

#Resolve location to LID
def get_wunderground_lid():
    if re.search("pws:",gv.sd['loc']):
        lid = gv.sd['loc'];
    else:
        data = urllib2.urlopen("http://autocomplete.wunderground.com/aq?h=0&query="+urllib.quote_plus(gv.sd['loc']))
        data = json.load(data)
        if data is None:
            return ""
        lid = "zmw:" + data['RESULTS'][0]['zmw']

    return lid

def get_woeid():
    data = urllib2.urlopen("http://query.yahooapis.com/v1/public/yql?q=select%20woeid%20from%20geo.placefinder%20where%20text=%22"+urllib.quote_plus(gv.sd["loc"])+"%22").read()
    woeid = re.search("<woeid>(\d+)<\/woeid>", data)
    if woeid == None:
        return 0
    return woeid.group(1)

def get_weather_data():
    woeid = get_woeid()
    if woeid == 0:
        return []
    data = urllib2.urlopen("http://weather.yahooapis.com/forecastrss?w="+woeid).read();
    if data == None:
        return []
    newdata = re.search("<yweather:condition\s+text=\"([\w|\s]+)\"\s+code=\"(\d+)\"\s+temp=\"(\d+)\"\s+date=\"(.*)\"", data)
    loc = re.search("<title>Yahoo! Weather - (.*)<\/title>",data)
    region = re.search("<yweather:location .*?country=\"(.*?)\"\/>",data)
    region = region.group(1);
    if region == "United States" or region == "Bermuda" or region == "Palau":
        temp = str(newdata.group(3))+"&#176;F"
    else:
        temp = str(int(round((newdata.group(3)-32)*(5/9))))+"&#176;C"
    weather = {"text": newdata.group(1), "code": newdata.group(2), "temp": temp, "date": newdata.group(4), "location": loc.group(1)}
    return weather;

def get_wunderground_weather_data():
    options = get_weather_options()
    lid = get_wunderground_lid()
    if lid == "":
        return []
    data = urllib2.urlopen("http://api.wunderground.com/api/"+options['wapikey']+"/conditions/q/"+lid+".json")
    data = json.load(data)
    if data == None:
        return []
    if 'error' in data['response']:
        return []
    region = data['current_observation']['display_location']['country_iso3166']
    temp_c = data['current_observation']['temp_c']
    temp_f = data['current_observation']['temp_f']
    if region == "US" or region == "BM" or region == "PW":
        temp = str(round(temp_f))+"&#176;F"
    else:
        temp = str(temp_c)+"&#176;C"
    if data['current_observation']['icon_url'].find("nt_") >= 0:
        code = "nt_"+data['current_observation']['icon']
    else:
        code = data['current_observation']['icon']
    weather = {"text": data['current_observation']['weather'], "code": code, "temp": temp, "date": data['current_observation']['observation_time'], "location": data['current_observation']['display_location']['full']}
    return weather;

#Lookup code and get the set delay
def code_to_delay(code):
    data = get_weather_options()
    if data['weather_provider'] == "yahoo":
        adverse_codes = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,35,37,38,39,40,41,42,43,44,45,46,47]
        reset_codes = [36]
    else:
        adverse_codes = ["flurries","sleet","rain","sleet","snow","tstorms","nt_flurries","nt_sleet","nt_rain","nt_sleet","nt_snow","nt_tstorms"]
        reset_codes = ["sunny","nt_sunny"]
    if code in adverse_codes:
        return data['delay_duration']
    if code in reset_codes:
        return 0
    return False

def stop_onrain():
    """Stop stations that do not ignore rain."""
    for b in range(gv.sd['nbrd']):
        for s in range(8):
            sid = b*8 + s # station index
            if gv.sd['ir'][b]&1<<s: # if station ignores rain...
                continue
            elif not all(v == 0 for v in gv.rs[sid]):
                gv.srvals[sid] = 0
                set_output()
                gv.sbits[b] = gv.sbits[b]&~1<<s # Clears stopped stations from display
                gv.ps[sid] = [0,0]
                gv.rs[sid] = [0,0,0,0]
    return

class settings:
    """Load an html page for entering weather-based irrigation adjustments"""
    def __init__(self):
        self.render = web.template.render('templates/')

    def GET(self):
        return self.render.weather_adj(get_weather_options())

class settings_json:
    """Returns plugin settings in JSON format"""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_weather_options())

class update:
    """Save user input to weather_adj.json file"""
    def GET(self):
        qdict = web.input()
        if not qdict.has_key('auto_delay'):
            qdict['auto_delay'] = 'off'
        f = open('./data/weather_adj.json', 'w') # write the monthly percentages to file
        json.dump(qdict, f)
        f.close()
        raise web.seeother('/')

weather_to_delay() # Run the plugin on program launch
try:
    sched.add_interval_job(weather_to_delay, hours=1) # Run the plugin's function every hour
except NameError:
    pass
