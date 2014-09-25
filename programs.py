__author__ = 'Rimco'
from options import options

import datetime


class _Program(object):
    SAVE_EXCLUDE = ['SAVE_EXCLUDE', 'index']

    def __init__(self, programs_instance, index):
        self._programs = programs_instance
        self.schedule = []

        self.name = "Program %02d" % (index+1)
        self.stations = []
        self.enabled = True

        self.modulo = 24*60
        self.manual = False  # Non-repetitive (run-once) if True
        self.start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

        options.load(self, index)

    @property
    def index(self):
        return self._programs.get().index(self)

    def add(self, start_minute, end_minute):
        start_minute %= self.modulo
        end_minute %= self.modulo

        if end_minute < start_minute:
            end_minute += self.modulo

        if end_minute > self.modulo:
            new_entries = [
                [0, end_minute % self.modulo],
                [start_minute, self.modulo]
            ]
        else:
            new_entries = [[start_minute, end_minute]]

        new_schedule = self.schedule[:]

        while new_entries:
            entry = new_entries.pop(0)
            for existing in new_schedule:
                if existing[0] <= entry[0] < existing[1]:
                    entry[0] = existing[1]
                if existing[0] < entry[1] <= existing[1]:
                    entry[1] = existing[0]
                if entry[0] < existing[0] <= existing[1] < entry[1]:
                    new_entries.append([existing[1], entry[1]])
                    entry[1] = existing[0]

                if entry[1] - entry[0] <= 0:
                    break

            if entry[1] - entry[0] > 0:
                new_schedule.append(entry)
                new_schedule.sort(key=lambda ent: ent[0])

        self.schedule = new_schedule

    def is_active(self, date_time):
        time_delta = date_time - self.start
        minute_delta = time_delta.days*24*60 + int(time_delta.seconds/60)

        if self.manual and minute_delta >= self.modulo:
            return False

        current_minute = minute_delta % self.modulo

        result = False
        for entry in self.schedule:
            if entry[0] <= current_minute < entry[1]:
                result = True
                break
            elif entry[0] <= current_minute+self.modulo < entry[1]:
                result = True
                break
            elif entry[0] > current_minute:
                break

        return result

    def active_intervals(self, date_time_start, date_time_end):
        result = []
        start_delta = date_time_start - self.start
        start_minutes = (start_delta.days*24*60 + int(start_delta.seconds/60)) % self.modulo
        current_date_time = date_time_start - datetime.timedelta(minutes=start_minutes,
                                                                 seconds=date_time_start.second,
                                                                 microseconds=date_time_start.microsecond)

        while current_date_time < date_time_end:
            for entry in self.schedule:
                start = current_date_time + datetime.timedelta(minutes=entry[0])
                end = current_date_time + datetime.timedelta(minutes=entry[1])

                if end <= date_time_start:
                    continue

                if start >= date_time_end:
                    break

                result.append({
                    'start': start,
                    'end': end
                })

            if self.manual:
                break

            current_date_time += datetime.timedelta(minutes=self.modulo)

        return result

    def __setattr__(self, key, value):
        try:
            super(_Program, self).__setattr__(key, value)
            if not key.startswith('_') and key not in self.SAVE_EXCLUDE:
                options.save(self, self.index)
        except ValueError:  # No index available yet
            pass


class _Programs(object):
    def __init__(self):
        self._programs = []

        for i in range(options.program_count):
            self._programs.append(_Program(self, i))

    def add_program(self):
        self._programs.append(_Program(self, len(self._programs)))
        options.program_count = len(self._programs)

    def remove_program(self, index):
        if 0 <= index < len(self._programs):
            del self._programs[index]

        for i in range(index, len(self._programs)):
            options.save(self._programs[i], i)  # Save programs using new indices

        options.program_count = len(self._programs)

    def count(self):
        return options.program_count

    def get(self, index=None):
        if index is None:
            result = self._programs[:]
        else:
            result = self._programs[index]
        return result

programs = _Programs()