# !/usr/bin/env python
# -*- coding: utf-8 -*-

# Python 2/3 compatibility imports
from __future__ import print_function
from six.moves import zip
from six.moves import range
try:
    from urllib.request import urlopen, Request
except ImportError:
    from six.moves.urllib.request import urlopen, Request

# standard library imports
import base64
import json
import re
import subprocess
import time

# local module imports
import gv  # Get access to SIP's settings
from helpers import restart
from helpers import report_error
from sip import template_render
from urls import urls  # Get access to SIP's URLs
import web
from webpages import ProtectedPage

installed = []

# Add new url(s).
# fmt: off
urls.extend([
            u"/plugins", u"plugins.plugin_manager.plugins",
            u"/upd-plugins", u"plugins.plugin_manager.update_plugins",
            u"/browse-plugins", u"plugins.plugin_manager.browse_plugins",
            u"/inst-plugins", u"plugins.plugin_manager.install_plugins",
            u"/pmr", u"plugins.plugin_manager.restart_page"
             ])
# fmt: on
# Add this plugin to the plugins menu
gv.plugin_menu.append([_(u"Manage Plugins"), u"/plugins"])


def get_permissions():
    global installed
    try:
        permissions = []
        files = subprocess.check_output([u"ls", u"plugins"])
        files = files.decode(u'utf-8') #  to unicode string
        installed = [f for f in list(files.split(u"\n")) if re.match("[^_].+\.py$", f)]
        pm = installed.index(u"plugin_manager.py")
        del installed[pm]  #  Remove this plugin from list
        for p in installed:
            mod = subprocess.check_output([u"stat", u"-c %a", u"plugins/" + p])
            mod = mod.decode(u'utf-8')
            permissions.append(int(list(mod.strip())[1]) % 2)
        settings = dict(list(zip(installed, permissions)))
        return settings
    except IOError as e:
        report_error(u"get_permissions IOError", e)
        settings = {}
        return settings


def parse_manifest(plugin):
    try:
        with open(u"plugins/manifests/" + plugin + u".manifest") as mf:
            mf_list = mf.readlines()
            sep = [i for i, s in enumerate(mf_list) if u"###" in s][0]
            desc = u"".join(mf_list[:sep]).rstrip()
            f_list = [line.strip() for line in mf_list[int(sep) + 2 :]]
            return (desc, f_list)
    except IOError as e:
        report_error(u"parse_manifest IOError", e)
        return (u"", [])


def get_readme():
    plugs = {}
    try:
        response = urlopen(
            u"https://api.github.com/repos/Dan-in-CA/SIP_plugins/readme"
        )
        data = response.read()
        d = json.loads(data.decode('utf-8'))
        text = base64.b64decode(d[u"content"]).decode(u'utf-8')
        t_list = text.split()
        sep = [i for i, s in enumerate(t_list) if u"***" in s][0]
        plug_list = t_list[sep + 1 :]
        breaks = [i for i, s in enumerate(plug_list) if u"---" in s]


        for i in range(len(breaks)):
            if i < len(breaks) - 1:
                plugs[plug_list[breaks[i] - 1]] = u" ".join(
                    plug_list[breaks[i] + 1 : breaks[i + 1] - 1]
                )
            else:
                plugs[plug_list[breaks[i] - 1]] = u" ".join(plug_list[breaks[i] + 1 :])
    except IOError as e:
        report_error(U"We couldn't get readme file for github", e)

    return plugs


class plugins(ProtectedPage):
    """
    Load an html page for enabling or disabling plugins
    """

    def GET(self):
        settings = get_permissions()
        return template_render.plugins(settings)


class update_plugins(ProtectedPage):
    """
    Change plugin permissions or
    Delete selected plugins
    """

    def GET(self):
        global installed
        qdict = web.input()
        if qdict[u"btnId"] == u"upd":
            for f in installed:
                if f in qdict:
                    command = u"chmod g+x plugins/" + f
                    subprocess.call(command.split())
                else:
                    command = u"chmod g-x plugins/" + f
                    subprocess.call(command.split())
                time.sleep(1)
            raise web.seeother(u"/restart")
        if qdict[u"btnId"] == u"del":
            del_list = []
            for k in list(qdict.keys()):  # Get plugins to delete
                if k[:3] == u"del":
                    del_list.append(k[4:])
            for p in del_list:  # get files to delete for each plugin in list
                name = p.split(u".")[0]
                desc, files = parse_manifest(name)
                for f in files:
                    victim = f.split()
                    if victim[0][-3:] == u".py":
                        b_code = victim[0].replace(u".py", u".pyc")
                        command = u"rm -f " + victim[1] + u"/" + b_code
                        subprocess.call(command.split())
                    command = u"rm -f " + victim[1] + u"/" + victim[0]
                    subprocess.call(command.split())
            raise web.seeother(u"/restart")


class browse_plugins(ProtectedPage):
    """
    Load an html page for choosing and installing plugins.
    """

    def GET(self):
        plug_dict = get_readme()
        return template_render.plugins_repo(plug_dict)


class install_plugins(ProtectedPage):
    """
    Install selected plugins from GitHub
    """

    def GET(self):
        qdict = web.input()
        for p in list(qdict.keys()):  # Get plugins to install
            #           https://raw.github.com/<username>/<repo>/<branch>/some_directory/file.r #### Example
            response = urlopen(
                u"https://raw.github.com/Dan-in-CA/SIP_plugins/master/"
                + p
                + u"/"
                + p
                + u".manifest"
            )
            data = response.readlines()
            data = [i.decode('utf-8') for i in data]
            sep = [i for i, s in enumerate(data) if u"###" in s][0]
            file_list = [line.strip() for line in data[int(sep) + 2 :]]
            short_list = [
                x for x in file_list if not u"data" in x and not u"manifest" in x
            ]
            with open(u"plugins/manifests/" + p + u".manifest", "w") as new_mf:
                new_mf.writelines(data)
            for f in short_list:
                pf = f.split()
                response = urlopen(
                    u"https://raw.github.com/Dan-in-CA/SIP_plugins/master/"
                    + p
                    + u"/"
                    + pf[0]
                )
                f_data = response.read()
                try:
                    f_data = f_data.decode('utf-8')
                    with open(pf[1] + u"/" + pf[0], "w") as next_file:
                        next_file.write(f_data)
                except UnicodeDecodeError:
                    with open(pf[1] + u"/" + pf[0], "wb") as next_file:
                        next_file.write(f_data)
        raise web.seeother(u"/plugins")

    class restart_page(ProtectedPage):
        """Restart system."""

        def GET(self):
            restart(2, True)
            return template_render.home()
