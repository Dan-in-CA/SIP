__author__ = 'Rimco'

from options import options
from programs import programs

import datetime


def combined_schedule(start_time, end_time):

    # Aggregate per station:
    station_schedules = {}
    for program in programs.get():
        if not program.enabled:
            continue

        program_intervals = program.active_intervals(start_time, end_time)

        for station in sorted(program.stations):
            if station not in station_schedules:
                station_schedules[station] = []

            station_schedules[station] += [interval[:] for interval in program_intervals]  # Simple deepcopy

    all_intervals = []
    # Adjust for weather and remove overlap:
    for station, schedule in station_schedules.iteritems():
        for interval in schedule:
            adjustment = 1.0  # FIXME: get (weather) level adjustment
            time_delta = interval[1] - interval[0]
            time_delta = datetime.timedelta(seconds=(time_delta.days * 24 * 3600 + time_delta.seconds) * adjustment)
            interval[1] = interval[0] + time_delta

        last_end = datetime.datetime(2000, 1, 1)
        for interval in schedule:
            if last_end > interval[0]:
                time_delta = last_end - interval[0]
                interval[0] += time_delta
                interval[1] += time_delta
            last_end = interval[1]

            all_intervals.append([station, interval])

    # Make list of entries sorted on time (stable sorted on station #)
    all_intervals.sort(key=lambda inter: inter[1])

    current_usage = 0.0
    current_active = []  # [ [station_index, [start, end] ], ... ]
    max_usage = 1 if options.sequential else 1000000  # FIXME

    # Try to add each interval
    for station, interval in all_intervals:
        usage = 1  # FIXME
        done = False

        while not done:
            # Delete all intervals that have finished
            while current_active:
                if current_active[0][1][1] > interval[0]:
                    break
                current_usage -= 1  # FIXME
                del current_active[0]

            # Check if we can add it now
            if current_usage + usage <= max_usage:
                current_usage += usage
                # Add the newly "activated" station to the active list
                for index in range(len(current_active)):
                    if current_active[index][1][1] > interval[1]:
                        current_active.insert(index, [station, interval])
                        break
                else:
                    current_active.append([station, interval])
                done = True
            else:
                # Shift this interval to next possibility
                next_option = current_active[0][1][1]
                time_to_next = next_option - interval[0]
                interval[0] += time_to_next
                interval[1] += time_to_next

    result = {}
    for station, interval in all_intervals:
        if station not in result:
            result[station] = []
        result[station].append(interval)

    return result
