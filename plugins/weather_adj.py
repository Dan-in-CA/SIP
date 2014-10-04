#!/usr/bin/env python
import thread

import web, json, time, re
import gv # Get access to ospi's settings
import urllib, urllib2
from urls import urls # Get access to ospi's URLs

# Add a new url to open the data entry page.
urls.extend(['/wa', 'plugins.weather_adj.settings', '/wj', 'plugins.weather_adj.settings_json', '/uwa', 'plugins.weather_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Weather Adjust Settings', '/wa'])


def weather_to_delay(run_loop=False):
    if run_loop:
        time.sleep(3) # Sleep some time to prevent printing before startup information

    while True:
        data = get_weather_options()
        if data["auto_delay"] != "off":
            print("Checking rain status...")
            weather = get_weather_data() if data['weather_provider'] == "yahoo" else get_wunderground_weather_data()
            if weather != []:
                delay = code_to_delay(weather["code"])
                if delay > 0:
                    print("Rain detected: " + weather["text"] + ". Adding delay of " + str(delay))
                    gv.sd['rd'] = float(delay)
                    gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                    stop_onrain()
                elif delay == -1:
                    str_weather = "Good weather detected: " + weather["text"] + "."
                    if gv.sd['rdst'] > 0:
                        str_weather +=  " Removing rain delay.";
                        gv.sd['rdst'] = 0
                    print(str_weather)
                elif delay == False:
                    print("No rain detected: " + weather["text"] + ". No action.")
        if not run_loop:
            break
        time.sleep(3600)

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
        try:
            data = urllib2.urlopen("http://autocomplete.wunderground.com/aq?h=0&query="+urllib.quote_plus(gv.sd['loc']))
        except urllib2.URLError as e:
            print "Error getting weather: ", e.reason
            return ""
        data = json.load(data)
        if data is None:
            return ""
        lid = "zmw:" + data['RESULTS'][0]['zmw']

    return lid

def get_woeid():
    try:
        data = urllib2.urlopen("http://query.yahooapis.com/v1/public/yql?q=select%20woeid%20from%20geo.placefinder%20where%20text=%22"+urllib.quote_plus(gv.sd["loc"])+"%22").read()
    except urllib2.URLError as e:
        print "Error getting weather: ", e.reason
        return 0
    woeid = re.search("<woeid>(\d+)<\/woeid>", data)
    if woeid == None:
        return 0
    return woeid.group(1)

def get_weather_data():
    woeid = get_woeid()
    if woeid == 0:
        return []
    try:
        data = urllib2.urlopen("http://weather.yahooapis.com/forecastrss?w="+woeid).read();
    except urllib2.URLError as e:
        print "Error getting weather: ", e.reason
        return []
    if data == None:
        return []
    newdata = re.search("<yweather:condition\s+text=\"([\w|\s]+)\"\s+code=\"(\d+)\"\s+temp=\"(\d+)\"\s+date=\"(.*)\"", data)
    loc = re.search("<title>Yahoo! Weather - (.*)<\/title>",data)
    region = re.search("<yweather:location .*?country=\"(.*?)\"\/>",data)
    region = region.group(1);
    if region == "United States" or region == "Bermuda" or region == "Palau":
        temp = str(newdata.group(3))+"&#176;F"
    else:
        temp = str(round((int(newdata.group(3))-32)*(5/9)))+"&#176;C"
    weather = {"text": newdata.group(1), "code": newdata.group(2), "temp": temp, "date": newdata.group(4), "location": loc.group(1)}
    return weather;

def get_wunderground_weather_data():
    options = get_weather_options()
    lid = get_wunderground_lid()
    if lid == "":
        return []
    try:
        data = urllib2.urlopen("http://api.wunderground.com/api/"+options['wapikey']+"/conditions/q/"+lid+".json")
    except urllib2.URLError as e:
        print "Error getting weather: ", e.reason
        return []
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
        adverse_codes = ["flurries","sleet","rain","snow","tstorms","nt_flurries","nt_sleet","nt_rain","nt_sleet","nt_snow","nt_tstorms"]
        reset_codes = ["sunny", "clear", "mostlysunny", "partlycloudy"]
    if code in adverse_codes:
        return data['delay_duration']
    if code in reset_codes:
        return -1
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

thread.start_new_thread(weather_to_delay, (True,))
