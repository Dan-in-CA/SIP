# !/usr/bin/env python
# -*- coding: utf-8 -*-

#### urls is used by web.py. When a GET request is received, the corresponding class is executed.
urls = [
    # fmt: off
    u"/",   u"webpages.home",
    u"/cv", u"webpages.change_values",
    u"/vo", u"webpages.view_options",
    u"/co", u"webpages.change_options",
    u"/vs", u"webpages.view_stations",
    u"/cs", u"webpages.change_stations",
    u"/sn", u"webpages.get_set_station",
    u"/vr", u"webpages.view_runonce",
    u"/cr", u"webpages.change_runonce",
    u"/vp", u"webpages.view_programs",
    u"/mp", u"webpages.modify_program",
    u"/cp", u"webpages.change_program",
    u"/dp", u"webpages.delete_program",
    u"/ep", u"webpages.enable_program",
    u"/vl", u"webpages.view_log",
    u"/cl", u"webpages.clear_log",
    u"/lo", u"webpages.log_options",
    u"/rp", u"webpages.run_now",
    u"/ttu", u"webpages.toggle_temp",
    u"/rev", u"webpages.show_revision",
    u"/wl",  u"webpages.water_log",
    u"/api/status", u"webpages.api_status",
    u"/api/log", u"webpages.api_log",
    u"/login",  u"webpages.login",
    u"/logout", u"webpages.logout",
    u"/restart", u"webpages.sw_restart",
    u"/rss", u"webpages.rain_sensor_state"
    # fmt: on
]
