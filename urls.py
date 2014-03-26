#!/usr/bin/env python

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
    '/gp', 'graph_programs',
    '/vl', 'view_log',
    '/cl', 'clear_log',
    '/lo', 'log_options',
    '/rp', 'run_now',
    '/ttu', 'toggle_temp',
    '/rev', 'show_revision',
    ]