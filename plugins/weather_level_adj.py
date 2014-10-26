# !/usr/bin/env python
import datetime
from random import randint
from threading import Thread
import sys
import traceback
import shutil
import json
import time
import re
import os
import urllib
import urllib2
import errno

import web
import gv  # Get access to ospi's settings
from urls import urls  # Get access to ospi's URLs
from ospi import template_render
from webpages import ProtectedPage


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

# Add a new url to open the data entry page.
urls.extend(['/lwa',  'plugins.weather_level_adj.settings',
             '/lwj',  'plugins.weather_level_adj.settings_json',
             '/luwa', 'plugins.weather_level_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Weather-based Water Level', '/lwa'])


################################################################################
# Main function loop:                                                          #
################################################################################

class WeatherLevelChecker(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
        self.status = ''

        self._sleep_time = 0

    def add_status(self, msg):
        if self.status:
            self.status += '\n' + msg
        else:
            self.status = msg
        print msg

    def update(self):
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def run(self):
        time.sleep(randint(3, 10))  # Sleep some time to prevent printing before startup information

        while True:
            try:
                self.status = ''
                options = options_data()
                if options["auto_wl"] == "off":
                    if 'wl_weather' in gv.sd:
                        del gv.sd['wl_weather']
                else:

                    print "Checking weather status..."
                    remove_data(['history_', 'conditions_', 'forecast10day_'])

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

                    if not info:
                        self.add_status(str(history))
                        self.add_status(str(today))
                        self.add_status(str(forecast))
                        raise Exception('No information available!')

                    self.add_status('Using %d days of information.' % len(info))

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

                    self.add_status('Water needed (%d days): %.1fmm' % (len(info), water_needed))
                    self.add_status('Total rainfall       : %.1fmm' % total_info['rain_mm'])
                    self.add_status('_______________________________-')
                    self.add_status('Irrigation needed    : %.1fmm' % water_left)
                    self.add_status('Weather Adjustment   : %.1f%%' % water_adjustment)

                    gv.sd['wl_weather'] = water_adjustment

                    self._sleep(3600)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('Weather-base water level encountered error:\n' + err_string)
                self._sleep(60)
            time.sleep(0.5)

checker = WeatherLevelChecker()


################################################################################
# Web pages:                                                                   #
################################################################################

class settings(ProtectedPage):
    """Load an html page for entering weather-based irrigation adjustments"""

    def GET(self):
        return template_render.weather_level_adj(options_data())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format"""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(options_data())


class update(ProtectedPage):
    """Save user input to weather_level_adj.json file"""
    def GET(self):
        qdict = web.input()
        if 'auto_wl' not in qdict:
            qdict['auto_wl'] = 'off'
        with open('./data/weather_level_adj.json', 'w') as f:  # write the settings to file
            json.dump(qdict, f)
        checker.update()
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
        'wapikey': '',
        'status': checker.status
    }
    try:
        with open('./data/weather_level_adj.json', 'r') as f:  # Read the settings from file
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
    directory = os.path.dirname(path)
    mkdir_p(directory)
    try_nr = 1
    while try_nr <= 2:
        try:
            if not os.path.exists(path) or force:
                with open(path, 'wb') as fh:
                    req = urllib2.urlopen("http://api.wunderground.com/api/"+options['wapikey']+"/" + suffix)
                    while True:
                        chunk = req.read(20480)
                        if not chunk:
                            break
                        fh.write(chunk)

            try:
                with file(path, 'r') as fh:
                    data = json.load(fh)
            except ValueError:
                raise Exception('Failed to read ' + path + '.')

            if data is not None:
                if 'error' in data['response']:
                    raise Exception(str(data['response']['error']))
            else:
                raise Exception('JSON decoding failed.')

        except Exception as err:
            if try_nr < 2:
                print str(err), 'Retrying.'
                os.remove(path)
            else:
                raise
        try_nr += 1

    return data


def remove_data(prefixes):
    # Delete old files
    for prefix in prefixes:
        check_date = datetime.date.today()
        start_delta = datetime.timedelta(days=14)
        day_delta = datetime.timedelta(days=1)
        check_date -= start_delta
        for index in range(60):
            datestring = check_date.strftime('%Y%m%d')
            path = os.path.join('.', 'data', 'weather_level_history', prefix + datestring)
            if os.path.isdir(path):
                shutil.rmtree(path)
            check_date -= day_delta


################################################################################
# Info queries:                                                                #
################################################################################

def history_info():
    options = options_data()
    if int(options['days_history']) == 0:
        return {}

    lid = get_wunderground_lid()
    if lid == "":
        raise Exception('No Location ID found!')

    check_date = datetime.date.today()
    day_delta = datetime.timedelta(days=1)

    info = {}
    for index in range(-1, -1 - int(options['days_history']), -1):
        check_date -= day_delta
        datestring = check_date.strftime('%Y%m%d')
        request = "history_"+datestring+"/q/"+lid+".json"

        data = get_data(request)

        if data and len(data['history']['dailysummary']) > 0:
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
        raise Exception('No Location ID found!')

    datestring = datetime.date.today().strftime('%Y%m%d')

    request = "conditions/q/"+lid+".json"
    name = "conditions_"+datestring+"/q/"+lid+".json"
    data = get_data(request, name, True)

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

    lid = get_wunderground_lid()
    if lid == "":
        raise Exception('No Location ID found!')

    datestring = datetime.date.today().strftime('%Y%m%d')

    request = "forecast10day/q/"+lid+".json"
    name = "forecast10day_"+datestring+"/q/"+lid+".json"
    data = get_data(request, name)

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