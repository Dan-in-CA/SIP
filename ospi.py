#!/usr/bin/env python

import re, os, time, datetime, thread, sys # standard Python modules # base64,
from calendar import timegm
try:
    import json
except ImportError:
    import simplejson as json
except ImportError:
    print "Error: json module not found"
    sys.exit()

import web # the Web.py module. See webpy.org (Enables the Python OpenSprinkler web interface)
web.config.debug = False # Improves page load speed
from web import form
import gv # 'global vars' An empty module, used for storing vars (as attributes), that need to be 'global' across threads and between functions and classes.
from gpio_pins import * # provides access to GPIO pins
from urls import * # Provides access to URLs for UI pages

import random
from hashlib import sha1

##############################
#### Revision information ####
gv.ver = 203
gv.rev = 'XXX'
gv.rev_date = '13/July/2014'

#!!! Note: This add-on feature is now deprecated. Code is left in place for backward compatibility.
################################################################
#### Import ospi_addon module (ospi_addon.py) if it exists. ####
# try:
#     import ospi_addon #This provides a stub for adding custom features to ospi.py as external modules.
# except ImportError:
#     print 'add_on not imported'


##############################
#### Function Definitions ####

def baseurl():
    """Return URL app is running under."""
    baseurl = web.ctx['home']
    return baseurl

def check_rain():
    try:
        if gv.sd['rst'] == 0:
            if GPIO.input(pin_rain_sense): # Rain detected
                gv.sd['rs'] = 1
            else:
                gv.sd['rs'] = 0
        elif gv.sd['rst'] == 1:
            if not GPIO.input(pin_rain_sense):
                gv.sd['rs'] = 1
            else:
                gv.sd['rs'] = 0
    except NameError:
        pass

def clear_mm():
    """Clear manual mode settings."""
    if gv.sd['mm']:
        gv.sbits = [0] * (gv.sd['nbrd'] +1)
        gv.ps = []
        for i in range(gv.sd['nst']):
            gv.ps.append([0,0])
        gv.rs = []
        for i in range(gv.sd['nst']):
            gv.rs.append([0,0,0,0])
        gv.srvals = [0]*(gv.sd['nst'])
        set_output()
    return

def reboot():
    gv.srvals = [0]*(gv.sd['nst'])
    set_output()
    os.system('reboot')

def CPU_temperature():
    """Returns the temperature of the CPU if available."""
    try:
        if gv.platform == '':
            return str(0)
        if gv.platform == 'bo':
            res = os.popen('cat /sys/class/hwmon/hwmon0/device/temp1_input').readline()
            return (str(int(float(res)/1000)))
        if gv.platform == 'pi':
            res = os.popen('vcgencmd measure_temp').readline()
            return(res.replace("temp=","").replace("'C\n",""))
    except:
        pass

def timestr(t):
     return str((t/60>>0)/10>>0) + str((t/60>>0)%10) + ":" + str((t%60>>0)/10>>0) + str((t%60>>0)%10)

def log_run():
    """add run data to csv file - most recent first."""
    if gv.sd['lg']:
        if gv.lrun[1] == 98:
            pgr = 'Run-once'
        elif gv.lrun[1] == 99:
            pgr = 'Manual'
        else:
            pgr = str(gv.lrun[1])

        start = time.gmtime(gv.now - gv.lrun[2])
        logline = '{"program":"' + pgr + '","station":' + str(gv.lrun[0]) + ',"duration":"' + timestr(gv.lrun[2]) + '","start":"' + time.strftime('%H:%M:%S","date":"%Y-%m-%d"', start) + '}\n'
        log = read_log()
        log.insert(0, logline)
        f = open('./data/log.json', 'w')
        if gv.sd['lr']:
            f.writelines(log[:gv.sd['lr']])
        else:
            f.writelines(log)
        f.close()
    return

def prog_match(prog):
    """Test a program for current date and time match."""
    if not prog[0]: return 0 # Skip if program is not enabled
    devday = int(gv.now/86400) # Check day match
    lt = time.gmtime(gv.now)
    if (prog[1]>=128) and (prog[2]>1): #Inverval program
        if (devday %prog[2]) != (prog[1] - 128): return 0
    else: # Weekday program
        if not prog[1]-128 & 1<<lt[6]: return 0
        if prog[1]>=128 and prog[2] == 0: #even days
            if lt[2]%2 != 0: return 0
        if prog[1]>=128 and prog[2] == 1: #Odd days
            if lt[2]==31 or (lt[1]==2 and lt[2]==29): return 0
            elif lt[2]%2 !=1: return 0
    this_minute = (lt[3]*60)+lt[4] # Check time match
    if this_minute < prog[3] or this_minute >= prog[4]: return 0
    if prog[5] == 0: return 0
    if ((this_minute - prog[3]) / prog[5]) * prog[5] == this_minute - prog[3]:
        return 1 # Program matched
    return 0

def schedule_stations(stations):
    """Schedule stations/valves/zones to run."""
    if gv.sd['rd'] or (gv.sd['urs'] and gv.sd['rs']): # If rain delay or rain detected by sensor
        rain = True
    else:
        rain = False
    accumulate_time = gv.now
    if gv.sd['seq']: #sequential mode, stations run one after another
        for b in range(len(stations)):
                for s in range(8):
                    sid = b*8 + s # station index
                    if gv.rs[sid][2]: # if station has a duration value
                        if not rain or gv.sd['ir'][b]&1<<s: # if no rain or station ignores rain
                            gv.rs[sid][0] = accumulate_time # start at accumulated time
                            accumulate_time += gv.rs[sid][2] # add duration
                            gv.rs[sid][1] = accumulate_time # set new stop time
                            accumulate_time += gv.sd['sdt'] # add station delay
                        else:
                            gv.sbits[b] = gv.sbits[b]&~1<<s
                            gv.ps[s] = [0,0]

    else: # concurrent mode, stations allowed to run in parallel
        for b in range(len(stations)):
                for s in range(8):
                    sid = b*8 + s # station index
                    if not stations[b]&1<<s: # skip stations not in prog
                        continue
                    if gv.rs[sid][2]: # if station has a duration value
                        if not rain or gv.sd['ir'][b]&1<<s: # if no rain or station ignores rain
                            gv.rs[sid][0] = gv.now #accumulate_time # set start time
                            gv.rs[sid][1] = (gv.now + gv.rs[sid][2]) # set stop time
                        else: # if rain and station does not ignore, clear station from display
                            gv.sbits[b] = gv.sbits[b]&~1<<s
                            gv.ps[s] = [0,0]
    gv.sd['bsy'] = 1
    return

def stop_onrain():
    """Stop stations that do not ignore rain."""
    for b in range(gv.sd['nbrd']):
        for s in range(8):
            sid = b*8 + s # station index
            if gv.sd['ir'][b]&1<<s: # if station ignores rain...
                continue
            elif not all(v == 0 for v in gv.rs[sid]):
                gv.srvals[sid] = 0
                set_output()
                gv.sbits[b] = gv.sbits[b]&~1<<s # Clears stopped stations from display
                gv.ps[sid] = [0,0]
                gv.rs[sid] = [0,0,0,0]
    return

def stop_stations():
        """Stop all running stations, clear schedules."""
        gv.srvals = [0]*(gv.sd['nst'])
        set_output()
        gv.ps = []
        for i in range(gv.sd['nst']):
            gv.ps.append([0,0])
        gv.sbits = [0] * (gv.sd['nbrd'] +1)
        gv.rs = []
        for i in range(gv.sd['nst']):
            gv.rs.append([0,0,0,0])
        gv.sd['bsy'] = 0
        return

def timing_loop():
    """ ***** Main timing algorithm. Runs in a separate thread.***** """
    print 'Starting timing loop \n'
    last_min = 0
    while True: # infinite loop
        gv.now = timegm(time.localtime()) # Current time based on local time from the Pi. updated once per second.
        if gv.sd['en'] and not gv.sd['mm'] and (not gv.sd['bsy'] or not gv.sd['seq']):
            lt = time.gmtime(gv.now)
            if (lt[3]*60)+lt[4] != last_min: # only check programs once a minute
                last_min = (lt[3]*60)+lt[4]
                for i, p in enumerate(gv.pd): # get both index and prog item
                    if prog_match(p) and p[0] and p[6]: # check if program time matches current time, is active, and has a duration
                        duration = p[6]*gv.sd['wl']/100 # program duration scaled by "water level"
                        for b in range(len(p[7:7+gv.sd['nbrd']])): # check each station for boards listed in program up to number of boards in Options
                            for s in range(8):
                                sid = b*8+s # station index
                                if sid+1 == gv.sd['mas']: continue # skip if this is master station
                                if gv.srvals[sid]: continue # skip if currently on

                                if p[7+b]&1<<s: # if this station is scheduled in this program
                                    if gv.sd['seq']: # sequential mode
                                        gv.rs[sid][2] = duration # p[6]*gv.sd['wl']/100 # store duration scaled by water level
                                        gv.rs[sid][3] = i+1 # store program number for scheduling
                                        gv.ps[sid][0] = i+1 # store program number for display
                                        gv.ps[sid][1] = duration
                                    else: # concurrent mode
                                        if duration < gv.rs[sid][2]: # If duration is shortter than any already set for this station
                                            continue
                                        else:
                                            gv.rs[sid][2] = duration
                                            gv.rs[sid][3] = i+1 # store program number
                                            gv.ps[sid][0] = i+1 # store program number for display
                                            gv.ps[sid][1] = duration
                        schedule_stations(p[7:7+gv.sd['nbrd']]) # turns on gv.sd['bsy']


        if gv.sd['bsy']:
            for b in range(gv.sd['nbrd']): # Check each station once a second
                for s in range(8):
                    sid = b*8 + s # station index
                    if gv.srvals[sid]: # if this station is on
                        if gv.now >= gv.rs[sid][1]: # check if time is up
                            gv.srvals[sid] = 0
                            set_output()
                            gv.sbits[b] = gv.sbits[b]&~1<<s
                            if gv.sd['mas']-1 != sid: # if not master, fill out log
                                gv.ps[sid] = [0,0]
                                gv.lrun[0] = sid
                                gv.lrun[1] = gv.rs[sid][3]
                                gv.lrun[2] = int(gv.now - gv.rs[sid][0])
                                gv.lrun[3] = gv.now
                                log_run()
                                gv.pon = None # Program has ended
                            gv.rs[sid] = [0,0,0,0]
                    else: # if this station is not yet on
                        if gv.now >= gv.rs[sid][0] and gv.now < gv.rs[sid][1]:
                            if gv.sd['mas']-1 != sid: # if not master
                                gv.srvals[sid] = 1 # station is turned on
                                set_output()
                                gv.sbits[b] = gv.sbits[b]|1<<s # Set display to on
                                gv.ps[sid][0] = gv.rs[sid][3]
                                gv.ps[sid][1] = gv.rs[sid][2]+1 ### testing display
                                if gv.sd['mas'] and gv.sd['mo'][b]&1<<(s-(s/8)*80):# Master settings
                                    masid = gv.sd['mas'] - 1 # master index
                                    gv.rs[masid][0] = gv.rs[sid][0] + gv.sd['mton']
                                    gv.rs[masid][1] = gv.rs[sid][1] + gv.sd['mtoff']
                                    gv.rs[masid][3] = gv.rs[sid][3]
                            elif gv.sd['mas'] == sid+1:
                                gv.sbits[b] = gv.sbits[b]|1<<sid #(gv.sd['mas'] - 1)
                                gv.srvals[masid] = 1
                                set_output()

            for s in range(gv.sd['nst']):
                if gv.rs[s][1]: # if any station is scheduled
                    program_running = True
                    gv.pon = gv.rs[s][3] # Store number of running program
                    break
                program_running = False
                gv.pon = None

            if program_running:
                if gv.sd['urs'] and gv.sd['rs']: # Stop stations if use rain sensor and rain detected.
                    stop_onrain() #Clear schedule for stations that do not ignore rain.
                for idx in range(len(gv.rs)): # loop through program schedule (gv.ps)
                    if gv.rs[idx][2] == 0: # skip stations with no duration
                        continue
                    if gv.srvals[idx]: # If station is on, decrement time remaining display
                        gv.ps[idx][1] -= 1

            if not program_running:
                gv.srvals = [0]*(gv.sd['nst'])
                set_output()
                gv.sbits = [0] * (gv.sd['nbrd'] +1)
                gv.ps = []
                for i in range(gv.sd['nst']):
                    gv.ps.append([0,0])
                gv.rs = []
                for i in range(gv.sd['nst']):
                    gv.rs.append([0,0,0,0])
                gv.sd['bsy'] = 0

            if gv.sd['mas'] and (gv.sd['mm'] or not gv.sd['seq']): # handle master for maual or concurrent mode.
                mval = 0
                for sid in range(gv.sd['nst']):
                    bid = sid/8
                    s = sid-bid*8
                    if gv.sd['mas'] != sid +1 and (gv.srvals[sid] and gv.sd['mo'][bid]&1<<s):
                        mval = 1
                        break
                if not mval:
                    gv.rs[gv.sd['mas']-1][1] = gv.now # turn off master

        if gv.sd['urs']:
            check_rain()

        if gv.sd['rd'] and gv.now>= gv.sd['rdst']: # Check of rain delay time is up
            gv.sd['rd'] = 0
            gv.sd['rdst'] = 0 # Rain delay stop time
            jsave(gv.sd, 'sd')
        time.sleep(1)
        #### End of timing loop ####

def data(dataf):
    """Return contents of requested text file as string or create file if a missing config file."""
    try:
        f = open('./data/'+dataf+'.txt', 'r')
        data = f.read()
        f.close()
    except IOError:
        if dataf == 'snames': ## A config file -- return defaults and create file if not found. ##
            data = "['S1','S2','S3','S4','S5','S6','S7','S8',]"
            f = open('./data/'+dataf+'.txt', 'w')
            f.write(data)
            f.close()
        else:
            return None
    return data

def save(dataf, datastr):
    """Save data to text file. dataf = file to save to, datastr = data string to save."""
    f = open('./data/'+dataf+'.txt', 'w')
    f.write(datastr)
    f.close()
    return

def read_log():
    try:
        logf = open('./data/log.json')
        records = logf.readlines()
        logf.close()
        return records
    except IOError:
        return []

def jsave(data, fname):
    """Save data to a json file."""
    f = open('./data/'+fname+'.json', 'w')
    json.dump(data, f)
    f.close()

def load_programs():
    """Load program data from json file, if it exists, into memory, otherwise create an empty programs var."""
    try:
        pf = open('./data/programs.json', 'r')
        gv.pd = json.load(pf)
        pf.close()
    except IOError:
        gv.pd = [] #A config file -- return default and create file if not found.
        pf = open('./data/programs.json', 'w')
        json.dump(gv.pd, pf)
        pf.close()
    return gv.pd

def output_prog():
    """Converts program data to text string and outputs JavaScript vars used to display program page."""
    lpd = [] # Local program data
    dse = int(gv.now/86400) # days since epoch
    for p in gv.pd:
        op = p[:] # Make local copy of each program
        if op[1] >= 128 and op[2] > 1:
            rel_rem = (((op[1]-128) + op[2])-(dse % op[2])) % op[2] # Convert absolute days to relative remaining (rel_rem) days
            op[1] = rel_rem + 128 # Update from saved value based on current date
        lpd.append(op)
    progstr = 'var nprogs='+str(len(lpd))+',nboards='+str(gv.sd['nbrd'])+',ipas='+str(gv.sd['ipas'])+',mnp='+str(gv.sd['mnp'])+',pd=[];'
    for i, pro in enumerate(lpd): #gets both index and object
        progstr += 'pd['+str(i)+']='+str(pro).replace(' ', '')+';'
    return progstr

def passwordSalt():
    return "".join(chr(random.randint(33,127)) for x in xrange(64))

def passwordHash(password, salt):
    return sha1(password + salt).hexdigest()

#####################
#### Global vars ####

#Settings Dictionary. A set of vars kept in memory and persisted in a file.
#Edit this default dictionary definition to add or remove "key": "value" pairs or change defaults.
gv.sd = ({u"en": 1, u"seq": 1, u"mnp": 32, u"ir": [0], u"rsn": 0, u"htp": 8080, u"nst": 8,
            u"rdst": 0, u"loc": u"", u"tz": 48, u"tf": 1,  u"rs": 0, u"rd": 0, u"mton": 0,
            u"lr": u"100", u"sdt": 0, u"mas": 0, u"wl": 100, u"bsy": 0, u"lg": u"",
            u"urs": 0, u"nopts": 13, u"pwd": u"b3BlbmRvb3I=", u"password": u"", u"salt": u"", u"ipas": 0, u"rst": 1,
            u"mm": 0, u"mo": [0], u"rbt": 0, u"mtoff": 0, u"nprogs": 1, u"nbrd": 1, u"tu": u"C",
            u"snlen":32, u"name": u"OpenSprinkler Pi",u"theme": u"basic","show":[255]})

gv.sd['salt'] = passwordSalt()
gv.sd['password'] = passwordHash('opendoor', gv.sd['salt'])
# note old passwords stored in the "pwd" option will be lost - reverts to default password.

try:
    sdf = open('./data/sd.json', 'r') ## A config file ##
    sd_temp = json.load(sdf)
    sdf.close()
    for key in gv.sd: # If file loaded, replce default values in gv.sd with values from file
        if key in sd_temp:
            gv.sd[key] = sd_temp[key]
except IOError: # If file does not exist, it will be created created using defaults.
    sdf = open('./data/sd.json', 'w') # save file
    json.dump(gv.sd, sdf)
    sdf.close()

gv.now = timegm(time.localtime())

gv.plugin_menu = [] #Empty list of lists for plugin links (e.g. ['name', 'URL'])

gv.srvals = [0]*(gv.sd['nst']) #Shift Register values

gv.rovals = [0]* gv.sd['nbrd']*7 #Run Once durations

gv.pd = load_programs() # Load program data from file

gv.ps = [] #Program schedule (used for UI display)
for i in range(gv.sd['nst']):
    gv.ps.append([0,0])

gv.pon = None #Program on (Holds program number of a running program)

gv.sbits = [0] * (gv.sd['nbrd'] +1) # Used to display stations that are on in UI

gv.rs = [] #run schedule
for i in range(gv.sd['nst']):
    gv.rs.append([0,0,0,0]) #scheduled start time, scheduled stop time, duration, program index

gv.lrun=[0,0,0,0] #station index, program number, duration, end time (Used in UI)

gv.scount = 0 # Station count, used in set station to track on stations with master association.

gv.snames = data('snames') # initialize station names to be used by plugins

  ########################
  #### Login Handling ####

def checkPassword(password, salt, hash):
    return hash == sha1(password + salt).hexdigest()

def checkLogin():
    try:
        if gv.sd['ipas'] == 0 and web.config._session.user != 'admin':
            raise web.seeother('/login')
    except KeyError:
        pass

def verifyLogin():
    qdict = web.input()

    if gv.sd['ipas'] == 1:
        return True
    if web.config._session.user == 'admin':
        return True
    if qdict.has_key('pw') and gv.sd['password'] == sha1(qdict['pw'] + gv.sd['salt']).hexdigest():
        return True

    raise web.unauthorized()

signin_form = form.Form(form.Password('password',
                                      description='Password:'),
                        validators = [form.Validator("Incorrect password, please try again",
                                      lambda x: checkPassword(x.password, gv.sd['salt'], gv.sd['password'])) ])

class login:
    """Login page"""
    def GET(self):
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={'gv': gv, 'str': str, 'user': web.config._session.user})
        return render.login(signin_form())

    def POST(self):
        my_signin = signin_form()
        render = web.template.render('templates', globals={'gv': gv, 'str': str, 'user': web.config._session.user})
        if not my_signin.validates():
            return render.login(my_signin)
        else:
            web.config._session.user = 'admin'
            raise web.seeother('/')

class logout:
    def GET(self):
        web.config._session.user = 'anonymous'
        raise web.seeother('/')

###########################
#### Class Definitions ####
class home:
    """Open Home page."""
    def GET(self):
        checkLogin()
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data, 'user': web.config._session.user })
        return render.home()

class change_values:
    """Save controller values, return browser to home page."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        if qdict.has_key('rsn') and qdict['rsn'] == '1':
            stop_stations()
            raise web.seeother('/')
            return
        if qdict.has_key('en') and qdict['en'] == '':
            qdict['en'] = '1' #default
        elif qdict.has_key('en') and qdict['en'] == '0':
            gv.srvals = [0]*(gv.sd['nst']) # turn off all stations
            set_output()
        if qdict.has_key('mm') and qdict['mm'] == '0':
            clear_mm()
        if qdict.has_key('rd') and qdict['rd'] != '0' and qdict['rd'] != '':
            gv.sd['rd'] = float(qdict['rd'])
            gv.sd['rdst'] = gv.now + gv.sd['rd']*3600 + 1 # +1 adds a smidge just so after a round trip the display hasn't already counted down by a minute.
            stop_onrain()
        elif qdict.has_key('rd') and qdict['rd'] == '0':
            gv.sd['rdst'] = 0
        for key in qdict.keys():
            try:
                gv.sd[key] = int(qdict[key])
            except:
                pass
        jsave(gv.sd, 'sd')
        if qdict.has_key('rbt') and qdict['rbt'] == '1':
            reboot()
        raise web.seeother('/')# Send browser back to home page

class view_options:
    """Open the options page for viewing and editing."""
    def GET(self):
        checkLogin()
        qdict = web.input()
        errorCode = "none"
        if qdict.has_key('errorCode'):
            errorCode = qdict['errorCode']
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data})
        return render.options(errorCode)

class change_options:
    """Save changes to options made on the options page."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        if qdict.has_key('opw') and qdict['opw'] != "":
            try:
                if passwordHash(qdict['opw'], gv.sd['salt']) == gv.sd['password']:
                    if qdict['npw'] == "":
                        raise web.seeother('/vo?errorCode=pw_blank')
                    elif qdict['cpw'] !='' and qdict['cpw'] == qdict['npw']:
                        gv.sd['password'] = passwordHash(qdict['npw'], gv.sd['salt'])
                    else:
                        raise web.seeother('/vo?errorCode=pw_mismatch')
                else:
                    raise web.seeother('/vo?errorCode=pw_wrong')
            except KeyError:
                pass

        try:
            if qdict.has_key('oipas') and (qdict['oipas'] == 'on' or qdict['oipas'] == '1'):
                gv.sd['ipas'] = 1
            else:
                gv.sd['ipas'] = 0
        except KeyError:
            pass

        if qdict.has_key('oname'):
            gv.sd['name'] = qdict['oname']
        if qdict.has_key('oloc'):
            gv.sd['loc'] = qdict['oloc']
        if qdict.has_key('otz'):
            gv.sd['tz'] = int(qdict['otz'])
        try:
            if qdict.has_key('otf') and (qdict['otf'] == 'on' or qdict['otf'] == '1'):
                gv.sd['tf'] = 1
            else:
                gv.sd['tf'] = 0
        except KeyError:
            pass

        if int(qdict['onbrd'])+1 != gv.sd['nbrd']: self.update_scount(qdict)
        gv.sd['nbrd'] = int(qdict['onbrd'])+1

        gv.sd['nst'] = gv.sd['nbrd']*8
        if qdict.has_key('ohtp'):
            gv.sd['htp']= int(qdict['ohtp'])
        if qdict.has_key('osdt'):
            gv.sd['sdt']= int(qdict['osdt'])

        if qdict.has_key('omas'):
            gv.sd['mas'] = int(qdict['omas'])
        if qdict.has_key('omton'):
            gv.sd['mton']= int(qdict['omton'])
        if qdict.has_key('omtoff'):
            gv.sd['mtoff']= int(qdict['omtoff'])
        if qdict.has_key('owl'):
            gv.sd['wl'] = int(qdict['owl'])

        if qdict.has_key('ours') and (qdict['ours'] == 'on' or qdict['ours'] == '1'):
          gv.sd['urs'] = 1
        else:
          gv.sd['urs'] = 0

        if qdict.has_key('oseq') and (qdict['oseq'] == 'on' or qdict['oseq'] == '1'):
          gv.sd['seq'] = 1
        else:
          gv.sd['seq'] = 0

        if qdict.has_key('orst') and (qdict['orst'] == 'on' or qdict['orst'] == '1'):
          gv.sd['rst'] = 1
        else:
          gv.sd['rst'] = 0

        if qdict.has_key('olg') and (qdict['olg'] == 'on' or qdict['olg'] == '1'):
          gv.sd['lg'] = 1
        else:
          gv.sd['lg'] = 0

        if qdict.has_key('olr'):
            gv.sd['lr'] = int(qdict['olr'])

        srvals = [0]*(gv.sd['nst']) # Shift Register values
        rovals = [0]*(gv.sd['nst']) # Run Once Durations
        jsave(gv.sd, 'sd')
        if qdict.has_key('rbt') and qdict['rbt'] == '1':
            reboot()
        raise web.seeother('/')

    def update_scount(self, qdict):
        """Increase or decrease the number of stations displayed when number of expansion boards is changed in options."""
        if int(qdict['onbrd'])+1 > gv.sd['nbrd']: # Lengthen lists
            incr = int(qdict['onbrd']) - (gv.sd['nbrd']-1)
            for i in range(incr):
                gv.sd['mo'].append(0)
                gv.sd['ir'].append(0)
                gv.sd['show'].append(255)
            snames = data('snames')
            nlst = re.findall('[\'"].*?[\'"]', snames)
            ln = len(nlst)
            nlst.pop()
            for i in range((incr*8)+1):
                nlst.append("'S"+('%d'%(i+ln))+"'")
            nstr = '['+','.join(nlst)
            nstr = nstr.replace("', ", "',")+"]"
            save('snames', nstr)
            for i in range(incr*8):
                gv.srvals.append(0)
                gv.ps.append([0,0])
                gv.rs.append([0,0,0,0])
            for i in range(incr):
                gv.sbits.append(0)
        elif int(qdict['onbrd'])+1 < gv.sd['nbrd']: # Shorten lists
            onbrd = int(qdict['onbrd'])
            decr = gv.sd['nbrd'] - (onbrd+1)
            gv.sd['mo'] = gv.sd['mo'][:(onbrd+1)]
            gv.sd['ir'] = gv.sd['ir'][:(onbrd+1)]
            gv.sd['show'] = gv.sd['show'][:(onbrd+1)]
            snames = data('snames')
            nlst = re.findall('[\'"].*?[\'"]', snames)
            nstr = '['+','.join(nlst[:8+(onbrd*8)])+']'
            save('snames', nstr)
            newlen = gv.sd['nst'] - decr * 8
            gv.srvals = gv.srvals[:newlen]
            gv.ps = gv.ps[:newlen]
            gv.rs = gv.rs[:newlen]
            gv.sbits = gv.sbits[:onbrd+1]
        return

class view_stations:
    """Open a page to view and edit a run once program."""
    def GET(self):
        checkLogin()
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data })
        return render.stations()

class change_stations:
    """Save changes to station names, ignore rain and master associations."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        for i in range(gv.sd['nbrd']): # capture master associations
            if qdict.has_key('m'+str(i)):
                try:
                    gv.sd['mo'][i] = int(qdict['m'+str(i)])
                except ValueError:
                    gv.sd['mo'][i] = 0
            if qdict.has_key('i'+str(i)):
                try:
                    gv.sd['ir'][i] = int(qdict['i'+str(i)])
                except ValueError:
                    gv.sd['ir'][i] = 0
            if qdict.has_key('sh'+str(i)):
                try:
                    gv.sd['show'][i] = int(qdict['sh'+str(i)])
                except ValueError:
                    gv.sd['show'][i] = 255
        names = '['
        for i in range(gv.sd['nst']):
            if qdict.has_key('s'+str(i)):
                names += "'" + qdict['s'+str(i)] + "',"
            else:
                names += "'S"+str(i+1) + "',"
        names += ']'
        gv.snames = names
        save('snames', names.encode('ascii', 'backslashreplace'))
        jsave(gv.sd, 'sd')
        raise web.seeother('/')

class get_station:
    """Return a page containing a number representing the state of a station or all stations if 0 is entered as station number."""
    def GET(self, sn):
        verifyLogin()
        if sn == '0':
            status = '<!DOCTYPE html>\n'
            status += ''.join(str(x) for x in gv.srvals)
            return status
        elif int(sn)-1 <= gv.sd['nbrd']*7:
            status = '<!DOCTYPE html>\n'
            status += str(gv.srvals[int(sn)-1])
            return status
        else:
            return 'Station '+sn+' not found.'

class set_station:
    """turn a station (valve/zone) on=1 or off=0 in manual mode."""
    def GET(self, nst, t=None): # nst = station number, status, optional duration
        nstlst = [int(i) for i in re.split('=|&t=', nst)]
        if len(nstlst) == 2:
            nstlst.append(0)
        sid = int(nstlst[0])-1 # station index
        b = sid/8 #board index
        if nstlst[1] == 1 and gv.sd['mm']: # if status is on and manual mode is set
            gv.rs[sid][0] = gv.now # set start time to current time
            if nstlst[2]: # if an optional duration time is given
                gv.rs[sid][2] = nstlst[2]
                gv.rs[sid][1] = gv.rs[sid][0] + nstlst[2] # stop time = start time + duration
            else:
                gv.rs[sid][1] = float('inf') # stop time = infinity
            gv.rs[sid][3] = 99 # set program index
            gv.ps[sid][1] = nstlst[2]
            gv.sd['bsy']=1
            time.sleep(1)
        if nstlst[1] == 0 and gv.sd['mm']: # If status is off
            gv.rs[sid][1] = gv.now
            time.sleep(1)
        raise web.seeother('/')

class view_runonce:
    """Open a page to view and edit a run once program."""
    def GET(self):
        checkLogin()
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data })
        return render.runonce()

class change_runonce:
    """Start a Run Once program. This will override any running program."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        if not gv.sd['en']: return # check operation status
        gv.rovals = json.loads(qdict['t'])
        gv.rovals.pop()
        stations = [0] * gv.sd['nbrd']
        gv.ps = [] # program schedule (for display)
        gv.rs = [] # run schedule
        for i in range(gv.sd['nst']):
            gv.ps.append([0,0])
            gv.rs.append([0,0,0,0])
        for i, v in enumerate(gv.rovals):
            if v: # if this element has a value
                gv.rs[i][0] = gv.now
                gv.rs[i][2] = v
                gv.rs[i][3] = 98
                gv.ps[i][0] = 98
                gv.ps[i][1] = v
                stations[i/8] += 2**(i%8)
        schedule_stations(stations)
        raise web.seeother('/')

class view_programs:
    """Open programs page."""
    def GET(self):
        checkLogin()
        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data })
        return render.programs()


class modify_program:
    """Open page to allow program modification."""
    def GET(self):
        checkLogin()
        qdict = web.input()
        pid = int(qdict['pid'])
        prog = [];
        if pid != -1:
            mp = gv.pd[pid][:] # Modified program
            if mp[1] >= 128 and mp[2] > 1: # If this is an interval program
                dse = int(gv.now/86400)
                rel_rem = (((mp[1]-128) + mp[2])-(dse%mp[2]))%mp[2] # Convert absolute to relative days remaining for display
                mp[1] = rel_rem + 128 # Update from saved value.
            prog = str(mp).replace(' ', '')

        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data })
        return render.modify(pid, prog)

class change_program:
    """Add a program or modify an existing one."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        pnum = int(qdict['pid'])+1 # program number
        cp = json.loads(qdict['v'])
        if cp[0] == 0 and pnum == gv.pon: # if disabled and program is running
            for i in range(len(gv.ps)):
                if gv.ps[i][0] == pnum:
                    gv.ps[i] = [0,0]
                if gv.srvals[i]:
                    gv.srvals[i] = 0
            for i in range(len(gv.rs)):
                if gv.rs[i][3] == pnum:
                    gv.rs[i] = [0,0,0,0]
        if cp[1] >= 128 and cp[2] > 1:
            dse = int(gv.now/86400)
            ref = dse + cp[1]-128
            cp[1] = (ref%cp[2])+128
        if int(qdict['pid']) > gv.sd['mnp']:
            alert = '<script>alert("Maximum number of programs\n has been reached.");window.location="/";</script>'
            return alert
        elif qdict['pid'] == '-1': #add new program
            gv.pd.append(cp)
        else:
            gv.pd[int(qdict['pid'])] = cp #replace program
        jsave(gv.pd, 'programs')
        gv.sd['nprogs'] = len(gv.pd)
        raise web.seeother('/vp')
        return

class delete_program:
    """Delete one or all existing program(s)."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        if qdict['pid'] == '-1':
            del gv.pd[:]
            jsave(gv.pd, 'programs')
        else:
            del gv.pd[int(qdict['pid'])]
        jsave(gv.pd, 'programs')
        gv.sd['nprogs'] = len(gv.pd)
        raise web.seeother('/vp')
        return
                          
class enable_program:
    """Activate an existing program(s)."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        gv.pd[int(qdict['pid'])][0] = int(qdict['enable'])
        jsave(gv.pd, 'programs')
        raise web.seeother('/vp')
        return
                          
class view_log:
    """View Log"""
    def GET(self):
        verifyLogin()
        records = read_log()
        snames = data('snames')
        zones = re.findall(r"\'(.+?)\'",snames)

        gv.baseurl = baseurl()
        gv.cputemp = CPU_temperature()
        render = web.template.render('templates', globals={ 'gv': gv, 'str': str, 'eval': eval, 'data': data, 'json': json })
        return render.log(records)

class clear_log:
    """Delete all log records"""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        f = open('./data/log.json', 'w')
        f.write('')
        f.close
        raise web.seeother('/vl')

class run_now:
    """Run a scheduled program now. This will override any running programs."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        pid = int(qdict['pid'])
        p = gv.pd[int(qdict['pid'])] # program data
        if not p[0]: # if program is disabled
            raise web.seeother('/vp')
        stop_stations()
        for b in range(len(p[7:7+gv.sd['nbrd']])): # check each station
            for s in range(8):
                sid = b*8+s # station index
                if sid+1 == gv.sd['mas']: continue # skip if this is master valve
                if p[7+b]&1<<s: # if this station is scheduled in this program
                    gv.rs[sid][2] = p[6]*gv.sd['wl']/100 # duration scaled by water level
                    gv.rs[sid][3] = pid+1 # store program number in schedule
                    gv.ps[sid][0] = pid+1 # store program number for display
                    gv.ps[sid][1] = gv.rs[sid][2] # duration
        schedule_stations(p[7:7+gv.sd['nbrd']])
        raise web.seeother('/')

class show_revision:
    """Show revision info to the user. Use: [URL of Pi]/rev."""
    def GET(self):
        checkLogin()
        revpg = '<!DOCTYPE html>\n'
        revpg += 'Python Interval Program for OpenSprinkler Pi<br/><br/>\n'
        revpg += 'Compatable with OpenSprinkler firmware 1.8.3.<br/><br/>\n'
        revpg += 'Includes plugin archetecture\n'
        revpg += 'ospi.py revision: '+str(gv.rev) +'<br/><br/>\n'
        revpg += 'updated ' + gv.rev_date +'\n'
        return revpg

class toggle_temp:
    """Change units of Raspi's CPU temperature display on home page."""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        if qdict['tunit'] == "C":
            gv.sd['tu'] = "F"
        else:
            gv.sd['tu'] = "C"
        jsave(gv.sd, 'sd')
        raise web.seeother('/')

class api_status:
    """Simple Status API"""
    def GET(self):
        verifyLogin()
        statuslist = []
        for bid in range(0, gv.sd['nbrd']):
            for s in range(0,8):
                if (gv.sd['show'][bid]>>s)&1 == 1:
                    sid = bid*8 + s
                    sn = sid + 1
                    sbit = (gv.sbits[bid]>>s)&1
                    irbit = (gv.sd['ir'][bid]>>s)&1
                    status = {'station' : sid, 'status' : 'disabled', 'reason' : '', 'master' : 0, 'programName' : '', 'remaining' : 0}
                    if gv.sd['en'] == 1:
                        if sbit:
                            status['status'] = 'on'
                        if not irbit:
                            if gv.sd['rd'] != 0:
                                status['reason'] = 'rain_delay'
                            if gv.sd['urs'] != 0 and gv.sd['rs'] != 0:
                                status['reason'] = 'rain_sensed'
                        if sn == gv.sd['mas']:
                            status['master'] = 1
                            status['reason'] = 'master'
                        else:
                            rem = gv.ps[sid][1]
                            if rem > 65536:
                                rem = 0

                            id = gv.ps[sid][0]
                            pname = 'P' + str(id)
                            if (id == 255 or id == 99):
                                pname = 'Manual Mode'
                            if (id == 254 or id == 98):
                                pname = 'Run-once Program'

                            if sbit:
                                status['status'] = 'on'
                                status['reason'] = 'program'
                                status['programName'] = pname
                                status['remaining'] = rem
                            else:
                                if gv.ps[sid][0] == 0:
                                    status['status'] = 'off'
                                else:
                                    status['status'] = 'waiting'
                                    status['reason'] = 'program'
                                    status['programName'] = pname
                                    status['remaining'] = rem
                    else:
                        status['reason'] = 'system_off'
                    statuslist.append(status)
        web.header('Content-Type', 'application/json')
        return json.dumps(statuslist)

class api_log:
    """Simple Log API"""
    def GET(self):
        verifyLogin()
        qdict = web.input()
        thedate = qdict['date']
        # date parameter filters the log values returned; "yyyy-mm-dd" format
        theday = datetime.date(*map(int, thedate.split('-')))
        prevday = theday - datetime.timedelta(days=1)
        prevdate = prevday.strftime('%Y-%m-%d')

        records = read_log()
        data = []

        for r in records:
            event = json.loads(r)

            # return any records starting on this date
            if not(qdict.has_key('date')) or event['date'] == thedate:
                data.append(event)
            # also return any records starting the day before and completing after midnight
            if event['date'] == prevdate:
                if int(event['start'].split(":")[0])*60 + int(event['start'].split(":")[1]) + int(event['duration'].split(":")[0]) > 24*60:
                    data.append(event)

        web.header('Content-Type', 'application/json')
        return json.dumps(data)

class water_log:
    """Simple Log API"""
    def GET(self):
        verifyLogin()
        records = read_log()
        data = "Date, Start Time, Zone, Duration, Program\n"
        for r in records:
            event = json.loads(r)
            data += event["date"] + ", " + event["start"] + ", " + str(event["station"]) + ", " + event["duration"] + ", " + event["program"] + "\n"

        web.header('Content-Type', 'text/csv')
        return data

################################
#### Code to import plugins ####
import plugins
print 'plugins loaded:'
print plugins.__all__
for name in plugins.__all__:
    plugin = getattr(plugins, name)

class OSPi_app(web.application):
    """Allow program to select HTTP port."""
    def run(self, port=gv.sd['htp'], *middleware): # get port number from options settings
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))

if __name__ == '__main__':
    app = OSPi_app(urls, globals())
    if web.config.get('_session') is None:
        web.config._session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'user': 'anonymous'})
    gv.srvals = [0]*(gv.sd['nst'])
    set_output()
    thread.start_new_thread(timing_loop, ())
    app.run()
