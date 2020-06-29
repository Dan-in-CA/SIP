#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import json
import gv


prog_keys = [
    u"enabled",
    u"day_mask",
    u"interval_base_day",
    u"start_min",
    u"stop_min",
    u"cycle_min",
    u"duration_sec",  #  needs special treatment for individual durations
    u"station_mask", #  needs special treatment for expansion boards
]


def convert():
    with open(u"./data/programs.json") as old:
        old_data = json.load(old)
    pd = []
    for i in range(len(old_data)): # for each old program (i)
        new_prog = {}  # to hold new_format
        for j in range(len(prog_keys)): # for each element in new format (j)
            new_prog[prog_keys[j]] = old_data[i][j]
        if gv.sd[u'idd']:
            new_prog[u"duration_sec"] = old_data[i].pop() # copy list from old data
        else:
            new_prog[u"duration_sec"] = [old_data[i][6]]
        new_prog[u"enabled"] = old_data[i][0]    
        if type(new_prog[u"station_mask"]) == int:
                new_prog[u"station_mask"] =[old_data[i][7]]
        new_prog[u"name"] = u"Unnamed" # Not in old format
        
        #  decode program type from old format & clean up new format
        new_prog[u"type"] = u"NA"
        if not new_prog[u"day_mask"] & 128:  #  if high bit not set
            new_prog[u"type"] = u"alldays"
        elif (
            new_prog[u"day_mask"] & 128  #  if high bit is set
            and new_prog[u"interval_base_day"] < 2  # low bit is 0 or 1
        ):
            days = [u"evendays", u"odddays"]
            new_prog[u"type"] = days[new_prog[u"interval_base_day"]]
        elif new_prog[u"interval_base_day"] >= 2:
            new_prog[u"type"] = u"interval"
            new_prog[u"day_mask"] &= ~128  #  clear high bit
        if ((new_prog[u"start_min"] + (sum(new_prog[u"duration_sec"]) // 60)) >= new_prog[u"stop_min"]):
            new_prog[u"cycle_min"] = 0
        if old_data[i][5]>= new_prog[u"stop_min"]:
           new_prog[u"stop_min"] =  new_prog[u"start_min"] + (sum(new_prog[u"duration_sec"]) // 60)
           new_prog[u"cycle_min"] = 0  
        pd.append(new_prog)
    return pd


if __name__ == "__main__":
    new_data = convert()
    with open(u"./data/programData.json", u"w") as pf:
        json.dump(new_data, pf, indent=4, sort_keys=True)
