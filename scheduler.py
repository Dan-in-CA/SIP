from stations import stations

__author__ = 'Rimco'

from options import options
from programs import programs
from log import log

import datetime


def predicted_schedule(start_time, end_time):
    """Determines all schedules for the given time range.
    To calculate what should currently be active, a start time of some time (a day) ago should be used.
    The current_active list should contain intervals as returned by this function.
    skip_uids is a list with uids that should not be returned. For example, if they already have been executed."""

    ADJUSTMENT = 1.0  # FIXME: get (weather) level adjustment
    MAX_USAGE = 1.01 if options.sequential else 1000000  # FIXME

    skip_uids = [entry['uid'] for entry in log.finished_runs()]
    current_active = log.active_runs()

    current_usage = 0.0
    for active in current_active:
        current_usage += active['usage']
        if active['uid'] not in skip_uids:
            skip_uids.append(active['uid'])

    # Aggregate per station:
    station_schedules = {}
    for p_index, program in enumerate(programs.get()):
        if not program.enabled:
            continue

        program_intervals = program.active_intervals(start_time, end_time)

        for station in sorted(program.stations):
            if station not in station_schedules:
                station_schedules[station] = []

            for interval in program_intervals:
                new_schedule = {
                    'program': p_index,
                    'start': interval['start'],
                    'end': interval['end'],
                    'uid': '%s-%d-%d' % (str(interval['start']), p_index, station),
                    'usage': 1.0  # FIXME
                }
                if new_schedule['uid'] not in skip_uids:
                    station_schedules[station].append(new_schedule)

    all_intervals = []
    # Adjust for weather and remove overlap:
    for station, schedule in station_schedules.iteritems():
        for interval in schedule:
            time_delta = interval['end'] - interval['start']
            time_delta = datetime.timedelta(seconds=(time_delta.days * 24 * 3600 + time_delta.seconds) * ADJUSTMENT)
            interval['end'] = interval['start'] + time_delta
            interval['adjustment'] = ADJUSTMENT

        last_end = datetime.datetime(2000, 1, 1)
        for interval in schedule:
            if last_end > interval['start']:
                time_delta = last_end - interval['start']
                interval['start'] += time_delta
                interval['end'] += time_delta
            last_end = interval['end']

            new_interval = {
                'station': station
            }
            new_interval.update(interval)

            all_intervals.append(new_interval)

    # Make list of entries sorted on time (stable sorted on station #)
    all_intervals.sort(key=lambda inter: inter['start'])

    # Try to add each interval
    for interval in all_intervals:
        done = False

        while not done:
            # Delete all intervals that have finished
            while current_active:
                if current_active[0]['end'] > interval['start']:
                    break
                current_usage -= current_active[0]['usage']
                del current_active[0]

            # Check if we can add it now
            if current_usage + interval['usage'] <= MAX_USAGE:
                current_usage += interval['usage']
                # Add the newly "activated" station to the active list
                for index in range(len(current_active)):
                    if current_active[index]['end'] > interval['end']:
                        current_active.insert(index, interval)
                        break
                else:
                    current_active.append(interval)
                done = True
            else:
                # Shift this interval to next possibility
                next_option = current_active[0]['end'] + datetime.timedelta(seconds=options.station_delay)
                time_to_next = next_option - interval['start']
                interval['start'] += time_to_next
                interval['end'] += time_to_next

    all_intervals.sort(key=lambda inter: inter['start'])

    return all_intervals


def combined_schedule(start_time, end_time):
    current_time = datetime.datetime.now()
    if current_time < start_time:
        result = predicted_schedule(start_time, end_time)
    elif current_time > end_time:
        result = []
        for entry in log.finished_runs():
            if start_time <= entry['start'] <= end_time or start_time <= entry['end'] <= end_time:
                result.append(entry)
    else:
        result = log.finished_runs()
        result += log.active_runs()
        predicted = predicted_schedule(start_time, end_time)
        result += [entry for entry in predicted if current_time <= entry['start'] <= end_time]

    return result


def check_schedule():
    if options.system_enabled and not options.manual_mode:
        current_time = datetime.datetime.now()

        active = log.active_runs()
        for entry in active:
            if entry['end'] <= current_time:
                log.finish_run(entry)
                stations.deactivate(entry['station'])

        check_start = current_time - datetime.timedelta(days=1)
        check_end = current_time + datetime.timedelta(days=1)
        schedule = predicted_schedule(check_start, check_end)
        for entry in schedule:
            if entry['start'] <= current_time < entry['end']:
                log.start_run(entry)
                stations.activate(entry['station'])

        if stations.master is not None:
            master_on = False

            # It's easy if we don't have to use delays:
            if options.master_on_delay == options.master_off_delay == 0:
                active = log.active_runs()

                for entry in active:
                    if stations.get(entry['station']).activate_master:
                        master_on = True
                        break

            else:
                active = combined_schedule(check_start, check_end, current_time)
                for entry in active:
                    if stations.get(entry['station']).activate_master:
                        if entry['start'] + datetime.timedelta(seconds=options.master_on_delay) \
                                <= current_time < \
                                entry['end'] + datetime.timedelta(seconds=options.master_off_delay):
                            master_on = True
                            break

            master_station = stations.get(stations.master)

            if master_on != master_station.active:
                master_station.active = master_on
