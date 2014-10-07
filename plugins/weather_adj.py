# !/usr/bin/env python
from random import randint
import thread
import json
import time
import re
import urllib
import urllib2

import web
import gv  # Get access to ospi's settings
from urls import urls  # Get access to ospi's URLs
from gpio_pins import set_output
from ospi import template_render
from webpages import ProtectedPage


# Add a new url to open the data entry page.
urls.extend(['/wa', 'plugins.weather_adj.settings',
             '/wj', 'plugins.weather_adj.settings_json',
             '/uwa', 'plugins.weather_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Weather-based Rain Delay', '/wa'])


def weather_to_delay(run_loop=False):
    if run_loop:
        time.sleep(randint(3, 10))  # Sleep some time to prevent printing before startup information

    while True:
        data = get_weather_options()
        if data["auto_delay"] != "off":
            print("Checking rain status...")
            weather = get_weather_data() if data['weather_provider'] == "yahoo" else get_wunderground_weather_data()
            delay = code_to_delay(weather["code"])
            if delay > 0:
                print("Rain detected: " + weather["text"] + ". Adding delay of " + str(delay))
                gv.sd['rd'] = float(delay)
                gv.sd['rdst'] = gv.now + gv.sd['rd'] * 3600 + 1  # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
                stop_onrain()
            elif delay == 0:
                print("No rain detected: " + weather["text"] + ". No action.")
            elif delay < 0:
                print("Good weather detected: " + weather["text"] + ". Removing rain delay.")
                gv.sd['rdst'] = gv.now

        if not run_loop:
            break
        time.sleep(3600)


def get_weather_options():
    try:
        with open('./data/weather_adj.json', 'r') as f:  # Read the monthly percentages from file
            data = json.load(f)
    except Exception, e:
        data = {'auto_delay': 'off', 'delay_duration': 24, 'weather_provider': 'yahoo', 'wapikey': ''}

    return data


# Resolve location to LID
def get_wunderground_lid():
    if re.search("pws:", gv.sd['loc']):
        lid = gv.sd['loc']
    else:
        data = urllib2.urlopen("http://autocomplete.wunderground.com/aq?h=0&query=" + urllib.quote_plus(gv.sd['loc']))
        data = json.load(data)
        if data is None:
            return ""
        lid = "zmw:" + data['RESULTS'][0]['zmw']

    return lid


def get_woeid():
    data = urllib2.urlopen(
        "http://query.yahooapis.com/v1/public/yql?q=select%20woeid%20from%20geo.placefinder%20where%20text=%22" +
        urllib.quote_plus(gv.sd["loc"]) + "%22").read()
    woeid = re.search("<woeid>(\d+)</woeid>", data)
    if woeid is None:
        return 0
    return woeid.group(1)


def get_weather_data():
    woeid = get_woeid()
    if woeid == 0:
        return {}
    data = urllib2.urlopen("http://weather.yahooapis.com/forecastrss?w=" + woeid).read()
    if data is None:
        return {}
    newdata = re.search("<yweather:condition\s+text=\"([\w|\s]+)\"\s+code=\"(\d+)\"\s+temp=\"(\d+)\"\s+date=\"(.*)\"",
                        data)
    weather = {"text": newdata.group(1),
               "code": newdata.group(2)}
    return weather


def get_wunderground_weather_data():
    options = get_weather_options()
    lid = get_wunderground_lid()
    if lid == "":
        return []
    data = urllib2.urlopen("http://api.wunderground.com/api/" + options['wapikey'] + "/conditions/q/" + lid + ".json")
    data = json.load(data)
    if data is None:
        return {}
    if 'error' in data['response']:
        return {}
    weather = {"text": data['current_observation']['weather'],
               "code": data['current_observation']['icon']}
    return weather


# Lookup code and get the set delay
def code_to_delay(code):
    data = get_weather_options()
    if data['weather_provider'] == "yahoo":
        adverse_codes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 35, 37, 38, 39, 40, 41, 42,
                         43, 44, 45, 46, 47]
        reset_codes = [36]
    else:
        adverse_codes = ["flurries", "sleet", "rain", "sleet", "snow", "tstorms"]
        adverse_codes += ["chance" + code_name for code_name in adverse_codes]
        reset_codes = ["sunny", "clear", "mostlysunny", "partlycloudy"]
    if code in adverse_codes:
        return float(data['delay_duration'])
    if code in reset_codes:
        return -1
    return 0


def stop_onrain():
    """Stop stations that do not ignore rain."""
    for b in range(gv.sd['nbrd']):
        for s in range(8):
            sid = b * 8 + s  # station index
            if gv.sd['ir'][b] & 1 << s:  # if station ignores rain...
                continue
            elif not all(v == 0 for v in gv.rs[sid]):
                gv.srvals[sid] = 0
                set_output()
                gv.sbits[b] &= ~1 << s  # Clears stopped stations from display
                gv.ps[sid] = [0, 0]
                gv.rs[sid] = [0, 0, 0, 0]
    return


class settings(ProtectedPage):
    """Load an html page for entering weather-based irrigation adjustments"""

    def GET(self):
        return template_render.weather_adj(get_weather_options())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format"""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_weather_options())


class update(ProtectedPage):
    """Save user input to weather_adj.json file"""

    def GET(self):
        qdict = web.input()
        if 'auto_delay' not in qdict:
            qdict['auto_delay'] = 'off'
        with open('./data/weather_adj.json', 'w') as f:  # write the monthly percentages to file
            json.dump(qdict, f)
        weather_to_delay()
        raise web.seeother('/')

thread.start_new_thread(weather_to_delay, (True,))
