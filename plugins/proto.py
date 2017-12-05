# !/usr/bin/env python
# -*- coding: utf-8 -*-

import web  # web.py framework
import gv  # Get access to SIP's settings
from urls import urls  # Get access to SIP's URLs
from sip import template_render  #  Needed for working with web.py templates
from webpages import ProtectedPage  # Needed for security
import json  # for working with data file

# Add new URLs to access classes in this plugin.
urls.extend([
    '/proto-sp', 'plugins.proto.settings',
    '/proto-save', 'plugins.proto.save_settings'

    ])

# Add this plugin to the PLUGINS menu ['Menu Name', 'URL'], (Optional)
gv.plugin_menu.append([_('Proto Plugin'), '/proto-sp'])

def empty_function():  # Only a place holder
    """
    Functions defined here can be called by classes
    or run when the plugin is loaded. See comment at end.
    """
    pass


class settings(ProtectedPage):
    """
    Load an html page for entering plugin settings.
    """

    def GET(self):
        try:
            with open('./data/proto.json', 'r') as f:  # Read settings from json file if it exists
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
        qdict = web.input()  # Dictionary of values returned as query string from settings page.
#        print qdict  # for testing
        with open('./data/proto.json', 'w') as f:  # Edit: change name of json file
             json.dump(qdict, f) # save to file
        raise web.seeother('/')  # Return user to home page.

#  Run when plugin is loaded
empty_function()
