#!/usr/bin/python
# encoding: utf-8

import gettext
import json
import locale
import os

__author__ = u"Dan"

try:
    with open(u"./data/sd.json", u"r") as sdf:
        sd_temp = json.load(sdf)
except:
    pass

try:
    sd_lang = sd_temp[u"lang"]
except:
    sd_lang = u"default"

languages = {
    u"en_US": u"English",
    u"af_AF": u"Afrikaans",
    u"ar_SA": u"Arabic",
    u"cs_CZ": u"Czech",
    u"fr_FR": u"French",
    u"de_DE": u"German",
    u"gr_GR": u"Greek",
    u"it_IT": u"Italian",
    u"pt_PT": u"Portuguese",
    u"sl_SL": u"Slovenian",
    u"es_ES": u"Spanish",
    u"ta_TA": u"Tamil",
}


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
localedir = curdir + u"/i18n"

gettext.install(u"sip_messages", localedir)

sys_lang = get_system_lang()

if sd_lang == u"default":
    if sys_lang in languages:
        ui_lang = sys_lang
    else:
        ui_lang = u"en_US"
else:
    ui_lang = sd_lang

try:
    gettext.translation(u"sip_messages", localedir, languages=[ui_lang]).install(True)
except IOError:
    pass
