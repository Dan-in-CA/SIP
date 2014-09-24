import json
import shelve
from threading import Timer

__author__ = 'Rimco'

OPTIONS_FILE = './data/options.db'


class _Options(object):
    # Using an array to preserve order
    OPTIONS = [
        #######################################################################
        # System ##############################################################
        {
            "key": "name",
            "name": "System name",
            "default": "OpenSprinkler Pi",
            "help": "Unique name of this OpenSprinkler system.",
            "category": "System"
        },
        {
            "key": "theme",
            "name": "System theme",
            "default": "basic",
            "options": ["basic", "original"],
            "help": "Determines the look of the GUI.",
            "category": "System"
        },
        {
            "key": "location",
            "name": "Location",
            "default": "",
            "help": "City name or zip code. Use comma or + in place of space.",
            "category": "System"
        },
        {
            "key": "time_format",
            "name": "24-hour clock",
            "default": True,
            "help": "Display times in 24 hour format (as opposed to AM/PM style.)",
            "category": "System"
        },
        {
            "key": "web_port",
            "name": "HTTP port",
            "default": 8080,
            "help": "HTTP port (effective after reboot.)",
            "category": "System"
        },

        #######################################################################
        # Security ############################################################
        {
            "key": "no_password",
            "name": "Disable security",
            "default": False,
            "help": "Allow anonymous users to access the system without a password.",
            "category": "Security"
        },

        #######################################################################
        # Station Handling ####################################################
        {
            "key": "sequential",
            "name": "Sequential",
            "default": True,
            "help": "Sequential or concurrent running mode.",
            "category": "Station Handling"
        },
        {
            "key": "output_count",
            "name": "Number of outputs",
            "default": 8,
            "help": "The number of outputs available (8 + 8*extensions)",
            "category": "Station Handling"
        },
        {
            "key": "station_delay",
            "name": "Station delay",
            "default": 0,
            "help": "Station delay time (in seconds), between 0 and 240.",
            "category": "Station Handling"
        },

        #######################################################################
        # Configure Master ####################################################
        {
            "key": "master_on_delay",
            "name": "Master on adjust",
            "default": 0,
            "help": "Master on delay (in seconds), between +0 and +60.",
            "category": "Configure Master"
        },
        {
            "key": "master_off_delay",
            "name": "Master off adjust",
            "default": 0,
            "help": "Master off delay (in seconds), between -60 and +60.",
            "category": "Configure Master"
        },

        #######################################################################
        # Rain Sensor #########################################################
        {
            "key": "rain_sensor_enabled",
            "name": "Use rain sensor",
            "default": False,
            "help": "Use rain sensor.",
            "category": "Rain Sensor"
        },
        {
            "key": "rain_sensor_no",
            "name": "Normally open",
            "default": True,
            "help": "Rain sensor default.",
            "category": "Rain Sensor"
        },

        #######################################################################
        # Logging #############################################################
        {
            "key": "run_log",
            "name": "Enable run logging",
            "default": False,
            "help": "Log all runs - note that repetitive writing to an SD card can shorten its lifespan.",
            "category": "Logging"
        },
        {
            "key": "run_entries",
            "name": "Max run entries",
            "default": 100,
            "help": "Number of run entries to save to disk, 0=no limit.",
            "category": "Logging"
        },
        {
            "key": "debug_log",
            "name": "Enable debug logging",
            "default": False,
            "help": "Log all internal events (for debugging purposes).",
            "category": "Logging"
        },


        #######################################################################
        # Not in Options page as-is ###########################################
        {
            "key": "system_enabled",
            "name": "Enable system",
            "default": True,
        },
        {
            "key": "manual_mode",
            "name": "Manual operation",
            "default": False,
        },


        {
            "key": "password_hash",
            "name": "Current password hash",
            "default": "",
        },
        {
            "key": "password_salt",
            "name": "Current password salt",
            "default": "",
        },

        {
            "key": "program_count",
            "name": "The number of programs",
            "default": 0,
        },

        {
            "key": "logged_runs",
            "name": "The runs that have been logged",
            "default": []
        }

    ]

    def __init__(self):
        self._values = {}
        self._write_timer = None

        for info in self.OPTIONS:
            self._values[info["key"]] = info["default"]

        try:
            db = shelve.open(OPTIONS_FILE)
            self._values.update(db)
            db.close()
        except Exception:
            pass

    def __str__(self):
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
        return pp.pformat(self._values)

    def __getattr__(self, item):
        if item.startswith('_'):
            result = super(_Options, self).__getattribute__(item)
        else:
            result = self._values[item]
        return result

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super(_Options, self).__setattr__(key, value)
        else:
            self._values[key] = value

            # Only write after 1 second without any more changes
            if self._write_timer is not None:
                self._write_timer.cancel()
            self._write_timer = Timer(1.0, self._write)
            self._write_timer.start()

    def _write(self):
        ''''This function saves the current data to disk. Use a timer to limit the call rate.'''
        db = shelve.open(OPTIONS_FILE)
        db.update(self._values)
        db.close()

    def get_categories(self):
        result = []
        for info in self.OPTIONS:
            if "category" in info and info["category"] not in result:
                result.append(info["category"])
        return result

    def get_options(self, category=None):
        if category is None:
            result = [opt["key"] for opt in self.OPTIONS]
        else:
            result = []
            for info in self.OPTIONS:
                if "category" in info and info["category"] == category:
                    result.append(info["key"])
        return result

    def get_info(self, option):
        return self.OPTIONS[option]

    def load(self, obj, key=""):
        cls = 'Cls' + type(obj).__name__
        try:
            values = getattr(self, cls + str(key))
            for name, value in values.iteritems():
                setattr(obj, name, value)
        except KeyError:
            pass

    def save(self, obj, key=""):
        cls = 'Cls' + type(obj).__name__
        values = {}
        exclude = obj.SAVE_EXCLUDE if hasattr(obj, 'SAVE_EXCLUDE') else []
        for attr in [att for att in dir(obj) if not att.startswith('_') and att not in exclude]:
            if not hasattr(getattr(obj, attr), '__call__'):
                values[attr] = getattr(obj, attr)
        setattr(self, cls + str(key), values)

options = _Options()