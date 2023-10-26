# !/usr/bin/env python
# -*- coding: utf-8 -*-

# standard library imports
import json  # for working with data file
from threading import Thread
from time import sleep

# local module imports
from blinker import signal
import gv  # Get access to SIP's settings
from sip import template_render  #  Needed for working with web.py templates
from urls import urls  # Get access to SIP's URLs
import web  # web.py framework
from webpages import ProtectedPage  # Needed for security
from webpages import showInFooter # Enable plugin to display readings in UI footer
from webpages import showOnTimeline # Enable plugin to display station data on timeline


# Add new URLs to access classes in this plugin.
# fmt: off
urls.extend([
    u"/proto-sp", u"plugins.proto.settings",
    u"/proto-save", u"plugins.proto.save_settings"

    ])
# fmt: on

# Add this plugin to the PLUGINS menu ["Menu Name", "URL"], (Optional)
gv.plugin_menu.append([_(u"Proto Plugin"), u"/proto-sp"])


def empty_function():  # Only a place holder
    """
    Functions defined here can be called by classes
    or run when the plugin is loaded. See comment at end.
    """
    pass

#############################
### Data display examples ###

## use 1 to turn on for testing, 0 to turn off ##
test_footer = 1
test_timeline = 1
 
if test_footer:
    example1 = showInFooter()  #  instantiate class to enable data in footer
    example1.label = u"Proto example data"
    example1.val = 0
    example1.unit = u" sec"
     
    example2 = showInFooter() #  instantiate class to enable data in footer
    example2.label = u"Second example data"
    example2.val = 0
    example2.unit = u" seconds"

if test_timeline:
    flow1 = showOnTimeline()  #  instantiate class to enable data on timeline
    flow1.unit = u"lph"
    flow1.val = 1
     
    flow2 = showOnTimeline()  #  instantiate class to enable data on timeline
    flow2.unit = u"Used(L)"
    flow2.val = 1

def data_test():
        while True: #  Display simulated plugin data
            
            #  Update footer data
            if test_footer:
                example1.val += 2 #  update plugin data 1
                example2.val += 4 #  update plugin data 2
            
            #  Update timeline data
            if test_timeline:
                flow1.val += 1
                flow2.val += 2
            
            sleep(1)        

# Run data_test() in baskground thread
ft = Thread(target = data_test)
ft.daemon = True
ft.start()

### End data display examples ###
#################################

### Station Completed ###
def notify_station_completed(station, **kw):
    print(u"Station {} run completed".format(station))


complete = signal(u"station_completed")
complete.connect(notify_station_completed)


class settings(ProtectedPage):
    """
    Load an html page for entering plugin settings.
    """

    def GET(self):
        try:
            with open(
                u"./data/proto.json", u"r"
            ) as f:  # Read settings from json file if it exists
                settings = json.load(f)
        except IOError:  # If file does not exist return empty value
            settings = {}  # Default settings. can be list, dictionary, etc.
        return template_render.proto(settings)  # open settings page


class save_settings(ProtectedPage):
    """
    Save user input to json file.
    Will create or update file when SUBMIT button is clicked
    CheckBoxes only appear in qdict if they are checked.
    """

    def GET(self):
        qdict = (
            web.input()
        )  # Dictionary of values returned as query string from settings page.
        #        print qdict  # for testing
        with open(u"./data/proto.json", u"w") as f:  # Edit: change name of json file
            json.dump(qdict, f)  # save to file
        raise web.seeother(u"/")  # Return user to home page.


#  Run when plugin is loaded
empty_function()
