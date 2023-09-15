#!/usr/bin/env python
# -*- coding: utf-8 -*-

# standard library imports
import json

# local module imports
import gv

prog_keys = [
    "enabled",
    "day_mask",
    "interval_base_day",
    "start_min",
    "stop_min",
    "cycle_min",
    "duration_sec",  #  needs special treatment for individual durations
    "station_mask", #  needs special treatment for expansion boards
]

def convert():
    with open("./data/programs.json") as old:
        old_data = json.load(old)
    pd = []
    for i in range(len(old_data)): # for each old program (i)
        new_prog = {}  # to hold new_format
        for j in range(len(prog_keys)): # for each element in new format (j)
            new_prog[prog_keys[j]] = old_data[i][j]
        if gv.sd['idd']:
            new_prog["duration_sec"] = old_data[i].pop() # copy list from old data
        else:
            new_prog["duration_sec"] = [old_data[i][6]]
        new_prog["enabled"] = old_data[i][0]
        new_prog["station_mask"] = []    
        for b in range(7, (7 + gv.sd["nbrd"])):
            new_prog["station_mask"].append(old_data[i][b])
                            
        new_prog["name"] = "" # Not in old format
        
        #  decode program type from old format & clean up new format
        new_prog["type"] = "NA"
        if not new_prog["day_mask"] & 128:  #  if high bit not set
            new_prog["type"] = "alldays"
        elif (
            new_prog["day_mask"] & 128  #  if high bit is set
            and new_prog["interval_base_day"] < 2  # low bit is 0 or 1
        ):
            days = ["evendays", "odddays"]
            new_prog["type"] = days[new_prog["interval_base_day"]]
        elif new_prog["interval_base_day"] >= 2:
            new_prog["type"] = "interval"
            new_prog["day_mask"] &= ~128  #  clear high bit
        if ((new_prog["start_min"] + (sum(new_prog["duration_sec"]) // 60)) >= new_prog["stop_min"]):
            new_prog["cycle_min"] = 0
        if old_data[i][5]>= new_prog["stop_min"]:
           new_prog["stop_min"] =  new_prog["start_min"] + (sum(new_prog["duration_sec"]) // 60)
           new_prog["cycle_min"] = 0  
        pd.append(new_prog)
    return pd

if __name__ == "__main__":
    new_data = convert()
    with open("./data/programData.json", "w") as pf:
        json.dump(new_data, pf, indent=4, sort_keys=True)
