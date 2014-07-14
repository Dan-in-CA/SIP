#!/usr/bin/env python

 #### urls is used by web.py. When a GET request is received, the corresponding class is executed.
urls = [
    '/',  'home',
    '/cv', 'change_values',
    '/vo', 'view_options',
    '/co', 'change_options',
    '/vs', 'view_stations',
    '/cs', 'change_stations',
    '/sn(\d+?\Z)', 'get_station', # regular expression, accepts any station number
    '/sn(\d+?=\d(&t=\d+?\Z)?)', 'set_station', # regular expression, accepts any digits
    '/vr', 'view_runonce',
    '/cr', 'change_runonce',
    '/vp', 'view_programs',
    '/mp', 'modify_program',
    '/cp', 'change_program',
    '/dp', 'delete_program',
    '/vl', 'view_log',
    '/cl', 'clear_log',
    '/lo', 'log_options',
    '/rp', 'run_now',
    '/ttu', 'toggle_temp',
    '/rev', 'show_revision',
    '/wl', 'water_log',
    '/api/status', 'api_status',
    '/api/log', 'api_log',
    '/login', 'login',
    '/logout', 'logout'
]