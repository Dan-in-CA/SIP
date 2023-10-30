# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# Node-RED SIP extension plugin

# standard library imports
import json  # for working with data file
from time import sleep

# local module imports
from blinker import signal
import gpio_pins
import gv  # Get access to SIP's settings
from helpers import *  # provides utility functions
import requests
from sip import template_render
from urls import urls  # Get access to SIP's URLs
import web
import webpages
from webpages import ProtectedPage  # Needed for security
from webpages import report_option_change, report_value_change
from webpages import change_options


# Add new URLs to access classes in this plugin.
# fmt: off
urls.extend([
    "/node-red-sp", "plugins.node_red.settings",
    "/node-red-save", "plugins.node_red.save_settings",
    "/jsin", "plugins.node_red.handle_requests"
    ])
# fmt: on

# Add this plugin to the PLUGINS menu ["Menu Name", "URL"], (Optional)
gv.plugin_menu.append([_("Node-red Settings"), "/node-red-sp"])

##########################
#### Global variables ####

prior_srvals = [0] * len(gv.srvals)
# prior_progs = sorted(gv.pd)
nr_settings = {}

list_vars = [
    "ps",
    "rovals",
    "rs",
    "snames",
    "srvals",
    "output_srvals",
    "lrun",
    "pd",
    "pnames",
    "sbits",
    "plugin_menu",
    ]

not_writable = [
    "cputemp",
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
    "pw",
    "upas",
    "ver_str",
    "ver_date",
    ]

danger_list = [
    "nst",
    "nopts",
    "nprogs",
    ]

prog_keys = [
    "cycle_min",
    "day_mask",
    "duration_sec",
    "enabled",
    "interval_base_day",
    "name",
    "start_min",
    "station_mask",
    "stop_min",
    "type",
    ]

###################
#### Functions ####

def set_rd(val):
    if "chng-rd" in nr_settings:
        gv.sd["rd"] = val
        if val:
            gv.sd["rdst"] = round(gv.now + (val * 3600))
            stop_onrain()
        else:
            gv.sd["rdst"] = 0
        jsave(gv.sd, "sd")
    report_rain_delay_change()
    report_option_change()
    
def set_mm(val):
    if "chng-sd" in nr_settings:
        if val == 1:
            gv.sd["mm"] = 1
            jsave(gv.sd, "sd")
        elif val == 0:
            clear_mm()
            gv.sd["mm"] = 0
            jsave(gv.sd, "sd")
        else:
            return "invalid request, must be 0 or 1"    
        
def set_rsn(val):
    if "stop-stn" in nr_settings:
        if val == 1: stop_stations()
                
def set_wl(val):
    if "chng-wl" in nr_settings:
        gv.sd["wl"] = val
        jsave(gv.sd, "sd")
        report_option_change()
        
def set_nbrd(val):
    if "chng-sd" in nr_settings:
        if val != gv.sd["nbrd"]:  # number f boards has changed
            if val == 0: val = 1
            brd_chng = val - gv.sd["nbrd"]
            change_options.update_scount(brd_chng)
            gv.sd["nbrd"] = gv.sd["nbrd"] + brd_chng
            gv.sd["nst"] = gv.sd["nbrd"] * 8
            change_options.update_prog_lists("nbrd")
            jsave(gv.sd, "sd")
            # return "Station count changed"
            msg = {"payload":"Station count set to " + str(val * 8)}
            msg = json.dumps(msg)
            print("msg: ", msg)  # - test
            to_node_red(msg)
    
def set_htp(val):
    if "chng-sd" in nr_settings:
        gv.sd["htp"] = val
        jsave(gv.sd, "sd")
        return "htp changed"

def set_idd(val):
    if "chng-sd" in nr_settings:
        if val != gv.sd["idd"] and (val == 0 or val == 1):
            gv.sd["idd"] = val
            change_options.update_prog_lists("idd")
            jsave(gv.sd, "sd")
            return "Individual durations changed"
        else:
            return "Error val must be 0 or 1"
    
def set_mton(val):
    if "chng-sd" in nr_settings:
        if val < -60 or val > 60:
            return "Error val must be -60 to +60"
        else:
            gv.sd["mton"] = val
        jsave(gv.sd, "sd")
        
def set_mtoff(val):
    if "chng-sd" in nr_settings:
        if val < -60 or val > 60:
            return "Error val must be -60 to 60"
        else:
            gv.sd["mtoff"] = val
        jsave(gv.sd, "sd")

def set_rbt(val):
    if "chng-sd" in nr_settings:
        if val == 1: reboot()
        
def set_rstrt(val):
    if "chng-sd" in nr_settings:
        if val == 1: restart()
    
def set_rs(val):
    if "chng-sd" in nr_settings:
        if val == 0 or val == 1:
            gv.sd["rst"] = val
        else:
            return "invalid input, must be 0 or 1"
        jsave(gv.sd, "sd")
             

def skip():  # - test
    pass

def bit_read(byts, read_lst):
    """Read bits in bytes.
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
    """Turn bits on or off."""
    for key, value in bit_dict.items():
        idx = int(key) - 1
        byte_idx = idx // 8
        if value:  # turn bits on
            gv.sd[bytes][byte_idx] |= 1 << (idx % 8)
        else:  # Turn bita off
            gv.sd[bytes][byte_idx] &= ~(1 << (idx % 8))


def load_settings():
    global nr_settings  # , base_url
    try:
        with open(
            "./data/node_red.json", "r"
        ) as f:  # Read nr_settings from json file if it exists
            nr_settings = json.load(f)
    except IOError:  # If file does not exist save default values
        nr_settings = {
            "station-on-off": "on",
            "chng-gv": "off",
            "chng-sd": "off",
            "chng-rd": "on",
            "chng-ro": "on",
            "chng-rn": "on",
            "nr-url": "http://localhost:1880/node-red",
            "chng-stn": "on",
            "stop-stn": "on",
            "chng-prog": "on",
            "chng-wl": "on",
            "blinker-signals": "on",
        }
        jsave(nr_settings, "node_red")
    return


load_settings()


def to_node_red(msg):
    url = nr_settings["nr-url"]
    resp = requests.post(url, data = msg)


# def set_rain_sensed(i):
#     gv.sd["rst"] = 0 if i else gv.sd["rst"] = 1
    # if i:
    #     gv.sd["rst"] = 0
    # else:
    #     gv.sd["rst"] = 1


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
                sid = ident - 1
            elif ident.isnumeric():  # quoted number
                sid = int(ident) - 1
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


def program_on_off(data):
    """Disable or enable a SIP program.
    Optionally end the program if running.
    """
    if "prog" in data:
        program = data["prog"]
    elif "program" in data:
        program = data["program"]
    
    state = int(data["set"])
    for p in range(len(program)):
        prog_p = program[p]
        if isinstance(prog_p, int):
            pid = prog_p - 1
        elif isinstance(prog_p, str):
            if prog_p.isnumeric():  # quoted number
                pid = int(prog_p) - 1
            elif prog_p.lower() == "all":
                for i in range(len(gv.pd)):
                    gv.pd[i]["enabled"] = state
                return
            else:
                try:
                    pid = gv.pnames.index(prog_p)
                except ValueError as e:
                    return e
        if (
            "end" in data
            and int(data["end"]) == 1
            and state == 0
            # and gv.pon - 1 == pid  # The program to be disabled is running
        ):
            stop_stations()
        gv.pd[pid]["enabled"] = state
    jsave(gv.pd, "programData")


def station_on_off(data):
    """Enable or disable a station.
    Called by "station switch" node.
    """
    print("data 346: ", data)  # - test
    if "sn" in data:
        station = data["sn"]
    elif "station" in data:
        station = data["station"]
    state = data["set"]
    masid = gv.sd["mas"] - 1
    if "preempt" in data:
        pre = data["preempt"]
    else:
        pre = 0
    for sn in range(len(station)):  # number of stations in data
        stn = station[sn]
        if isinstance(stn, int):
            sid = stn - 1  # station index
        elif isinstance(stn, str):
            if stn.isnumeric():  # quoted number
                sid = int(stn) - 1
            else:
                try:
                    sid = gv.snames.index(stn)
                except ValueError as e:
                    return e
        bid = sid // 8

        if (
            not pre  # preempt is not set
            and gv.pon  # a program is running
            and (gv.pd[gv.pon - 1]["station_mask"][bid])
            & 1 << sid  # station is in the program
            and gv.rs[sid][2]  # station has a duration in running program
        ):
            continue  # Skip if station is controlled by a running program

        if state:  # set == 1 in Node-red - applies to all stations in data
            gv.rs[sid] = [gv.now, float("inf"), 0, 100]
            gv.srvals[sid] = 1
            gv.sbits[bid] |= 1 << (sid % 8)  # Set sbits for this station
            gv.ps[sid][0] = 100
            gv.ps[sid][1] = float("inf")
        else:
            gv.lrun = [sid, gv.rs[sid][3], gv.now - gv.rs[sid][0], gv.now]
            log_run()
            gv.rs[sid] = [0, 0, 0, 0]
            gv.srvals[sid] = 0
            gv.sbits[bid] &= ~(1 << (sid % 8))
            gv.ps[sid] = [0, 0]
    gpio_pins.set_output()


def run_now(ident):
    """Start an existing program.
    ident can be a program name or number.
    """
    try:
        if isinstance(ident, int):
            pid = ident - 1
        elif ident.isnumeric():  # quoted number
            pid = int(ident) - 1
        else:
            pid = gv.pnames.index(str(ident))
    except Exception as e:
        print("Error: ", e)  # name not found
        return e
    run_program(pid)


### send blinker signals ###

def send_zone_change(name, **kw):
    """Send notification to node-red
    when core program signals a change in station state.
    """
    global prior_srvals
    if len(gv.srvals) > len(prior_srvals):
        prior_srvals += [0] * (len(gv.srvals) - len(prior_srvals))
    if not "station-on-off" in nr_settings:
        # to_node_red("Station status is disabled")  # - test
        return
    if gv.srvals != prior_srvals:  # check for a change
        for i in range(len(gv.srvals)):
            if (
                gv.srvals[i] != prior_srvals[i]
                and True  # Send station on/off: option ####
            ):  #  this station has changed
                if not gv.srvals[i]:  # station is off
                    if gv.sd["mas"] and gv.sd["mas"] == i + 1:
                        name = "master"
                    else:
                        name = gv.snames[i]
                    msg = {"station": i + 1, "name": name, "state": 0}
                    to_node_red(msg)
                else:
                    if gv.sd["mas"] and gv.sd["mas"] == i + 1:
                        name = "master"
                    else:
                        name = gv.snames[i]
                    msg = {"station": i + 1, "name": name, "state": 1}
                    # print("sending message to NR")  # - test
                    to_node_red(msg)
        prior_srvals = gv.srvals[:]


zones = signal("zone_change")
zones.connect(send_zone_change)

### rain delay ###
def send_rain_delay_change(name, **kw):  # see line 663
    """Send rain delay state change to node-red"""
    if gv.sd["rd"]:  #  just switched on
        state = 1
    else:  #  Just switched off
        state = 0
    msg = {"rd_state": state}
    to_node_red(msg)


rd_change = signal("rain_delay_change")
rd_change.connect(send_rain_delay_change)

### new day ###
def send_new_day(name, **kw):
    msg = {"newDay": gv.now}
    to_node_red(msg)

new_day = signal("new_day")
new_day.connect(send_new_day)

### logged in ###
def send_login(name, **kw):
    msg = {"logIn": "user logged in"}
    to_node_red(msg)

loggedin = signal("loggedin")
loggedin.connect(send_login)

### program change ##
# def send_program_change(name, **kw):
#     # print("Programs changed")  # - test
#     s_progs = sorted(gv.pd)
#     while i < len(prior_progs): # changes of program deleted, need to account for new programs.
#         if s_progs[i] != prior_progs[i]:
#             pass
    
# program_change = signal("program_change")
# program_change.connect(send_program_change)    


###############################
#### blinker signals ##########
"alarm"
"new_day" # working
"loggedin" # done
"option_change" 
"program_change"
"program_added"
"program_deleted"
"program_toggled"
"rain_changed" # need new state
"rain_delay_change"  # included with "value_change"
"rebooted"
"restarting"
"running_program_change"  # to do
"station_completed"
"station_names"
"stations_scheduled"
"value_change" # done - may need modification
"zone_change"  # working
###############################

#### dicts ####

set_sd = {
        "rd": set_rd,
        "mm": set_mm,
        "rsn": set_rsn,
        "wl": set_wl,
        "nbrd": set_nbrd,
        "htp": set_htp,
        "idd": set_idd,
        "mton": set_mton,
        "mtoff": set_mtoff,
        "rbt": set_rbt,
        "rstrt": set_rstrt,
        "rs": set_rs      
        }

#################

###########################
#### Class definitions ####

class settings(ProtectedPage):
    """
    Load an html page for entering plugin settings.
    """
    def GET(self):
        try:
            with open(
                "./data/node_red.json", "r"
            ) as f:  # Read settings from json file if it exists
                nr_settings = json.load(f)
        except IOError:  # If file does not exist return empty value
            nr_settings = {}  # Default settings. can be list, dictionary, etc.
        return template_render.node_red(nr_settings)  # open settings page


class save_settings(ProtectedPage):
    """
    Save user input to json file.
    Will create or update file when SUBMIT button is clicked
    CheckBoxes only appear in qdict if they are checked.
    """
    def GET(self):
        global nr_settings
        qdict = (
            web.input()
        )  # Dictionary of values returned as query string from settings page.
        with open("./data/node_red.json", "w") as f:
            json.dump(qdict, f, indent=4)  # save to file
            nr_settings = dict(qdict)
            # print("nr_settings: ", nr_settings)  # - test
        raise web.seeother("/")  # Return user to home page.


class handle_requests(object):
    """
    parse request messages from node-red
    """
    def GET(self):
        """return a value from get request."""
        qdict = dict(web.input())  # Dictionary of JSON values
        print("node-red request: ", qdict)  # - test
        if "gv" in qdict:
            attr = str(qdict["gv"])
            try:
                if attr in [
                    "ps",
                    "rovals",
                    "rs",
                    "snames",
                    "srvals",
                    "output_srvals",
                    "lrun",
                    "pd",
                    "pnames",
                    "sbits",
                    "plugin_menu",
                ]:  # these return lists
                    gv_lst = getattr(gv, attr)
                    sel_lst = []

                if "sn" in qdict or "station" in qdict:
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
        """Update SIP with value sent from node-red."""
        data = web.data()
        data = json.loads(data.decode("utf-8"))
        # not_writable = [
        #     "cputemp",
        #     "day_ord",
        #     "lang",
        #     "now",
        #     "nowt",
        #     "npw",
        #     "output_srvals",
        #     "output_srvals_lock",
        #     "passphrase",
        #     "plugin_data",
        #     "plugin_menu",
        #     "pw",
        #     "upas",
        #     "ver_str",
        #     "ver_date",
        # ]
        #
        # danger_list = [
        #     "nst",
        #     "nopts",
        #     "nprogs",
        # ]
        #
        # prog_keys = [
        #     "cycle_min",
        #     "day_mask",
        #     "duration_sec",
        #     "enabled",
        #     "interval_base_day",
        #     "name",
        #     "start_min",
        #     "station_mask",
        #     "stop_min",
        #     "type",
        # ]

        #######################
        #### Set gv values ####
        if "gv" in data:
            if "chng-gv" in nr_settings:
                attr = data["gv"]
                if attr in not_writable:
                    return "gv." + attr + " is not writable"
    
                try:
                    if attr in [
                        "ps",
                        "rovals",
                        "rs",
                        "snames",
                        "srvals",
                        "output_srvals",
                        "lrun",
                        "pd",
                        "pnames",
                        "sbits",
                        "plugin_menu",
                    ]:  # these return lists
                        gv_lst = getattr(gv, attr)
                    if "sn" in data or "station" in data:
                        if "sn" in data:
                            sn_dict = data["sn"]
                        elif "station" in data:
                            sn_dict = data["station"]
                        sn_lst = list(sn_dict.keys())
                        for i in sn_lst:
                            idx = int(i) - 1
                            gv_lst[idx] = sn_dict[i]
                        return "gv." + attr + " has ben updated"
                    elif "item" in data:
                        try:
                            item_dict = data["item"]
                            item_lst = list(item_dict.keys())
                            for i in item_lst:
                                idx = int(i) - 1
                                gv_lst[idx] = item_dict[i]
                            return "gv." + attr + " has ben updated"
                        except Exception as e:
                            return e
                    elif "index" in data:
                        try:
                            index_dict = data["item"]
                            index_lst = list(index_dict.keys())
                            for i in index_lst:
                                idx = int(i) - 1
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
            else:
                msg = "Global variable (gv) changes are disabled"
                to_node_red(msg)

        #######################
        #### set sd values ####
        elif "sd" in data and "val" in data:
            if "chng-sd" in nr_settings:
                
                # val = int(data["val"]) #### remove after refactor.
                                 
                    # Change values
                try:                    
                    set_sd[data["sd"]](int(data["val"]))
                except KeyError:
                    return "invalid request"
                    
                    # if data["sd"] == "rd":  # rain delay
                    #     pass
                   
                    #     if "chng-rd" in nr_settings:
                    #         gv.sd["rd"] = val
                    #         if val:
                    #             gv.sd["rdst"] = round(gv.now + (val * 3600))
                    #             stop_onrain()
                    #         else:
                    #             gv.sd["rdst"] = 0
                    #     report_rain_delay_change()  # see line 292
                    #     report_option_change()
                        
                        
                        
                    # elif data["sd"] == "mm":  # manual mode
                        # if val == 1:
                        #     gv.sd["mm"] = 1
                        # elif val == 0:
                        #     clear_mm()
                        #     gv.sd["mm"] = 0
                        # else:
                        #     return "invalid request"
                        
                    # elif data["sd"] == "rsn" and val == 1:
                    #     stop_stations()
                        
                    # elif data["sd"] == "wl" and "chng-wl" in nr_settings:
                    #     gv.sd["wl"] = val
                    #     report_option_change()
                        
                    # elif (
                    #     data["sd"] == "nbrd"
                    #     and val != gv.sd["nbrd"]  # number f boards has changed
                    # ):
                    #     brd_chng = val - gv.sd["nbrd"]
                    #     change_options.update_scount(brd_chng)
                    #     gv.sd["nbrd"] = gv.sd["nbrd"] + brd_chng
                    #     gv.sd["nst"] = gv.sd["nbrd"] * 8
                    #     change_options.update_prog_lists("nbrd")
                    #     return "Station count changed"
                    
                    # elif data["sd"] == "htp":
                    #     gv.sd["htp"] = val
                    #     jsave(gv.sd, "sd")
                    #     return "htp changed"
                    
                    # elif data["sd"] == "idd":
                    #     if val != gv.sd["idd"] and (val == 0 or val == 1):
                    #         gv.sd["idd"] = val
                    #         change_options.update_prog_lists("idd")
                    #         jsave(gv.sd, "sd")
                    #         return "Individual durations changed"
                    #     else:
                    #         return "Error val must be 0 or 1"
                        
                    # elif data["sd"] == "mton":
                    #     if val < -60 or val > 60:
                    #         return "Error val must be -60 to +60"
                    #     else:
                    #         gv.sd["mton"] = val
                            
                    # elif data["sd"] == "mtoff":
                    #     if val < -60 or val > 60:
                    #         return "Error val must be -60 to 60"
                    #     else:
                    #         gv.sd["mtoff"] = val
                            
                    # elif data["sd"] == "rbt" and val == 1:
                    #     reboot()
                        
                    # elif data["sd"] == "rstrt" and val == 1:
                    #     restart()
                        
                    # elif data["sd"] == "rs" and gv.sd["urs"]:
                    #     set_rain_sensed(val)
                    
                    ############### end of sd requests #############    
                        
                    if "bit" in data:
                        bit_write(data["sd"], data["bit"])
                        
                    else:  # handle all other vars
                        if not data["sd"] in danger_list or (
                            "force" in data and data["force"] == 1
                        ):
                            gv.sd[data["sd"]] = val
                        else:
                            return "Not recommended"
    
                    if "save" in data and data["save"] == 1:
                        jsave(gv.sd, "sd")
                        return "gv.sd[" + data["sd"] + "] updated to " + str(val)
                    
                except Exception as e:
                    return e
            else:
                msg = "Settinges (sd) changes are disabled"
                to_node_red(msg)            

        # Station on off
        elif ("sn" in data or "station" in data):
            if "chng-stn" in nr_settings:
                station_on_off(data)
            else:
                msg = "Station control is disabled"
                to_node_red(msg)             

        # run once
        elif ("ro" in data or "run once" in data):
            if "chng-ro" in nr_settings:
                pre = 1
                if "preempt" in data and data["preempt"] == 0:
                    pre = 0                 
                if "ro" in data:
                    run_once(data["ro"], pre)
                elif "run once" in data:
                    run_once(data["run once"], pre)
            else:
                msg = "Run Once is disabled"
                to_node_red(msg)                  

        # run now
        elif "runProg" in data:
            if "chng-rn" in nr_settings:
                run_now(data["runProg"])
            else:
                msg = "Run now is disabled"
                to_node_red(msg)                                

        # program on/off
        elif ("prog" in data or "program" in data):
            if "chng-prog" in nr_settings:
                program_on_off(data)
            else:
                msg = "Program control is disabled"
                to_node_red(msg)

        # stop all stations
        elif "stopAll" in data:
            if "stop-stn" in nr_settings: 
                stop_stations()
            else:
                msg = "Stop stations is disabled"
                to_node_red(msg)

        else:
            return "Unknown request"
