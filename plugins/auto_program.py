import web, json, time, io, re, urllib2, datetime
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs

try:
    from apscheduler.scheduler import Scheduler #This is a non-standard module. Needs to be installed in order for this feature to work.
except ImportError:
    pass

try:
    sched = Scheduler()
    sched.start() # Start the scheduler
except NameError:
    pass    

urls.extend(['/auto', 'plugins.auto_program.auto_program', '/uap', 'plugins.auto_program.update_auto_program']) # Add a new url to open the data entry page
    
@sched.cron_schedule(hour=2)
def setAutoProgram():
    # this routine will create a new program for today based on historical rainfall total and last 7 day watering
    try:
        # read data from the file, if it exists - if not stop!
        with io.open(r'./data/wx_settings.json', 'r') as data_file: 
            data = json.load(data_file)
        data_file.close()  
    except IOError:
        return

    # the program will be created with pid (program ID) of one more than the maximum # of programs
    autoPid = gv.sd['mnp']+1

    
    #
    #jsave(gv.pd, 'programs') # save programs file
    #gv.sd['nprogs'] = len(gv.pd) # set the length correctly
    return

class auto_program:
    """Load an html page for entering extra wx settings"""
    def __init__(self):
        self.render = web.template.render('templates/', globals={'json':json,'sorted':sorted})
    
    def GET(self):
        try:
        # read data from the file, if it exists
            with io.open(r'./data/wx_settings.json', 'r') as data_file: 
                data = json.load(data_file)
            data_file.close()  
        except IOError:
            return

        return self.render.auto_program(data)

class update_auto_program:
    """Save user input to wx_settings.json file """
    def GET(self):
        qdict=web.input()
        try:
            # read data from the file, if it exists
            with io.open(r'./data/wx_settings.json', 'r') as data_file: 
                data = json.load(data_file)
            data_file.close()  
            data['startTimeHour']=qdict['startTimeHour']
            data['startTimeMin']=qdict['startTimeMin']
            with io.open('./data/wx_settings.json', 'w', encoding='utf-8') as data_file:
                data_file.write(unicode(json.dumps(data, ensure_ascii=False)))

        except IOError:
            return

<<<<<<< HEAD
        raise web.seeother('/auto')
=======
        raise web.seeother('/')
>>>>>>> created auto program module



# call once on load
setAutoProgram()