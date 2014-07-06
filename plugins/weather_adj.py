#!/usr/bin/env python

import web, json, time
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs

urls.extend(['/wa', 'plugins.weather_adj.settings', '/uwa', 'plugins.weather_adj.update']) # Add a new url to open the data entry page.

gv.plugin_menu.append(['Weather Adjust Settings', '/wa']) # Add this plugin to the home page plugins menu

class settings:
    """Load an html page for entering weather-based irrigation adjustments"""
    def __init__(self):
        self.render = web.template.render('templates/')

    def GET(self):
        try:
            f = open('./data/weather_adj.json', 'r') # Read the monthly percentages from file
            data = json.load(f)
            f.close()
        except Exception, e:
            data = {'auto_delay': 'off', 'delay_duration': 24}
        return self.render.weather_adj(data)

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
