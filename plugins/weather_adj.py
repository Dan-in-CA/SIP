#!/usr/bin/env python
import thread

import web, json, time, re
import gv # Get access to ospi's settings
import urllib, urllib2
from urls import urls # Get access to ospi's URLs

# Add a new url to open the data entry page.
urls.extend(['/wa', 'plugins.weather_adj.settings', '/wj', 'plugins.weather_adj.settings_json', '/uwa', 'plugins.weather_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Weather Based Settings', '/wa'])

# set local variables - used to avoid mulitple dips to the file system
import weather_vars
weather_vars.defaults = {'auto_delay': 'off', 'forecast_delay' : 'off', 'forecast_dd': 24, 'delay_duration': 24, 'weather_provider': 'yahoo', 'wapikey': '', 'wapiStation' : '', 'history_delay' : 'off' , 'rain1' : 0.05 , 'rain1_dd' : 2 , 'rain24' : 0.25 , 'rain24_dd' : 24, 'rain48' : 0.5 ,'rain48_dd' : 24, 'history_delay' : 'off' , 'wind_delay' : 'off' , 'windspeed' : 10, 'wind_dd' : 1, 'temp_delay' : 'off' , 'temp' : 35, 'temp_dd' : 1 }
weather_vars.data = weather_vars.defaults

def weather_to_delay(run_loop=False):
    if run_loop:
        time.sleep(3) # Sleep some time to prevent printing before startup information

    loopDelay = 3600 # sleep time - defined in seconds
    print("Starting weather loop - delay time in seconds : " + str(loopDelay))

    while True:
        get_weather_options() # always fetch at start of loop in case of change
        delay = 0
        weather = get_weather_data() if weather_vars.data['weather_provider'] == "yahoo" else get_wunderground_weather_data()
        if weather == []: # catch exception condition
           delay = -1
           
        if weather_vars.data["auto_delay"] != "off" and gv.sd['rdst'] < (gv.now + loopDelay):  # only check if master switch and rain delay start potential 
            print("Processing Weather info...")
            
            if weather_vars.data["forecast_delay"] != "off" and delay==0:
                delay = code_to_delay(weather["code"])
                
            if delay > 0:
                print("Rain forecasted: " + weather["text"] + ". Adding delay of " + str(delay))
                gv.sd['rd'] = float(delay)
                gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                stop_onrain()
            elif delay == False:
                print("No rain forecast: " + weather["text"] + ". No action.")
            elif delay == 0:
                print("Good weather forecast: " + weather["text"] + ". Removing rain delay.")
                gv.sd['rdst'] = gv.now
#
            if weather_vars.data["wind_delay"] != "off" and weather_vars.data['weather_provider'] != "yahoo" and delay == 0 :
                print("Checking wind...")  # already have weather from prior if
                if float(weather["wind"]) >= float(weather_vars.data["windspeed"]):
                    delay = weather_vars.data["wind_dd"] # set delay
                if delay > 0:
                    print("Wind over limit of : " + str(weather_vars.data["windspeed"]) + " detected: " + str(weather["wind"]) + ". Adding delay of " + + str(weather_vars.data["wind_dd"]))
                    gv.sd['rd'] = float(delay)
                    gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                    stop_onrain()
                else:
                    print("Wind below limit : " + str(weather_vars.data["windspeed"]) + " vs  " + str(weather["wind"]) + ". No action.")
#            
            if weather_vars.data["temp_delay"] != "off" and weather_vars.data['weather_provider'] != "yahoo" and delay == 0 :
                print("Checking tempature...")  # already have weather from prior if
                if float(weather["tempNum"]) < float(weather_vars.data["temp"]):
                    delay = weather_vars.data["temp_dd"] # set delay
                if delay > 0:
                    print("Temp under limit of : " + str(weather_vars.data["temp"]) + " detected: " + weather["temp"] + ". Adding delay of " + + str(weather_vars.data["temp_dd"]))
                    gv.sd['rd'] = float(delay)
                    gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                    stop_onrain()
                else:
                    print("Temp above limit : " + str(weather_vars.data["temp"]) + " vs  " + str(weather["temp"]) + ". No action.")
#            
            if weather_vars.data["history_delay"] != "off" and weather_vars.data["weather_provider"] != "yahoo" and delay == 0  :
                print("Checking current rain...")  # already have weather from prior if
                delay = 0
                if float(weather["rain1"]) > float(weather_vars.data["rain1"]):
                    delay = weather_vars.data['rain1_dd']
                if delay > 0:
                    print("Current rain over limit of : " + str(weather_vars.data["rain1"]) + " rain last hour : " + str(weather["rain1"]) + "in one hour. Adding delay of " + str(delay))
                    gv.sd['rd'] = float(delay)
                    gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                    stop_onrain()
                else:
                    print("Rain below daily limit of : " + str(weather_vars.data["rain1"]) + " rain last hour : " + str(weather["rain1"]) + ". No action.")
#
            if weather_vars.data["history_delay"] != "off" and weather_vars.data["weather_provider"] != "yahoo" and delay == 0  :
                print("Checking rain history...")
                weatherHistory = get_wunderground_weather_yesterday()
                delay = 0
                if float(weather["rainToday"]) > float(weather_vars.data["rain24"]) :
                    delay = weather_vars.data['rain24_dd']
                if delay == 0 and (float(weather["rainToday"]) + float(weatherHistory["rain24"])) > float(weather_vars.data["rain48"]) :
                    delay = weather_vars.data['rain48_dd']
                if delay > 0:
                    print("Rain history - 24hrs: " + str(weather["rainToday"]) + ", 48hrs: " + str(weatherHistory["rain24"]) + ". Adding delay of " + str(delay))
                    gv.sd['rd'] = float(delay)
                    gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                    stop_onrain()
                else:
                    print("History below limits: history - 24hrs: " + str(weather["rainToday"]) + ", 48hrs: " + str(weatherHistory["rain24"]) + " yesterday. No action.")



        if not run_loop:
            break
        time.sleep(loopDelay) # set at top of loop

def get_weather_options():
    try:
        f = open('./data/weather_adj.json', 'r') # Read the options from the file file
        weather_vars.data = json.load(f)
        f.close()

        # set current conditions defaults
        weather_vars.data["forecastText"] = "tbd"
        weather_vars.data["curTempNum"] = 0
        weather_vars.data["curTemp"] = "tbd"
        weather_vars.data["curWind"] = "tbd"
        weather_vars.data["curRain1"] = "tbd"
        weather_vars.data["curRain24"] = "tbd"
        weather_vars.data["curRain48"] = "tbd"
        
        # verify defaults are set
        
        for key in weather_vars.defaults:
            if not key in weather_vars.data:
                weather_vars.data[key] = weather_vars.defaults[key]
                
    except Exception, e:
        print ("No file data - using default")

    return

#Resolve location to LID
def get_wunderground_lid():
    if re.search("pws:",gv.sd['loc']):
        lid = gv.sd['loc'];
    elif weather_vars.data["wapiStation"] != "":
        lid = "pws:" + weather_vars.data["wapiStation"]
    else:
        try:
            data = urllib2.urlopen("http://autocomplete.wunderground.com/aq?h=0&query="+urllib.quote_plus(gv.sd['loc']))
        except urllib2.URLError as e:
            print "HTTP error getting wunderground location : ", e.reason
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
        print "HTTP error getting yahoo location : ", e.reason
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
        print "HTTP error getting yahoo weather : ", e.reason
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
    weather = {"text": newdata.group(1), "code": newdata.group(2), "temp": temp, "tempNum": newdata.group(3), "date": newdata.group(4), "location": loc.group(1)}
    weather_vars.data["curTempNum"] = newdata.group(3)
    weather_vars.data["curTemp"] = temp
    weather_vars.data["forecastText"] = weather["text"]
    return weather;

def get_wunderground_weather_data():
    lid = get_wunderground_lid()
    if lid == "":
        return []
    try:
        data = urllib2.urlopen("http://api.wunderground.com/api/"+weather_vars.data['wapikey']+"/conditions/q/"+lid+".json")
    except urllib2.URLError as e:
        print "HTTP error getting wunderground weather : ", e.reason
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
    weather_vars.data["curTempNum"] = temp_f
    weather_vars.data["curTemp"] = temp
    weather_vars.data["curWind"] = data['current_observation']['wind_mph']
    weather_vars.data["curRain1"] = data['current_observation']['precip_1hr_in']
    weather_vars.data["curRain24"] = data['current_observation']['precip_today_in']
    weather = {"text": data['current_observation']['weather'], "code": code, "temp": temp, "tempNum": temp_f, "wind" : weather_vars.data["curWind"], "rain1" : weather_vars.data["curRain1"], "rainToday" : weather_vars.data["curRain24"], "date": data['current_observation']['observation_time'], "location": data['current_observation']['display_location']['full']}
    weather_vars.data["forecastText"] = weather["text"]
    return weather;

# get yesterday's weather
def get_wunderground_weather_yesterday():
    lid = get_wunderground_lid()
    if lid == "":
        return []
    data = urllib2.urlopen("http://api.wunderground.com/api/"+weather_vars.data['wapikey']+"/yesterday/q/"+lid+".json")
    data = json.load(data)
    if data == None:
        return []
    if 'error' in data['response']:
        return []
    weather_vars.data["curRain48"] = data['history']['dailysummary'][0]['precipi']
    weather = {"rain24" : weather_vars.data["curRain48"]}
    return weather;

#Lookup code and get the set delay
def code_to_delay(code):
    if weather_vars.data['weather_provider'] == "yahoo":
        adverse_codes = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,35,37,38,39,40,41,42,43,44,45,46,47]
        reset_codes = [36]
    else:
        adverse_codes = ["flurries","sleet","rain","snow","tstorms","nt_flurries","nt_sleet","nt_rain","nt_sleet","nt_snow","nt_tstorms"]
        reset_codes = ["sunny", "clear", "mostlysunny", "partlycloudy"]
    if code in adverse_codes:
        return weather_vars.data['forecast_dd']
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
#        get_weather_options() # make sure you have the latest
        weather = get_weather_data() if weather_vars.data['weather_provider'] == "yahoo" else get_wunderground_weather_data()
        if weather_vars.data['weather_provider'] != "yahoo" :
            weather = get_wunderground_weather_yesterday()
        gv.baseurl = web.ctx['home']
        self.render = web.template.render('templates/',globals={ 'gv': gv, 'str': str, 'm_vals' : weather_vars.data})

    def GET(self):
        print "Serving Weather webpage template - no parameters"
        return self.render.weather_adj()


class settings_json:
    """Returns plugin settings in JSON format"""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')  
        web.header('Content-Type', 'application/json')
        return json.dumps(weather_vars.data)


class update:
    """Save user input to weather_adj.json file"""
    def GET(self):
        qdict = web.input()
        if not qdict.has_key('auto_delay'):
            qdict['auto_delay'] = 'off'
        if not qdict.has_key('forecast_delay'):
            qdict['forecast_delay'] = 'off'
        if not "history_delay" in qdict:
            qdict["history_delay"]="off";
        if not "raining_delay" in qdict:
            qdict["raining_delay"]="off";
        if not "wind_delay" in qdict:
            qdict["wind_delay"]="off";
        if not "temp_delay" in qdict:
            qdict["temp_delay"]="off";

#       temporary - catch name change for forecast delay - phone based settings use "auto-delay", "forecast-delay" used internally & webpage
        if qdict['auto_delay'] != 'off' :
            qdict['forecast_delay'] = qdict['auto_delay']
            
#        print('saving the following data : ' + str(qdict))
        f = open('./data/weather_adj.json', 'w') # write the options to the file
        json.dump(qdict, f)
        f.close()
#       set variables by looping through existing set - allows for greater local set then handled by calling routine
        for key in qdict:
            weather_vars.data[key] = qdict[key]  # update local vars to new settings
            
        raise web.seeother('/')

thread.start_new_thread(weather_to_delay, (True,))
