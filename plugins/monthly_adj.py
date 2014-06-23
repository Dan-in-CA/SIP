#!/usr/bin/env python

import web, json, time
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs
try:
    from apscheduler.scheduler import Scheduler #This is a non-standard module. Needs to be installed in order for this feature to work.
except ImportError:
    print "The Python module apscheduler could not be found."
    pass

urls.extend(['/ma', 'plugins.monthly_adj.monthly_percent', '/uma', 'plugins.monthly_adj.update_percents']) # Add a new url to open the data entry page.

gv.plugin_menu.append(['Monthly Adjust', '/ma']) # Add this plugin to the home page plugins menu

try:
    sched = Scheduler()
    sched.start() # Start the scheduler
except NameError:
    pass

def set_wl():
    """Adjust irrigation time by percent based on historical climate data.""" 
    f = open('./data/levels.json', 'r') # Read the monthly percentages from file
    levels = json.load(f)
    f.close()
    mon = time.localtime().tm_mon # Get current month.
    gv.sd['wl'] = levels[mon-1] # Set the water level% (levels list is zero based).
    print 'Setting water level to {}%'.format(gv.sd['wl'])
    return

class monthly_percent:
    """Load an html page for entering monthly irrigation time adjustments"""
    def __init__(self):
        self.render = web.template.render('templates/')

    def GET(self):
        f = open('./data/levels.json', 'r') # Read the monthly percentages from file
        levels = json.load(f)
        f.close()
        return self.render.monthly(levels)

class update_percents:
    """Save user input to levels.json file"""
    def GET(self):
        qdict = web.input()
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        vals = []
        for m in months:
            vals.append(int(qdict[m]))
        f = open('./data/levels.json', 'w') # write the monthly percentages to file
        json.dump(vals, f)
        f.close()
        raise web.seeother('/')

set_wl() # Runs the function once at load.
try:
    sched.add_cron_job(set_wl, day=1) # Run the plugin's function the first day of each month.
except NameError:
    pass