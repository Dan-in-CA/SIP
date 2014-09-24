import datetime
from options import options

import logging
import time

__author__ = 'Rimco'

EVENT_FILE = './data/events.log'
EVENT_FORMAT = "%(asctime)s [%(levelname)s %(event_type)s] %(filename)s:%(lineno)d: %(message)s"
RUN_START_FORMAT = "%(asctime)s [START  Run] Program %(program)d - Station %(station)d: From %(start)s to %(end)s"
RUN_FINISH_FORMAT = "%(asctime)s [FINISH Run] Program %(program)d - Station %(station)d: From %(start)s to %(end)s"


class _Log(logging.Handler):
    def __init__(self):
        super(_Log, self).__init__()
        self._log = {
            'Run': options.logged_runs[:]
        }

        # Remove old entries:
        self._prune('Run')

    @property
    def level(self):
        return logging.DEBUG if options.debug_log else logging.INFO

    @level.setter
    def level(self, value):
        pass  # Override level using options

    def _save_log(self, msg):
        result = []
        for entry in self._log['Run']:
            result.append(entry)
            if 0 < options.run_entries <= len(result):
                break
        options.logged_runs = result

        if options.debug_log:
            with open(EVENT_FILE, 'a') as fh:
                fh.write(msg + '\n')

    def _prune(self, event_type):
        if event_type not in self._log or (event_type == 'Run' and options.run_entries == 0):
            return  # We cannot prune

        current_time = datetime.datetime.now()
        while len(self._log[event_type]) > options.run_entries and \
                current_time - self._log[event_type][0]['time'] > datetime.timedelta(days=2):
            del self._log[event_type][0]

    def start_run(self, interval):
        """Indicates a certain run has been started. The start time will be updated."""

        # Update time with current time
        interval = interval.copy()
        interval['start'] = datetime.datetime.now()
        interval['active'] = True

        self._log['Run'].append({
            'time': datetime.datetime.now(),
            'level': logging.INFO,
            'data': interval
        })

        fmt_dict = interval.copy()
        fmt_dict['asctime'] = time.strftime("%Y-%m-%d %H:%M:%S") + ',000'
        fmt_dict['start'] = fmt_dict['start'].strftime("%Y-%m-%d %H:%M:%S")
        fmt_dict['end'] = fmt_dict['end'].strftime("%Y-%m-%d %H:%M:%S")

        self._save_log(RUN_START_FORMAT % fmt_dict)
        self._prune('Run')

    def finish_run(self, interval):
        """Indicates a certain run has been stopped. Use interval=None to stop all active runs.
        The stop time(s) will be updated with the current time."""
        if isinstance(interval, str) or interval is None:
            uid = interval
        elif isinstance(interval, dict) and 'uid' in interval:
            uid = interval['uid']
        else:
            raise ValueError

        for entry in self._log['Run']:
            if (uid is None or entry['data']['uid'] == uid) and entry['data']['active']:
                entry['data']['end'] = datetime.datetime.now()
                entry['data']['active'] = False

                fmt_dict = entry['data'].copy()
                fmt_dict['asctime'] = time.strftime("%Y-%m-%d %H:%M:%S") + ',000'
                fmt_dict['start'] = fmt_dict['start'].strftime("%Y-%m-%d %H:%M:%S")
                fmt_dict['end'] = fmt_dict['end'].strftime("%Y-%m-%d %H:%M:%S")

                self._save_log(RUN_FINISH_FORMAT % fmt_dict)
                if uid is not None:
                    break

    def active_runs(self):
        result = [run['data'].copy() for run in self._log['Run'] if run['data']['active']]
        for entry in result:
            entry['end'] = datetime.datetime.now()
        return result

    def finished_runs(self):
        return [run['data'].copy() for run in self._log['Run'] if not run['data']['active']]

    def log_event(self, event_type, message, level=logging.INFO):
        if level >= self.level:
            if event_type not in self._log:
                self._log[event_type] = []

            self._log[event_type].append({
                'time': datetime.datetime.now(),
                'level': level,
                'data': message
            })
            self._save_log(message)
            self._prune(event_type)

    def clear(self, event_type):
        self._log[event_type] = []

    def event_types(self):
        return self._log.keys()

    def events(self, event_type):
        return [evt['data'] for evt in self._log.setdefault(event_type, [])]

    def emit(self, record):
        if not hasattr(record, 'event_type'):
            record.event_type = 'Event'

        txt = self.format(record) if options.debug_log else record.getMessage()
        self.log_event(record.event_type, txt, record.levelno)

log = _Log()
log.setFormatter(logging.Formatter(EVENT_FORMAT))

_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)
_logger.addHandler(log)