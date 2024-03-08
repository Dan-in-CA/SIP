# !/usr/bin/env python
# -*- coding: utf-8 -*-

# standard library imports
import ast
import base64
import json
import pathlib
import re
import requests
import subprocess
import time

# local module imports
import gv  # Get access to SIP's settings
from helpers import restart
from sip import template_render
from urls import urls  # Get access to SIP's URLs
import web
from webpages import ProtectedPage

installed = []

# Add new url(s).
# fmt: off
urls.extend([
            "/plugins", "plugins.plugin_manager.plugins",
            "/upd-plugins", "plugins.plugin_manager.update_plugins",
            "/browse-plugins", "plugins.plugin_manager.browse_plugins",
            "/inst-plugins", "plugins.plugin_manager.install_plugins",
            "/pmr", "plugins.plugin_manager.restart_page"
             ])
# fmt: on
# Add this plugin to the plugins menu
gv.plugin_menu.append([_("Manage Plugins"), "/plugins"])

def get_permissions():
    global installed
    try:
        permissions = []
        files = subprocess.check_output(["ls", "plugins"])
        files = files.decode('utf-8') #  to unicode string
        installed = [f for f in list(files.split("\n")) if re.match("[^_].+\.py$", f)]
        pm = installed.index("plugin_manager.py")
        del installed[pm]  #  Remove this plugin from list
        for p in installed:
            mod = subprocess.check_output(["stat", "-c %a", "plugins/" + p])
            mod = mod.decode('utf-8')
            permissions.append(int(list(mod.strip())[1]) % 2)
        settings = dict(list(zip(installed, permissions)))
        return settings
    except IOError as e:
        settings = {}
        return settings


def parse_manifest(plugin):
    try:
        with open("plugins/manifests/" + plugin + ".manifest") as mf:
            mf_list = mf.readlines()
            sep = [i for i, s in enumerate(mf_list) if "###" in s][0]
            desc = "".join(mf_list[:sep]).rstrip()
            f_list = [line.strip() for line in mf_list[int(sep) + 2 :]]
            return (desc, f_list)
    except IOError as e:
        return ("", [])


def get_readme():
    plugs = {}
    try:
        resp = requests.get("https://api.github.com/repos/Dan-in-CA/SIP_plugins/readme")
        txt = resp.text
        data = ast.literal_eval(txt)
        text = base64.b64decode(data["content"]).decode('utf-8')
        t_list = text.split()        
        sep = [i for i, s in enumerate(t_list) if "***" in s][0]
        plug_list = t_list[sep + 1 :]
        breaks = [i for i, s in enumerate(plug_list) if "---" in s]
        for i in range(len(breaks)):
            if i < len(breaks) - 1:
                plugs[plug_list[breaks[i] - 1]] = " ".join(
                    plug_list[breaks[i] + 1 : breaks[i + 1] - 1]
                )
            else:
                plugs[plug_list[breaks[i] - 1]] = " ".join(plug_list[breaks[i] + 1 :])
    except IOError as e:
        print("We couldn't get readme file for github", e)
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
        if qdict["btnId"] == "upd":
            for f in installed:
                if f in qdict:
                    command = "chmod g+x plugins/" + f
                    subprocess.call(command.split())
                else:
                    command = "chmod g-x plugins/" + f
                    subprocess.call(command.split())
            raise web.seeother("/restart")
        if qdict["btnId"] == "del":
            del_list = []
            for k in list(qdict.keys()):  # Get plugins to delete
                if k[:3] == "del":
                    del_list.append(k[4:])
            for p in del_list:  # get files to delete for each plugin in list
                name = p.split(".")[0]
                desc, files = parse_manifest(name)
                for f in files:
                    victim = f.split()
                    if victim[0][-3:] == ".py":
                        b_code = victim[0].replace(".py", ".pyc")
                        command = "rm -f " + victim[1] + "/" + b_code
                        subprocess.call(command.split())
                    command = "rm -f " + victim[1] + "/" + victim[0]
                    subprocess.call(command.split())
            raise web.seeother("/restart")


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
        """Get plugins to install"""
        qdict = web.input()
        for p in list(qdict.keys()):
            url = f"https://raw.github.com/Dan-in-CA/SIP_plugins/master/{p}/{p}.manifest"
            resp = requests.get(url)
            data = resp.text.splitlines()
            sep = [i for i, s in enumerate(data) if "###" in s][0]
            file_list = [line.strip() for line in data[int(sep) + 2 :]]
            short_list = []
            for line in file_list:
                parts = line.split()
                if (not parts[1] == "data"
                   and not parts[1] == "plugins/manifests"
                    ):
                    short_list.append(line)
            
            with open(f"plugins/manifests/{p}.manifest", "w") as new_mf:
                new_mf.writelines(resp.text)
            for f in short_list:
                pf = f.split()
                resp = requests.get(f"https://raw.github.com/Dan-in-CA/SIP_plugins/master/{p}/{pf[0]}")
                try:
                    f_data = resp.text
                    with open(f"{pf[1]}/{pf[0]}", "w") as next_file:
                        next_file.write(f_data)                        
                except FileNotFoundError: # If a needed sub-directory is missing
                    sub = pf[1].split("/")
                    pathlib.Path("plugins/" + sub[1]).mkdir(exist_ok=True) 
                    with open(pf[1] + "/" + pf[0], "w") as next_file:
                        next_file.write(f_data)                                                  
                except UnicodeDecodeError:
                    with open(pf[1] + "/" + pf[0], "wb") as next_file:
                        next_file.write(f_data)
        raise web.seeother("/plugins")

    class restart_page(ProtectedPage):
        """Restart sip."""
        def GET(self):
            restart(2)
