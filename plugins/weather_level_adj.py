# !/usr/bin/env python
import datetime
from random import randint
from helpers import baseurl, CPU_temperature, data, checkLogin

import web, json, time, re
import os
import gv # Get access to ospy's settings
import urllib, urllib2
from urls import urls # Get access to ospy's URLs
import errno

import thread
from ospy import template_render
from webpages import ProtectedPage


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

urls.extend(['/lwa', 'plugins.weather_level_adj.settings', '/lwj', 'plugins.weather_level_adj.settings_json', '/luwa', 'plugins.weather_level_adj.update']) # Add a new url to open the data entry page.
gv.plugin_menu.append(['Weather-based Water Level', '/lwa']) # Add this plugin to the home page plugins menu

################################################################################
# Web pages:                                                                   #
################################################################################

class settings(ProtectedPage):
    """Load an html page for entering weather-based irrigation adjustments"""

    def GET(self):
        return template_render.weather_level_adj(options_data())

class settings_json(object):
    """Returns plugin settings in JSON format"""

    def GET(self):
        checkLogin()
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(options_data())

class update(object):
    """Save user input to weather_level_adj.json file"""
    def GET(self):
        checkLogin()
        qdict = web.input()
        if not qdict.has_key('auto_wl'):
            qdict['auto_wl'] = 'off'
        with open('./data/weather_level_adj.json', 'w') as f: # write the settings to file
            json.dump(qdict, f)
        check_weather()
        raise web.seeother('/')

################################################################################
# Helper functions:                                                            #
################################################################################

def options_data():
    # Defaults:
    result = {
        'auto_wl': 'off',
        'wl_min': 0,
        'wl_max': 200,
        'days_history': 3,
        'days_forecast': 3,
        'wapikey': ''
    }
    try:
        with open('./data/weather_level_adj.json', 'r') as f: # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in result:
                result[key] = value
    except Exception:
        pass

    return result

# Resolve location to LID
def get_wunderground_lid():
    if re.search("pws:", gv.sd['loc']):
        lid = gv.sd['loc']
    else:
        data = urllib2.urlopen("http://autocomplete.wunderground.com/aq?h=0&query="+urllib.quote_plus(gv.sd['loc']))
        data = json.load(data)
        if data is None:
            return ""
        lid = "zmw:" + data['RESULTS'][0]['zmw']

    return lid

def get_data(suffix, name=None, force=False):
    if name is None:
        name = suffix
    options = options_data()
    path = os.path.join('.', 'data', 'weather_level_history', name)
    directory = os.path.split(path)[0]
    mkdir_p(directory)
    if not os.path.exists(path) or force:
        with open(path, 'wb') as fh:
            req = urllib2.urlopen("http://api.wunderground.com/api/"+options['wapikey']+"/" + suffix)
            while True:
                chunk = req.read(20480)
                if not chunk:
                    break
                fh.write(chunk)

    with file(path, 'r') as fh:
        data = json.load(fh)

    return data

################################################################################
# Info queries:                                                                #
################################################################################

def history_info():
    options = options_data()
    if int(options['days_history']) == 0:
        return {}

    lid = get_wunderground_lid()
    if lid == "":
        return {}

    check_date = datetime.date.today()
    day_delta = datetime.timedelta(days=1)
    check_date -= day_delta

    info = {}
    for index in range(-1, -1 - int(options['days_history']), -1):
        datestring = check_date.strftime('%Y%m%d')
        request = "history_"+datestring+"/q/"+lid+".json"
        data = get_data(request)

        check_date -= day_delta

        if data is None:
            continue
        if 'error' in data['response']:
            continue

        if len(data['history']['dailysummary']) > 0:
            info[index] = data['history']['dailysummary'][0]

    result = {}
    for index, day_info in info.iteritems():
        result[index] = {
            'temp_c': float(day_info['maxtempm']),
            'rain_mm': float(day_info['precipm']),
            'wind_ms': float(day_info['meanwindspdm']) / 3.6,
            'humidity': float(day_info['humidity'])
        }

    return result

def today_info():
    lid = get_wunderground_lid()
    if lid == "":
        return {}

    datestring = datetime.date.today().strftime('%Y%m%d')

    request = "conditions/q/"+lid+".json"
    name = "conditions_"+datestring+"/q/"+lid+".json"
    data = get_data(request, name, True)

    if data is None:
        return {}
    if 'error' in data['response']:
        return {}

    day_info = data['current_observation']

    result = {
        'temp_c': float(day_info['temp_c']),
        'rain_mm': float(day_info['precip_today_metric']),
        'wind_ms': float(day_info['wind_kph']) / 3.6,
        'humidity': float(day_info['relative_humidity'].replace('%', ''))
    }

    return result

def forecast_info():
    options = options_data()
    if int(options['days_forecast']) == 0:
        return {}

    lid = get_wunderground_lid()
    if lid == "":
        return {}

    datestring = datetime.date.today().strftime('%Y%m%d')

    request = "forecast10day/q/"+lid+".json"
    name = "forecast10day_"+datestring+"/q/"+lid+".json"
    data = get_data(request, name)

    if data is None:
        return {}
    if 'error' in data['response']:
        return {}

    info = {}
    for day_index, entry in enumerate(data['forecast']['simpleforecast']['forecastday']):
        info[day_index] = entry

    result = {}
    for index, day_info in info.iteritems():
        if index <= int(options['days_forecast']):
            result[index] = {
                'temp_c': float(day_info['high']['celsius']),
                'rain_mm': float(day_info['qpf_allday']['mm']),
                'wind_ms': float(day_info['avewind']['kph']) / 3.6,
                'humidity': float(day_info['avehumidity'])
            }

    return result

################################################################################
# Main function loop:                                                          #
################################################################################

def check_weather(run_loop=False):
    if run_loop:
        time.sleep(randint(3, 10)) # Sleep some time to prevent printing before startup information

    while True:
        try:
            options = options_data()
            if options["auto_wl"] == "off":
                if 'wl_weather' in gv.sd:
                    del gv.sd['wl_weather']
            else:

                print "Checking weather status..."
                history = history_info()
                forecast = forecast_info()
                today = today_info()

                info = {}

                for day in range(-20, 20):
                    if day in history:
                        day_info = history[day]
                    elif day in forecast:
                        day_info = forecast[day]
                    else:
                        continue

                    info[day] = day_info

                if 0 in info and 'rain_mm' in today:
                    day_time = datetime.datetime.now().time()
                    day_left = 1.0 - (day_time.hour * 60 + day_time.minute) / 24.0 / 60
                    info[0]['rain_mm'] = info[0]['rain_mm'] * day_left + today['rain_mm']

                print 'Using', len(info), 'days of information.'

                total_info = {
                    'temp_c': sum([val['temp_c'] for val in info.values()])/len(info),
                    'rain_mm': sum([val['rain_mm'] for val in info.values()]),
                    'wind_ms': sum([val['wind_ms'] for val in info.values()])/len(info),
                    'humidity': sum([val['humidity'] for val in info.values()])/len(info)
                }

                # We assume that the default 100% provides 4mm water per day (normal need)
                # We calculate what we will need to provide using the mean data of X days around today

                water_needed = 4 * len(info)                                # 4mm per day
                water_needed *= 1 + (total_info['temp_c'] - 20) / 15        # 5 => 0%, 35 => 200%
                water_needed *= 1 + (total_info['wind_ms'] / 100)           # 0 => 100%, 20 => 120%
                water_needed *= 1 - (total_info['humidity'] - 50) / 200     # 0 => 125%, 100 => 75%
                water_needed = round(water_needed, 1)

                water_left = water_needed - total_info['rain_mm']
                water_left = round(max(0, min(100, water_left)), 1)

                water_adjustment = round((water_left / (4 * len(info))) * 100, 1)

                water_adjustment = max(float(options['wl_min']), min(float(options['wl_max']), water_adjustment))

                print 'Water needed (%d days): %.1fmm' % (len(info), water_needed)
                print 'Total rainfall       : %.1fmm' % total_info['rain_mm']
                print '_______________________________-'
                print 'Irrigation needed    : %.1fmm' % water_left
                print 'Weather Adjustment   : %.1f%%' % water_adjustment

                gv.sd['wl_weather'] = water_adjustment

            if not run_loop:
                break
            time.sleep(3600)
        except Exception as err:
            print 'Weather-base water level encountered error:', err
            time.sleep(60)

thread.start_new_thread(check_weather, (True,))
