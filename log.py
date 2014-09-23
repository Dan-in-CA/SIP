from options import options

import logging
import time

__author__ = 'Rimco'

EVENT_FILE = './data/events.log'
EVENT_FORMAT = "%(asctime)s [%(levelname)s %(event_type)s] %(filename)s:%(lineno)d: %(message)s"
RUN_FORMAT = "%(asctime)s [Run] Program %(program)d - Station %(station)d: From %(start)s to %(end)s"


class Log(logging.Handler):
    SAVE_EXCLUDE = ['SAVE_EXCLUDE', 'level', 'formatter']

    def __init__(self):
        super(Log, self).__init__()
        self._log = {
            'Run': []
        }

        options.load(self)

    # We provide the runs property to get it saved to disk (limited by options setting)
    # Internally we keep track of more events to ensure we have enough entries to know what we already did
    @property
    def runs(self):
        result = []
        for entry in self._log['Run']:
            result.append(entry)
            if 0 < options.log_entries <= len(result):
                break

        return result

    @runs.setter
    def runs(self, value):
        self._log['Run'] = value.copy()

    @property
    def level(self):
        return logging.DEBUG if options.debug_log else logging.INFO

    @level.setter
    def level(self, value):
        pass  # Override level using options

    def _file_log(self, msg):
        if options.debug_log:
            with open(EVENT_FILE, 'a') as fh:
                fh.write(msg + '\n')

    def _prune(self, event_type):
        range_end = len(self._log.setdefault(event_type, []))
        if event_type == 'Run':
            if options.log_entries == 0:
                return  # We may not prune
            else:
                range_end -= options.log_entries  # Keep at least the last XX entries

        current_time = time.localtime()
        for index in reversed(range(0, range_end)):
            if current_time - self._log[event_type][index]['time'] > 2*24*3600:  # Older than two days
                del self._log[event_type][index]

    def log_run(self, interval):
        self._log['Run'].append({
            'time': time.localtime(),
            'level': logging.INFO,
            'data': interval
        })

        fmt_dict = interval.copy()
        fmt_dict['asctime'] = time.strftime("%Y-%m-%d %H:%M:%S") + ',000'
        fmt_dict['start'] = interval['start'].strftime("%Y-%m-%d %H:%M:%S")
        fmt_dict['end'] = interval['end'].strftime("%Y-%m-%d %H:%M:%S")

        self._file_log(RUN_FORMAT % fmt_dict)
        self._prune('Run')

    def log_event(self, event_type, message, level=logging.INFO):
        if level >= self.level:
            if event_type not in self._log:
                self._log[event_type] = []

            self._log[event_type].append({
                'time': time.localtime(),
                'level': level,
                'data': message
            })
            self._file_log(message)
            self._prune(event_type)

    def clear(self, event_type):
        self._log[event_type] = []

    def events(self, event_type):
        return [evt['data'] for evt in self._log.setdefault(event_type, [])]

    def emit(self, record):
        if not hasattr(record, 'event_type'):
            record.event_type = 'Event'

        txt = self.format(record) if options.debug_log else record.getMessage()
        self.log_event(record.event_type, txt, record.levelno)

log = Log()
log.setFormatter(logging.Formatter(EVENT_FORMAT))

_logger = logging.getLogger()
_logger.setLevel(logging.DEBUG)
_logger.addHandler(log)