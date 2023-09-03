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
from sip import template_render  #  Needed for working with web.py templates
from urls import urls  # Get access to SIP's URLs
import web  # web.py framework
import webpages
from webpages import ProtectedPage  # Needed for security
from webpages import report_option_change, report_value_change


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

#### Global variables ####
base_url = "http://localhost/"
prior_srvals = [0] * len(gv.srvals)
nr_settings = {}


#### Functions ####


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
    global nr_settings
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
    resp = requests.get(url, params=msg)


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
            and gv.pon - 1 == pid  # The program to be disabled is running
        ):
            stop_stations()
        gv.pd[pid]["enabled"] = state
    jsave(gv.pd, "programData")


def station_on_off(data):
    """Enable or disable a station.
    Called by "station switch" node.
    """
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


def send_zone_change(name, **kw):
    """Send notification to node-red
    when core program signals a change in station state.
    """
    # print("249 send_zone_change")
    global prior_srvals
    if len(gv.srvals) > len(prior_srvals):
        prior_srvals += [0] * (len(gv.srvals) - len(prior_srvals))
    if not "station-on-off" in nr_settings:
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


def send_rain_delay_change(name, **kw):  # see line 663
    """Send rain delay state change to node-red"""
    if gv.sd["rd"]:  #  just switched on
        state = 1
    else:  #  Just switched off
        state = 0
    msg = {"rd_state": state}
    to_node_red(msg)  # see line 107


rd_change = signal("rain_delay_change")
rd_change.connect(send_rain_delay_change)

###############################
#### blinker signals ##########
"alarm"
"new_day"
"loggedin"
"option_change"
"program_change"
"program_deleted"
"program_toggled"
"rain_changed"
"rain_delay_change"  # included with "value_change"
"rebooted"
"restarting"
"running_program_change"  # to do
"station_completed"
"station_names"
"stations_scheduled"
"value_change"
"zone_change"  # working
###############################


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
        raise web.seeother("/")  # Return user to home page.


class handle_requests(object):
    """
    parse request messages from node-red
    """

    def GET(self):
        """return value from get request."""
        qdict = dict(web.input())  # Dictionary of JSON values
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

        #######################
        #### Set gv values ####
        if "gv" in data and "chng-gv" in nr_settings:
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

        #######################
        #### set sd values ####
        elif "sd" in data and "chng-sd" in nr_settings and "val" in data:
            val = int(data["val"])
            try:
                # Change values
                if data["sd"] == "rd":  # rain delay
                    if "chng-rd" in nr_settings:
                        gv.sd["rd"] = val
                        if val:
                            gv.sd["rdst"] = round(gv.now + (val * 3600))
                            stop_onrain()
                        else:
                            gv.sd["rdst"] = 0
                    report_rain_delay_change()  # see line 292
                    report_option_change()

                elif data["sd"] == "mm":  # manual mode
                    if val == 1:
                        gv.sd["mm"] = 1
                    elif val == 0:
                        clear_mm()
                        gv.sd["mm"] = 0
                    else:
                        return "invalid request"

                elif data["sd"] == "rsn" and val == 1:
                    stop_stations()

                elif data["sd"] == "wl" and "chng-wl" in nr_settings:
                    gv.sd["wl"] = val
                    report_option_change()

                # Change options
                elif data["sd"] == "nbrd":
                    requests.get(url=base_url + "co", params={"onbrd": val})

                elif data["sd"] == "htp":
                    requests.get(url=base_url + "co", params={"ohtp": val})

                elif data["sd"] == "idd":
                    if val == 1:
                        requests.get(url=base_url + "co", params={"oidd": val})
                    elif val == 0:
                        requests.get(url=base_url + "co", params={"none": val})
                    else:
                        return "invalid request"

                elif data["sd"] == "mton":
                    if val < -60 or val > 60:
                        return "Error val must be -60 to +60"
                    else:
                        gv.sd["mton"] = val

                elif data["sd"] == "mtoff":
                    if val < -60 or val > 60:
                        return "Error val must be -60 to 60"
                    else:
                        gv.sd["mtoff"] = val

                elif data["sd"] == "rbt":
                    requests.get(url=base_url + "co", params={"rbt": val})

                elif data["sd"] == "rstrt":
                    requests.get(url=base_url + "co", params={"rstrt": val})

                elif data["sd"] == "rs" and gv.sd["urs"]:
                    set_rain_sensed(val)

                elif "bit" in data:
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

        # Station on off
        elif ("sn" in data or "station" in data) and "chng-stn" in nr_settings:
            station_on_off(data)

        # run once
        elif ("ro" in data or "run once" in data) and "chng-ro" in nr_settings:
            print("709 data: ", data)
            pre = 1
            if "preempt" in data and data["preempt"] == 0:
                pre = 0
            if "ro" in data:
                run_once(data["ro"], pre)
            elif "run once" in data:
                run_once(data["run once"], pre)

        elif "runProg" in data:
            run_now(data["runProg"])

        elif ("prog" in data or "program" in data) and "chng-prog" in nr_settings:
            program_on_off(data)

        # stop all stations
        elif "stopAll" in data:
            stop_stations()

        else:
            return "Unknown request"
