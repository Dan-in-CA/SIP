# !/usr/bin/env python
from random import randint
import thread

import web, json, time
import gv # Get access to ospy's settings
from urls import urls # Get access to ospy's URLs
from ospy import template_render
from webpages import ProtectedPage

urls.extend(['/ma', 'plugins.monthly_adj.monthly_percent', '/uma', 'plugins.monthly_adj.update_percents']) # Add a new url to open the data entry page.
gv.plugin_menu.append(['Monthly Adjust', '/ma']) # Add this plugin to the home page plugins menu

def set_wl(run_loop=False):
    """Adjust irrigation time by percent based on historical climate data."""
    if run_loop:
        time.sleep(randint(3, 10)) # Sleep some time to prevent printing before startup information

    last_month = 0
    while True:
        with open('./data/levels.json', 'r') as f: # Read the monthly percentages from file
            levels = json.load(f)
        month = time.localtime().tm_mon # Get current month.
        if month != last_month:
            last_month = month
            gv.sd['wl_monthly_adj'] = levels[month-1] # Set the water level% (levels list is zero based).
            print 'Monthly Adjust: Setting water level to {}%'.format(gv.sd['wl_monthly_adj'])

        if not run_loop:
            break
        time.sleep(3600)

class monthly_percent(ProtectedPage):
    """Load an html page for entering monthly irrigation time adjustments"""

    def GET(self):
        with open('./data/levels.json', 'r') as f: # Read the monthly percentages from file
            levels = json.load(f)
        return template_render.monthly(levels)


class update_percents(ProtectedPage):
    """Save user input to levels.json file"""
    def GET(self):
        qdict = web.input()
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        vals = []
        for m in months:
            vals.append(int(qdict[m]))
        with open('./data/levels.json', 'w') as f: # write the monthly percentages to file
            json.dump(vals, f)
        set_wl()
        raise web.seeother('/')

thread.start_new_thread(set_wl, (True,))