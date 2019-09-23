#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

prog_keys = [u"enabled",
             u"day_mask",
             u"interval_base_day",
             u"start_min",
             u"stop_min",
             u"cycle_min",
             u"duration_sec", #  needs special treatment for individual durations
#              u"station_mask", #  needs special treatment for expansion boards
            ]

def convert():
    with open(u"./data/programs.json") as old:
        old_data = json.load(old)   
    pd = []
    for i in range(len(old_data)):
        new_prog = {} # to hold new_format
        for j in range(len(prog_keys)):
            new_prog[prog_keys[j]] = old_data[i][j]
        if type(old_data[-1]) == list:
            new_prog[u"duration_sec"] = old_data[i].pop()
        new_prog[u"station_mask"] = old_data[i][7:]
        new_prog[u"name"] = u"Unnamed"
        
        #  decode program type from old format & clean up new format
        new_prog[u"type"] = u"NA"
        if not new_prog[u"day_mask"] & 128: #  if high bit not set
            new_prog[u"type"] = u"alldays"
        elif (new_prog[u"day_mask"] & 128
              and new_prog[u"interval_base_day"] < 2 # low bit is 0 or 1
            ):       
            days = [u"evendays", u"odddays"]
            new_prog[u"type"] = days[new_prog[u"interval_base_day"]]
            new_prog[u"day_mask"] &= ~128 #  clear high bit
        elif new_prog[u"interval_base_day"] >= 2:
            new_prog[u"type"] = u"interval"
        
        pd.append(new_prog)
    return pd

if __name__ == u"__main__":
    new_data = convert()
    with open(u"./data/programData.json", u"w") as pf:
        json.dump(new_data, pf, indent=4, sort_keys=True)