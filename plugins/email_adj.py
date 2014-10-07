# !/usr/bin/env python
# this plugins send email at google email

from threading import Thread
from random import randint
import json
import time
import os
import sys
import traceback

import web
import gv  # Get access to ospi's settings
from urls import urls  # Get access to ospi's URLs
from ospi import template_render
from webpages import ProtectedPage
from helpers import timestr

from email import Encoders
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText

# Add a new url to open the data entry page.
urls.extend(['/emla', 'plugins.email_adj.settings',
             '/emlj', 'plugins.email_adj.settings_json',
             '/uemla', 'plugins.email_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Email settings', '/emla'])

################################################################################
# Main function loop:                                                          #
################################################################################


class EmailSender(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
        self.status = ''

        self._sleep_time = 0

    def add_status(self, msg):
        if self.status:
            self.status += '\n' + msg
        else:
            self.status = msg
        print msg

    def update(self):
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def try_mail(self, subject, text, attachment=None):
        self.status = ''
        try:
            email(subject, text, attachment)  # send email with attachment from
            self.add_status('Email was sent: ' + text)
        except Exception as err:
            self.add_status('Email was not sent! ' + str(err))

    def run(self):
        time.sleep(randint(3, 10))  # Sleep some time to prevent printing before startup information

        dataeml = get_email_options()  # load data from file
        subject = "Report from ospi"  # Subject in email
        last_rain = 0
        was_running = False

        self.status = ''
        self.add_status('Email plugin is started')

        if dataeml["emllog"] != "off":          # if eml_log send email is enable (on)
            body = ('On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time())) +
                    ': System was powered on.')
            self.try_mail(subject, body, "/home/pi/ospi/data/log.json")

        while True:
            try:
                # send if rain detected
                if dataeml["emlrain"] != "off":             # if eml_rain send email is enable (on)
                    if gv.sd['rs'] != last_rain:            # send email only 1x if  gv.sd rs change
                        last_rain = gv.sd['rs']

                        if gv.sd['rs'] and gv.sd['urs']:    # if rain sensed and use rain sensor
                            body = ('On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time())) +
                                    ': System detected rain.')
                            self.try_mail(subject, body)    # send email without attachments

                if dataeml["emlrun"] != "off":              # if eml_rain send email is enable (on)
                    running = False
                    for b in range(gv.sd['nbrd']):          # Check each station once a second
                        for s in range(8):
                            sid = b * 8 + s  # station index
                            if gv.srvals[sid]:  # if this station is on
                                running = True
                                was_running = True

                    if was_running and not running:
                        was_running = False
                        if gv.lrun[1] == 98:
                            pgr = 'Run-once'
                        elif gv.lrun[1] == 99:
                            pgr = 'Manual'
                        else:
                            pgr = str(gv.lrun[1])

                        dur = str(timestr(gv.lrun[2]))
                        start = time.gmtime(gv.now - gv.lrun[2])

                        body = 'On ' + time.strftime("%d.%m.%Y at %H:%M:%S", time.localtime(time.time())) + \
                               ': System last run: ' + 'Station ' + str(gv.lrun[0]) + \
                               ', Program ' + pgr + \
                               ', Duration ' + dur + \
                               ', Start time ' + time.strftime("%d.%m.%Y at %H:%M:%S", start)

                        self.try_mail(subject, body)     # send email without attachment

                self._sleep(1)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('Email plugin encountered error: ' + err_string)
                self._sleep(60)


checker = EmailSender()

################################################################################
# Helper functions:                                                            #
################################################################################


def get_email_options():
    """Returns the defaults data form file."""
    dataeml = {
        'emlusr': '',
        'emlpwd': '',
        'emladr': '',
        'emllog': 'off',
        'emlrain': 'off',
        'emlrun': 'off',
        'status': checker.status
    }
    try:
        with open('./data/email_adj.json', 'r') as f:  # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in dataeml:
                dataeml[key] = value
    except Exception:
        pass

    return dataeml


def email(subject, text, attach=None):
    """Send email with with attachments"""
    dataeml = get_email_options()
    if dataeml['emlusr'] != '' and dataeml['emlpwd'] != '' and dataeml['emladr'] != '':
        gmail_user = dataeml['emlusr']          # User name
        gmail_name = gv.sd['name']              # OSPi name
        gmail_pwd = dataeml['emlpwd']           # User password
        #--------------
        msg = MIMEMultipart()
        msg['From'] = gmail_name
        msg['To'] = dataeml['emladr']
        msg['Subject'] = subject
        msg.attach(MIMEText(text))
        if attach is not None:              # If insert attachments
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(open(attach, 'rb').read())
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(attach))
            msg.attach(part)
        mailServer = smtplib.SMTP("smtp.gmail.com", 587)
        mailServer.ehlo()
        mailServer.starttls()
        mailServer.ehlo()
        mailServer.login(gmail_user, gmail_pwd)
        mailServer.sendmail(gmail_name, dataeml['emladr'], msg.as_string())   # name + e-mail address in the From: field
        mailServer.close()
    else:
        raise Exception('E-mail plug-in is not properly configured!')

################################################################################
# Web pages:                                                                   #
################################################################################


class settings(ProtectedPage):
    """Load an html page for entering email adjustments."""

    def GET(self):
        return template_render.email_adj(get_email_options())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_email_options())


class update(ProtectedPage):
    """Save user input to email_adj.json file."""

    def GET(self):
        qdict = web.input()
        if 'emllog' not in qdict:
            qdict['emllog'] = 'off'
        if 'emlrain' not in qdict:
            qdict['emlrain'] = 'off'
        if 'emlrun' not in qdict:
            qdict['emlrun'] = 'off'
        with open('./data/email_adj.json', 'w') as f:  # write the settings to file
            json.dump(qdict, f)
        raise web.seeother('/')
