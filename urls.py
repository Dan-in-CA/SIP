# !/usr/bin/env python
# -*- coding: utf-8 -*-

#### urls is used by web.py. When a GET request is received, the corresponding class is executed.
urls = [
    # fmt: off
    "/",   "webpages.home",
    "/cv", "webpages.change_values",
    "/vo", "webpages.view_options",
    "/co", "webpages.change_options",
    "/sn", "webpages.get_set_station",
    "/vr", "webpages.view_runonce",
    "/cr", "webpages.change_runonce",
    "/vp", "webpages.view_programs",
    "/mp", "webpages.modify_program",
    "/cp", "webpages.change_program",
    "/dp", "webpages.delete_program",
    "/ep", "webpages.enable_program",
    "/vl", "webpages.view_log",
    "/cl", "webpages.clear_log",
    "/lo", "webpages.log_options",
    "/rp", "webpages.run_now",
    "/ttu", "webpages.toggle_temp",
    "/rev", "webpages.show_revision",
    "/sip_log",  "webpages.water_log",
    "/api/status", "webpages.api_status",
    "/api/log", "webpages.api_log",
    "/api/plugins", "webpages.plugin_data",
    "/login",  "webpages.login",
    "/logout", "webpages.logout",
    "/restart", "webpages.sw_restart",
    "/rss", "webpages.rain_sensor_state",
    "/refresh", "webpages.page_refresh"
    # fmt: on
]
