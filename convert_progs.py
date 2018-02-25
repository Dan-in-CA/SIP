#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

prog_keys = ['enabled',
             'day_mask',
             'interval_base_day',
             'start_min',
             'stop_min',
             'cycle_min',
             'duration_sec', #  needs special treatment for individual durations
#              'station_mask', #  needs special treatment for expansion boards
            ]

def convert():
    with open('./data/programs.json') as old:
        old_data = json.load(old)   
    pd = []
    for i in range(len(old_data)):
        new_prog = {} # to hold new_format
        for j in range(len(prog_keys)):
            new_prog[prog_keys[j]] = old_data[i][j]
        if type(old_data[-1]) == list:
            new_prog['duration_sec'] = old_data[i].pop()
        new_prog['station_mask'] = old_data[i][7:]
        new_prog['name'] = 'Unnamed'
        
        #  decode program type from old format & clean up new format
        new_prog['type'] = "NA"
        if not new_prog['day_mask'] & 128: #  if high bit not set
            new_prog['type'] = 'alldays'
        elif (new_prog['day_mask'] & 128
              and new_prog['interval_base_day'] < 2 # low bit is 0 or 1
            ):       
            days = ['evendays', 'odddays']
            new_prog['type'] = days[new_prog['interval_base_day']]
            new_prog['day_mask'] &= ~128 #  clear high bit
        elif new_prog['interval_base_day'] >= 2:
            new_prog['type'] = 'interval'
        
        pd.append(new_prog)
    return pd

if __name__ == '__main__':
    new_data = convert()
    with open('./data/programData.json', 'w') as pf:
        json.dump(new_data, pf, indent=4, sort_keys=True)