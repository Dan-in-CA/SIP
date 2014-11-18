#!/usr/bin/env python
'''Pulses a selected circuit with a 2.5 Hz signal for 30 sec
to discover the location of a valve'''
import web
from time import sleep
from web import form
import gv # Get access to ospi's settings
from urls import urls # Get access to ospi's URLs
import gpio_pins as gpio
#urls = ('/pls', 'pulse')
render = web.template.render('templates/')

#app = web.application(urls, globals())

urls.extend(['/pls', 'plugins.pulse_cct.pulse']) 
gv.plugin_menu.append(['Pulse Circuit', '/pls']) # Add this plugin to the home page plugins menu
gv.curCCT=1 # the curent pulse circuit
render = web.template.render('templates/')
pulse_form = form.Form(
    form.Dropdown('CCT', [1,2,3,4,5,6,7,8]),
    form.Button("Trigger"),
    form.Button("Exit")
)
pform = pulse_form()
def chatter(cct):
    gv.srvals = [0]*8 #TODO read how many valves are in service, and which ones
    gpio.set_output() #TODO switch on gpio functions after debugging
    lv = 1
    for cnt in range(150):
        #toggle cct
        gv.srvals[cct] ^= lv
        gpio.set_output()
        sleep(0.2)
    #switch everything off
    gv.srvals = [0]*8
    gpio.set_output()

# define what happens when the index page is called
class pulse:

    def GET(self):
        pform.CCT.value = gv.curCCT
#        print 'Rendered, gv.curCCT is %s' %gv.curCCT
        return render.pulse(pform, "Open Sprinkler")#monthly(levels)


    def POST(self):
        userData = web.input()
#        print userData
        if userData.has_key('Exit'):
            raise web.seeother('/')            
        else:
            gv.curCCT = int(userData['CCT'])
#            print 'Selected Circuit is %s' %gv.curCCT
            chatter(gv.curCCT-1)
            raise web.seeother("/pls")
