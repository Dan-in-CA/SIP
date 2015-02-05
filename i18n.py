#!/usr/bin/python
# encoding: utf-8

import os
import locale
import gettext
import json

__author__ = 'Dan'

try:
    with open('./data/sd.json', 'r') as sdf:
        sd_temp = json.load(sdf)
except:
    pass
       
try:
    sd_lang = sd_temp['lang']
except:
    sd_lang = 'default'

languages = ({
    "en_US": "English",
    "cs_CZ": "Czech",
    "es_ES": "Spanish",
    "fr_FR": "French",
})


def get_system_lang():
    """Return default system locale language"""
    lc, encoding = locale.getdefaultlocale()
    if lc:
        return lc
    else:
        return None

# File location directory.
curdir = os.path.abspath(os.path.dirname(__file__))

# i18n directory.
localedir = curdir + '/i18n'

gettext.install('ospi_messages', localedir, unicode=True)

sys_lang = get_system_lang()

if sd_lang == 'default':
    if sys_lang in languages:
        ui_lang = sys_lang
    else:
        ui_lang = 'en_US'
else:
    ui_lang = sd_lang

try:
    gettext.translation('ospi_messages', localedir, languages=[ui_lang]).install(True)
except IOError:
    pass
