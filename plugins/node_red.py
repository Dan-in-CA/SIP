# !/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function

# standard library imports
import json  # for working with data file
import threading
from threading import Thread
from time import sleep

# local module imports
from blinker import signal
import gpio_pins
import gv  # Get access to SIP's settings
from helpers import * # provides functions for button taps
# import helpers
import requests
from sip import template_render  #  Needed for working with web.py templates
from urls import urls  # Get access to SIP's URLs
import web  # web.py framework
import webpages
from webpages import ProtectedPage  # Needed for security
# from webpages import refresh_page
from webpages import showInFooter # Enable plugin to display readings in UI footer
from webpages import showOnTimeline # Enable plugin to display station data on timeline


# Add new URLs to access classes in this plugin.
# fmt: off
urls.extend([
    u"/node-red-sp", u"plugins.node_red.settings",
    u"/node-red-save", u"plugins.node_red.save_settings",
    u"/jsin", u"plugins.node_red.parse_json"

    ])
# fmt: on

# Add this plugin to the PLUGINS menu ["Menu Name", "URL"], (Optional)
gv.plugin_menu.append([_(u"Node-red Settings"), u"/node-red-sp"])

#### Global variables ####
base_url = "http://localhost/"
prior_srvals = [0] * len(gv.srvals)
prior_rd = 0
nr_settings = {}


#### Functions ####

def bit_read(byts, read_lst):
    """ Read bits in bytes.
        Return dict of bit values per input read list
    """
    res_lst = []
    print("byts: ", byts)
    print("read_lst:", read_lst)
    for i in read_lst:
        idx = int(i) - 1
        bid = idx // 8
        bit = (byts[bid] >> (idx % 8)) & 1
        res_lst.append(bit)
    res_dict = dict(zip(read_lst, res_lst))
    return res_dict

def bit_write(bytes, bit_dict):
    """Turn bits on or off.
    """
    for key, value in bit_dict.items():
        idx = int(key) - 1
        byte_idx = idx // 8
        if value: # turn bits on
            gv.sd[bytes][byte_idx] |= 1 << (idx % 8)
        else:  # Turn bita off
            gv.sd[bytes][byte_idx] &= ~(1 << (idx % 8))

def load_settings():
    global nr_settings
    try:
        with open(
            "./data/node_red.json", "r"
        ) as f:  # Read nr_settings from json file if it exists
            nr_settings = json.load(f)
            # print("settings type:", type(nr_settings))  # - test                
    except IOError:  # If file does not exist save default values
        nr_settings = {"station-on-off": "on",
                    "chng-gv": "on",
                    "chng-sd": "on",
                    "chng-ro": "on",                    
                    "nr-url": "http://localhost:1880/node_red",
                    "chng-stn": "on",
                    "blinker-signals": "on"
                } 
        jsave(nr_settings, "node_red")
    # print("node-red settings: ", nr_settings)  # - test
    return
    
load_settings()    

def to_node_red(note):
    url = nr_settings["nr-url"]
    # print("104 to node-red: ", note)  # - test)
    resp = requests.get(url, params = note)
    # print("response: ", resp)  # - test



#
# def set_rain_delay(hrs):
#     gv.sd["rd"] = hrs
#     gv.sd["rdst"] = int(
#         gv.now + hrs * 3600
#     )
#     stop_onrain()
#     report_rain_delay_change()
            
def set_rain_sensed(i):
    if i:
        gv.sd["rst"] = 0
    else:
        gv.sd["rst"] = 1
          
    
def run_once(list, pre):
    """ 
    Start a run once program from node-red
    Optionally disable preemption of running program.
    """   
    if not gv.sd["en"]:  # check if SIP is enabled
        return       
    if pre:
        stop_stations()  # preempt any running program.
    dur_sum = 0
    stations = [0] * gv.sd["nbrd"]
    for s in list:
        ident = s[0]
        try:
            if isinstance(ident, int):
                sid = ident -1
            elif ident.isnumeric():  # quoted number
                sid = int(ident) -1
            else:
                 sid = gv.snames.index(ident)
        except Exception as e:
            print("Error: ", e)  # name not found
            return e
        dur = s[1]
        gv.rs[sid][0] = gv.now + dur_sum
        dur_sum += dur
        gv.rs[sid][1] = gv.now + dur_sum
        gv.rs[sid][2] = dur
        gv.rs[sid][3] = 100
        gv.ps[sid][0] = 100
        gv.ps[sid][1] = dur
        stations[sid // 8] += 2 ** (sid % 8)
    if not gv.sd["bsy"]:
        schedule_stations(stations)
        
def station_on_off(data):
    if (not gv.sd["mm"]  # SIP is not in manual mode
        and not "req mm" in data 
        or ("req mm" in data                
            and data["req mm"] == 1
            and not gv.sd["mm"])
        ):
        return "Error: manual mode required"
    try:
        station = data["sn"]
    except KeyError:
        station = data["station"]               
    val = data["set"]
    new_srvals = gv.srvals
    masid = gv.sd["mas"] - 1
    for sn in range(len(station)): # number of stations in data
        sid = station[sn] - 1 # station index
        bid = sid // 8
        if val: # set == 1 in Node-red - applies to all stations in data                   
            new_srvals[sid] = 1 # station[s] == station number in UI 
            gv.srvals[sid] = 1                 
            gv.sbits[bid] |= 1 << sid % 8  # Set sbits for this station                   
            gv.ps[sid][0] = 100
            gv.rs[sid] = [gv.now, float("inf"), 0, 100] 
                             
        else:
            gv.sbits[bid] &= ~(1 << sid)
            gv.ps[sid][0] = 0
            gv.lrun = [sid,
                       gv.rs[sid][3],
                       gv.now - gv.rs[sid][0],
                       gv.now
                       ]
            log_run()
            gv.rs[sid] = [0,0,0,0]
    gpio_pins.set_output()
    
def run_now(ident):
    print("198 ideint: ", ident)  # - test
    try:
        if isinstance(ident, int):
            pid = ident -1
        elif ident.isnumeric():  # quoted number
            pid = int(ident) -1
        else:
             pid = gv.pnames.index(str(ident))
    except Exception as e:
        print("Error: ", e)  # name not found
        return e
    run_program(pid)  

def send_zone_change(name, **kw):
    """ Send notification to node-red 
        when core program signals a change in station state.
    """
    global prior_srvals
    if len(gv.srvals) > len(prior_srvals):
        prior_srvals += [0] * (len(gv.srvals) - len(prior_srvals))
    if not "station-on-off" in nr_settings:
        return
    if gv.srvals != prior_srvals:   # check for a change
        for i in range(len(gv.srvals)):
            if (gv.srvals[i] != prior_srvals[i]
                and True # Send station on/off: option ####
                ):  #  this station has changed
                if not gv.srvals[i]:  # station is off
                    if (gv.sd["mas"]
                        and gv.sd["mas"] == i + 1
                        ):
                        name = "master"
                    else:
                        name =  gv.snames[i]   
                    note = {"station": i + 1, "name": name,  "state": 0}
                    to_node_red(note)
                else:
                    if (gv.sd["mas"]
                        and gv.sd["mas"] == i + 1
                        ):
                        name = "master"
                    else:
                        name =  gv.snames[i]                    
                    note = {"station": i + 1, "name": name, "state": 1}
                    to_node_red(note)               
        prior_srvals = gv.srvals[:]
zones = signal("zone_change")
zones.connect(send_zone_change)

def send_rain_delay_change(name, **kw):
    global prior_rd
    if gv.sd["rd"] != prior_rd: # rain delay has changed
        if gv.sd["rd"]: #  just switched on
            state = 1
        else:           #  Just switched off
            state = 0
        note = {"rd_state": state}
        to_node_red(note)
        prior_rd = gv.sd["rd"]  

rd_change = signal("value_change")
rd_change.connect(send_rain_delay_change)

#### blinker signals ##########
"alarm"
"new_day"
"loggedin"
"option_change"
"program_change"
"program_deleted"
"program_toggled"
"rain_changed"
# "rain_delay_change" # included with "value_change"
"rebooted"
"restarting"
"running_program_change"
"station_completed"
"station_names"
"stations_scheduled"
"value_change"
"zone_change"
###############################




def send_blinker_signal():
    pass

#############################
### Data display examples ###

## use 1 to turn on for testing, 0 to turn off ##
test_footer = 0
test_timeline = 0
 
if test_footer:
    example1 = showInFooter()  #  instantiate class to enable data in footer
    example1.label = u"Proto example data"
    example1.val = 0
    example1.unit = u" sec"
     
    example2 = showInFooter() #  instantiate class to enable data in footer
    example2.label = u"Second example data"
    example2.val = 0
    example2.unit = u" seconds"

if test_timeline:
    flow1 = showOnTimeline()  #  instantiate class to enable data on timeline
    flow1.unit = u"lph"
    flow1.val = 1
     
    flow2 = showOnTimeline()  #  instantiate class to enable data on timeline
    flow2.unit = u"Used(L)"
    flow2.val = 1

def data_test():
        while True: #  Display simulated plugin data
            
            #  Update footer data
            if test_footer:
                example1.val += 2 #  update plugin data 1
                example2.val += 4 #  update plugin data 2
            
            #  Update timeline data
            if test_timeline:
                flow1.val += 1
                flow2.val += 2
            
            sleep(1)        

# Run data_test() in baskground thread
ft = Thread(target = data_test)
ft.daemon = True
ft.start()

### End data display examples ###
#################################

class settings(ProtectedPage):
    """
    Load an html page for entering plugin settings.
    """
    def GET(self):
        try:
            with open(
                u"./data/node_red.json", u"r"
            ) as f:  # Read settings from json file if it exists
                nr_settings = json.load(f)
        except IOError:  # If file does not exist return empty value
            nr_settings = {}  # Default settings. can be list, dictionary, etc.
        # print("settings type:", type(nr_settings))  # - test
        return template_render.node_red(nr_settings)  # open settings page


class save_settings(ProtectedPage):
    """
    Save user input to json file.
    Will create or update file when SUBMIT button is clicked
    CheckBoxes only appear in qdict if they are checked.
    """
    # global nr_settings
    def GET(self):
        global nr_settings
        qdict = (
            web.input()
        )  # Dictionary of values returned as query string from settings page.
        with open(u"./data/node_red.json", u"w") as f:
            json.dump(qdict, f, indent=4)  # save to file
            nr_settings = dict(qdict)           
        raise web.seeother(u"/")  # Return user to home page.
    
# class refresh_page(object):
#     """Return event to trigger page reload."""
#     # flag = None
#     # def __init__(self):
#     #     self.run()
#
#     def GET(self):
#         print("AJAX request recieved")  # - test       
#         event_obj = threading.Event()
#         print("e-object: ", event_obj)  # - test
#         self.flag = event_obj.wait()
#
#     # def run(self): ### maybe make this external
#         thread1 = threading.Thread(target=self.GET)
#         thread1.start()

#     @staticmethod
#     def send(self):
#         # self.flag.set
#         self.event_obj.set()


class parse_json(object):
    """
    parse JSON request message from node-red
    """    

# gv lists:
# ["lrun", "pd", "ps", "rovals", "rs", "sbits", "snames", "srvals", "output_srvals", "plugin_menu"]  
    
    def GET(self):
        """ return value from get request. """
        qdict = (
            dict(web.input())  # Dictionary of JSON values
        )
        # print("qdict: ", qdict)  # - test
        if "gv" in qdict:
            attr = str(qdict["gv"])
            try:
                # if (attr == "rs"
                #     and "station" in qdict
                #     ):
                #     stn_rs = gv.rs[int(qdict["station"]) - 1]
                #     msg = {"start": stn_rs[0], "end": stn_rs[1], "duration": stn_rs[2]}
                #     return json.dumps(msg)
                
                if (attr in ["ps",
                             "rovals",
                             "rs",
                             "snames",
                             "srvals",
                             "output_srvals",
                             "lrun",
                             "pd",
                             "pnames",
                             "sbits",
                             "plugin_menu"
                             ]  # these return lists
                    ):
                             
                    gv_lst = getattr(gv, attr)
                    sel_lst = []                             
                             
                if ("sn"  in qdict or "station" in qdict):
                    # ):
                    sn_lst = []
                    if "sn" in qdict:
                        sn_lst = json.loads(qdict["sn"])
                    elif "station" in qdict:
                        sn_lst = json.loads(qdict["station"])                                            
                    for i in sn_lst:
                        sel_lst.append(gv_lst[i - 1])
                    res_dict = dict(zip(sn_lst, sel_lst))
                    return res_dict
                
                elif "item" in qdict:
                    item_lst = json.loads(qdict["item"])
                    try:
                        for i in item_lst:
                            sel_lst.append(gv_lst[i - 1])
                    except TypeError:
                        return "Error, item value must be an array in double quotes"
                    except IndexError:
                        pass
                    res_dict = dict(zip(item_lst, sel_lst))
                    return res_dict                    
                    
                elif "index" in qdict: 
                    index_lst = json.loads(qdict["index"])                   
                    try:
                        for i in index_lst:
                            sel_lst.append(gv_lst[i])
                    except TypeError:
                        return "Error, item value must be an array in double quotes"
                    except IndexError:
                        # return "Error, max index is " + str(len(index_lst) - 2)
                        pass                        
                    res_dict = dict(zip(index_lst, sel_lst))
                    return res_dict                     
                
                elif "bit" in qdict:
                    bit_dict = bit_read(getattr(gv, attr), json.loads(qdict["bit"]))
                    return json.dumps(bit_dict)                
                
                else:                  
                    return json.dumps(getattr(gv, attr))
            except Exception as e:
                return e
            
        elif "sd" in qdict:
            try:               
                if "bit" in qdict:
                    bit_dict = bit_read(gv.sd[qdict["sd"]], json.loads(qdict["bit"]))
                    return json.dumps(bit_dict)
                else:
                    return json.dumps(gv.sd[qdict["sd"]])
            except Exception as e:
                return e            
        else:
            return "Unknown request"
        
    def POST(self):
        """ Update SIP with value sent from node-red. """
        data = web.data()
        # print("447 data: ", data)  # - test
        data = json.loads(data.decode('utf-8'))
           
        not_writable = ["cputemp",
                        "day_ord",
                        "lang", 
                        "now",
                        "nowt",
                        "npw",
                        "output_srvals",
                        "output_srvals_lock",
                        "passphrase",
                        "plugin_data",
                        "plugin_menu",
                        'pw',
                        "upas",
                        "ver_str",
                        "ver_date"
                        ]
        
        danger_list = ["nst",
                       "nopts",
                       "nprogs",                                   
                      ]
        
        prog_keys = ['cycle_min',
                     'day_mask',
                     'duration_sec',
                     'enabled',
                     'interval_base_day',
                     'name', 'start_min',
                     'station_mask',
                     'stop_min',
                     'type'
                    ]
        
        #######################
        #### Set gv values ####        
        if ("gv" in data
            and "chng-gv" in nr_settings
            ):
            attr = data["gv"]
            if attr in not_writable:
                return "gv." + attr + " is not writable"           
            
            try:             
                if (attr in ["ps",
                             "rovals",
                             "rs",
                             "snames",
                             "srvals",
                             "output_srvals",
                             "lrun",
                             "pd",
                             "pnames",
                             "sbits",
                             "plugin_menu"
                             ]  # these return lists
                    ):
                    gv_lst = getattr(gv, attr)
                                                          
                if "sn"  in data or "station" in data:
                    if "sn" in data:
                        sn_dict = data["sn"]
                    elif "station" in data:
                        sn_dict = data["station"]
                    sn_lst = list(sn_dict.keys())
                    for i in sn_lst:
                        idx = int(i)- 1                
                        gv_lst[idx] = sn_dict[i]
                    # print(gv_lst)  # - test
                    return "gv." + attr + " has ben updated"
                
                elif "item" in data:
                    try:
                        item_dict = data["item"]
                        item_lst = list(item_dict.keys())
                        for i in item_lst:
                            idx = int(i)- 1
                            gv_lst[idx] = item_dict[i]
                        return "gv." + attr + " has ben updated"
                    except Exception as e:
                        return e
                                  
                elif "index" in data:
                    try:
                        index_dict = data["item"]
                        index_lst = list(index_dict.keys())
                        for i in index_lst:
                            idx = int(i)- 1
                            gv_lst[idx] = index_dict[i]
                        return "gv." + attr + " has ben updated" 
                    except Exception as e:
                        return e                    

                elif hasattr(gv, data["gv"]):                   
                    setattr(gv, data["gv"], data["val"])
                    return "gv." + data["gv"] + " updated to " + str(data["val"])
                else:
                    return "Unknown request"
            except Exception as e:
                return e                 
       
        #######################
        #### set sd values ####
        elif ("sd" in data
              and "chng-sd" in nr_settings
              ):
            # print("data: ", data)  # - test          
            if "val"in data:
                val = int(data["val"])
            else:
                val = None                
            try:     
                # Change values
                if data["sd"] == "rd":  # rain delay
                    if ((not val == None
                        # and not gv.sd["rd"]  # Rain delay already set
                        and not val == -1)
                        or val == 0
                        ):
                        requests.get(url = base_url + "cv", params = {"rd":val})
                        data = ""
                    elif val == -1:
                        note = {"rd_state": "0"}
                        to_node_red(note)                        
                    
                elif data["sd"] == "mm":  # manual mode
                    if val == 0:
                        clear_mm()
                        gv.sd["mm"] = 0
                    elif val == 1:
                        gv.sd["mm"] = 1
                    else:
                        return "invalid request"    
                                               
                elif (data["sd"] == "rsn"
                   and val == 1
                   ):
                    stop_stations()                         
                # Change options
                elif data["sd"] == "nbrd":
                    requests.get(url = base_url + "co", params = {"onbrd":val})
                    
                elif data["sd"] == "htp":
                    requests.get(url = base_url + "co", params = {"ohtp":val})                    
                       
                elif data["sd"] == "idd":
                    if val == 1:
                        requests.get(url = base_url + "co", params = {"oidd":val})
                    elif val == 0:
                        requests.get(url = base_url + "co", params = {"none":val})
                    else:
                        return "invalid request"                        
                        
                elif ((data["sd"] == "mton"
                      or data["sd"] == "mtoff")
                      and (val < -60 
                           or val > 60)            
                      ):
                    return "Error val must be -60 to 60"
                
                elif data["sd"] == "rbt":
                    requests.get(url = base_url + "co", params = {"rbt":val})
                    
                elif data["sd"] == "rstrt":
                    requests.get(url = base_url + "co", params = {"rstrt":val})                                   
                                    
                elif ( gv.sd["urs"]
                      and data["sd"] == "rs"
                      ):
                    set_rain_sensed(val) 
                    
                elif  "bit" in data:
                    # print("bits in data: ", data["bit"])  # - test
                    bit_write(data["sd"], data["bit"])
                                     
                else:  # handle all other vars
                    if (not data["sd"] in danger_list
                        or ("force" in data
                            and data["force"] == 1 )
                        ): 
                        gv.sd[data["sd"]] = val
                    else:
                        return "Not recommended"
                                             
                if ("save" in data
                    and data["save"] == 1
                    ):
                    jsave(gv.sd, "sd")
                return "gv.sd[" + data["sd"] + "] updated to " + str(val)                    
            except Exception as e:
                return e 
        
        # simulate button click/tap
        elif "tap" in data:
            
           ### need to get val from data and call named function
           
            print("tap received")
            # URL = ''
            # requests.post(base_url + "co", params = data )
            
           # gv.cputemp = get_cpu_temp()
           # template_render.home()   # - test
           # print(web.ctx)
           # raise web.seeother("localhost/")
           
           #### page refresh test
           # print("flag info: ", refresh_page.flag)
           # refresh_page.send()
       
            # clear_mm()
            # gv.sd["mm"] = 0
            
        # Station on off
        elif (("sn" in data or "station" in data)
              and "chng-stn" in nr_settings
              ):
            station_on_off(data)
            
            # if (not gv.sd["mm"]  # SIP is not in manual mode
            #     and not "req mm" in data 
            #     or ("req mm" in data                
            #         and data["req mm"] == 1
            #         and not gv.sd["mm"])
            #     ):
            #     return "Error: manual mode required"
            # try:
            #     station = data["sn"]
            # except KeyError:
            #     station = data["station"]               
            # val = data["set"]
            # new_srvals = gv.srvals
            # masid = gv.sd["mas"] - 1
            # for sn in range(len(station)): # number of stations in data
            #     sid = station[sn] - 1 # station index
            #     bid = sid // 8
            #     if val: # set == 1 in Node-red - applies to all stations in data                   
            #         new_srvals[sid] = 1 # station[s] == station number in UI 
            #         gv.srvals[sid] = 1                 
            #         gv.sbits[bid] |= 1 << sid % 8  # Set sbits for this station                   
            #         gv.ps[sid][0] = 100
            #         gv.rs[sid] = [gv.now, float("inf"), 0, 100] 
            #
            #     else:
            #         gv.sbits[bid] &= ~(1 << sid)
            #         gv.ps[sid][0] = 0
            #         gv.lrun = [sid,
            #                    gv.rs[sid][3],
            #                    gv.now - gv.rs[sid][0],
            #                    gv.now
            #                    ]
            #         log_run()
            #         gv.rs[sid] = [0,0,0,0]
            # gpio_pins.set_output()
                   
        # run once
        elif (("ro" in data or "run once" in data)
              and "chng-ro" in nr_settings
              ):
            print("709 data: ", data)
            pre = 1
            if ("preempt" in data
                and data["preempt"] == 0
               ):
                pre = 0
            try:
                run_once(data["ro"], pre)
            except KeyError:
                run_once(data["run once"], pre)
        
        elif ("run" in data):
              run_now(data["run"])
              
        # stop all stations
        elif ("stop-all" in data):
            stop_stations()
        
        else:
            # print("Unknown request: ", data)  # - test
            return "Unknown request"            


#  Run when plugin is loaded

# load_settings()

# empty_function()
# to_node_red()
