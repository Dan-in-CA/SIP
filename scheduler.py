# # Program Scheduler

# This module is responsible for managing the scheduling of programs and resulting
# stations activity in the SIP system. From program data in gv.pd[], it maintains
# a list of running and upcoming program periods, which are then used to generate a
# list of upcoming station periods. The scheduler ensures that station periods
# are applied on time to the running stations list (gv.rs[]), allowing for
# efficient management of irrigation schedules in the timing_loop().

# Program schedules are initialized for the current day on startup and new day
# events and updated by signal events received from the main SIP code. These
# events include new day, program addition, modification, deletion, and toggling.

# Schedule execution is triggered by the timing_loop() in sip.py, which calls
# the prog_station_sched_run() function to process the program and station
# schedules. Execution is conditioned by the system being enabled and not in
# manual mode.

# Program periods are defined by their start and stop times, program index,
# and program cycle number. Program cycle is the occurrence number starting
# at 1 of recurring program. Non recurring programs have a single period
# with cycle number 1. Station periods are defined by their start and stop times,
# station index, program index, and cycle number. The scheduler uses these sorted
# periods lists to determine when to activate or deactivate stations based on the
# defined periods.

# The program periods are stored in _prog_sched_list[], while the station
# periods are stored in _station_sched_list[]. The scheduler uses a lock
# (_prog_station_sched_lock) to synchronize access to these lists, ensuring
# thread safety when adding, removing, or updating schedules. These lists
# and the lock are local variables to this module and should not be accessed
# outside of this module.
# 

# standard library imports
import time
from datetime import datetime, timedelta
from datetime import time as d_time
from operator import itemgetter
from threading import RLock

# local module imports
import gv
from blinker import signal
from helpers import (
    days_since_epoch,
    plugin_adjustment,
    report_station_scheduled,
    run_schedule_completed,
    station_stop_on_rain,
)

#############################
# Global variables
#

local_tz = datetime.now().astimezone().tzinfo


#############################
# Local variables
#

# program and station schedule lists
_prog_sched_list = []
_station_sched_list = []

# Next time for the program or station scheduler to run
_prog_station_sched_next_time = None

# Lock for synchronizing access to the program and station schedule lists
_prog_station_sched_lock = RLock()


##############################
# Local helper functions
#
# TODO: Some functions could be moved to helpers.py for reusability.


def prog_data_match_day(prog: dict, daytime_s: int) -> bool:
    """
    Test if a program is set to run on a specific calendar date in seconds
    """
    daytime_t = time.localtime(daytime_s)  # time as time struct.
    if prog["type"] == "interval":
        if (days_since_epoch() % prog["interval_base_day"]) != prog["day_mask"]:
            return False
    else:  # Weekday program
        if not prog["day_mask"] - 128 & 1 << daytime_t.tm_wday:
            return False
        if prog["type"] == "evendays" and daytime_t.tm_mday % 2 != 0:
            return False
        if prog["type"] == "odddays" and (
            daytime_t.tm_mday == 31
            or (daytime_t.tm_mon == 2 and daytime_t.tm_mday == 29)
            or daytime_t.tm_mday % 2 != 1
        ):
            return False
    return True


def prog_cycle_duration(prog: dict) -> int:
    """
    Calculate program recurring cycle duration in seconds
    """
    if gv.sd["seq"]:  # sequential
        if gv.sd["idd"]:
            return sum(prog["duration_sec"])
        else:
            s_count = 0
            for m in prog["station_mask"]:
                s_count += (m).bit_count()
            return s_count * prog["duration_sec"][0]
    else:  # concurrent
        if gv.sd["idd"]:
            return max(prog["duration_sec"])
        else:
            return prog["duration_sec"][0]


def running_station_program_is_running(pid: int) -> bool:
    """
    Returns True if a program (pid) is in the running schedule (gv.rs[]).
    """
    pnum = pid + 1
    for sid in range(len(gv.rs)):
        if gv.rs[sid][3] == pnum:
            return True
    return False


def date_str(date: int) -> str:
    """
    Convert timestamp (sec since epoch) to date and time string YYY:MM:DD HH:MM:SS
    Date and time use system local timezone (local_tz)
    """
    return datetime.fromtimestamp(date, tz=local_tz).strftime("%Y:%m:%d %H:%M:%S")


def dur_str(dur: int) -> str:
    """
    Convert duration in seconds to HH:MM:SS
    """
    minutes, s = divmod(dur, 60)
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def system_enabled_in_auto_mode() -> bool:
    """
    Returns True if the system is enabled and not in manual mode.
    """
    return gv.sd["en"] and not gv.sd["mm"]


def prog_sched_str(period) -> str:
    """
    Convert program schedule period, with duration, to comma separated string values
    Used for exporting program schedule to csv file

    Order: start, stop, duration, pnum, program cycle
    """
    start, stop, pnum, cycle = period
    duration = stop - start
    return (
        f"{date_str(start)}, {date_str(stop)}, {dur_str(duration)}, {pnum}, {cycle}\n"
    )


def prog_sched_list_to_csv_file(filename: str) -> None:
    """
    Export all program schedules on file in csv format
    Used for debugging and testing purposes
    """

    with open(filename, "w", encoding="utf-8") as file:
        header = "start, stop, duration, pnum, cycle\n"
        file.write(header)

        file.writelines(prog_sched_str(period) for period in _prog_sched_list)


def station_sched_str(period) -> str:
    """
    Convert station period, adding duration, to comma separated string values
    Order: start, stop, duration, sid, pnum, program cycle
    """
    start, stop, sid, pnum, cycle = period
    duration = stop - start
    return f"{date_str(start)}, {date_str(stop)}, {dur_str(duration)}, {sid}, {pnum}, {cycle}\n"


def station_sched_list_to_file(filename: str) -> None:
    """
    Export station schedule to file in csv format
    Used for debugging and testing purposes
    """

    with open(filename, "w", encoding="utf-8") as file:
        header = "start, stop, duration, sid, pnum, cycle\n"
        file.write(header)

        file.writelines(station_sched_str(period) for period in _station_sched_list)


# ###########################
# Signal events receiver functions
#


def prog_sched_on_new_day(name: str) -> None:
    """
    Re-schedule all programs on new day or system (re)start.
    """
    prog_station_sched_stop()
    prog_sched_add_program()
    # Debug
    # filename = f"./data/prog_sched_{datetime.now(tz=local_tz).strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    # prog_sched_save_to_file(filename)
    prog_station_sched_restart()


sch_new_day = signal("new_day")
sch_new_day.connect(prog_sched_on_new_day)


def prog_sched_on_program_added(name: str, pid: int) -> None:
    """
    Re-schedule on program added.
    """
    prog_station_sched_stop()
    prog_sched_add_program(pid)
    prog_station_sched_start()


sch_program_added = signal("program_added")
sch_program_added.connect(prog_sched_on_program_added)


def prog_sched_on_program_change(name: str, pid: int) -> None:
    """
    Re-schedule on program change.
    """
    prog_station_sched_stop()
    prog_sched_remove_program(pid)
    prog_sched_add_program(pid)
    prog_station_sched_start()


sch_program_change = signal("program_change")
sch_program_change.connect(prog_sched_on_program_change)


def prog_sched_on_program_deleted(name: str, pid: int) -> None:
    """
    Re-schedule on program deleted.
    """
    prog_station_sched_stop()
    # multiple program pid could have changed - forced to update all program schedules with new pid
    prog_sched_remove_program()
    prog_sched_add_program()

    prog_station_sched_start()


sch_program_deleted = signal("program_deleted")
sch_program_deleted.connect(prog_sched_on_program_deleted)


def prog_sched_on_program_deleted_all(name: str) -> None:
    """
    Re-schedule on all program deleted.
    """
    prog_station_sched_stop()
    prog_and_station_sched_remove_running_program()


sch_program_deleted = signal("program_deleted_all")
sch_program_deleted.connect(prog_sched_on_program_deleted_all)


def prog_sched_on_program_toggled(name: str, pid: int, state: bool) -> None:
    """
    Re-schedule on program toggled (enabled / disabled).
    """
    prog_station_sched_stop()
    if state:
        prog_sched_add_program(pid)  # Enabled
    else:
        prog_sched_remove_program(pid)  # Disabled
    prog_station_sched_start()


sch_program_toggled = signal("program_toggled")
sch_program_toggled.connect(prog_sched_on_program_toggled)


def prog_sched_on_value_change(name, values=None, **kw):
    """
    System Value Change (Main Webpage Settings)
    """
    if "en" in values:
        if values["en"]:  # System enabled
            prog_station_sched_stop()
            prog_sched_add_program()
            prog_station_sched_start()
        else:  # System disabled
            prog_station_sched_stop()
            prog_sched_remove_program()
        return
    if "mm" in values:
        if values["mm"]:  # Manual Mode
            prog_station_sched_stop()
            prog_sched_remove_program()
        else:  # Auto mode
            prog_station_sched_stop()
            prog_sched_add_program()
            prog_station_sched_start()
        return

    if "wl" in values:  # Water Level
        prog_station_sched_stop()
        prog_sched_remove_program()
        prog_sched_add_program()
        prog_station_sched_start()
        return


sch_value_change = signal("value_change")
sch_value_change.connect(prog_sched_on_value_change)


def prog_sched_rain_delay_change(name, **kw):
    """
    Rain delay timer changed (Main Webpage Settings)
    """
    if gv.sd["rd"]:  # Stop when rain delay is active
        prog_station_sched_stop()
        prog_sched_remove_program()
    else:  # Restart when rain delay is cleared
        prog_station_sched_stop()
        prog_sched_add_program()
        prog_station_sched_start()


sch_rain_delay_change = signal("rain_delay_change")
sch_rain_delay_change.connect(prog_sched_rain_delay_change)


def prog_sched_system_option_change(name, **kw):
    """
    System options changed
    """
    prog_station_sched_stop()
    prog_sched_add_program()
    prog_station_sched_start()


sch_system_option_change = signal("option_change")
sch_system_option_change.connect(prog_sched_system_option_change)


##############################
# Program and Station Schedule Functions
#


def prog_station_sched_start() -> None:
    """
    Start the scheduler in a separate thread so it doesn't block our main code
    """
    global _prog_station_sched_next_time

    # Wait for prog_station_sched_run() to process any pending events
    with _prog_station_sched_lock:
        # Reset the next time for the scheduler to run
        _prog_station_sched_next_time = 0


def prog_station_sched_stop() -> None:
    """
    Stop the scheduler thread and cancel any scheduled events
    """

    global _prog_station_sched_next_time

    # Wait for prog_station_sched_run() to process any pending events
    with _prog_station_sched_lock:
        # Reset the next time for the scheduler to run
        _prog_station_sched_next_time = None


def prog_station_sched_restart() -> None:
    """
    Restart the scheduler to process any pending events immediately.
    This function is called when a program is added, changed, or deleted.
    """
    prog_station_sched_stop()  # Stop the scheduler and cancel any scheduled events
    prog_station_sched_start()  # Start the scheduler in a separate thread


def prog_data_to_prog_sched(
    pid: int, start_s: int | None = None, _get_previous_day: bool = False
) -> list:
    """
    Get program's list of running and upcoming period(s) for a specific day and time until next midnight.
    Program can have a single period, or multiple periods for recurring program (one per cycle).
    If _get_previous_day is True, will search for the latest period starting in the previous day and still running.
    When start_s is None, current date and time is used.

    Returns periods list = [ [start_time_s, stop_time_s, pid, cycle], ... ]
    - start_time_s and stop_time_s: timestamps in seconds since epoch
    - pid: program index
    - cycle: cycle number for recurring program starting at 1,  default to 1 for non-recurring program
    """

    periods = []

    p = gv.pd[pid]  # Get program data

    if not p["enabled"]:
        return periods  # skip disabled programs

    if not any(p["duration_sec"]):
        return periods  # skip program without any station duration

    if start_s is None:
        start_s = round(time.time())

    start_dt = datetime.fromtimestamp(start_s, tz=local_tz)
    start_d = datetime.date(start_dt)
    start_midnight_dt = datetime.combine(start_d, d_time.min)
    start_midnight_s = int(start_midnight_dt.timestamp())

    # get program period that started in the previous day and ends in current day
    if not _get_previous_day:
        previous_day_dt = start_midnight_dt - timedelta(days=1)
        previous_day_s = int(previous_day_dt.timestamp())
        previous_day_start_periods = prog_data_to_prog_sched(pid, previous_day_s, True)
        periods.extend(
            [item for item in previous_day_start_periods if item[1] > start_s]
        )

    # check if program is active in the current day
    if not prog_data_match_day(p, start_s):
        return periods

    p_start_s = start_midnight_s + int(p["start_min"]) * 60
    p_stop_s = start_midnight_s + int(p["stop_min"]) * 60

    # skip program ended before start_s
    if p_stop_s <= start_s:
        return periods

    if p["cycle_min"]:  # recurring program
        cycle = 1
        cycle_start_s = p_start_s
        cycle_duration_s = int(p["cycle_min"]) * 60
        p_stop_s = p_stop_s - cycle_duration_s
        while cycle_start_s <= p_stop_s:
            cycle_stop_s = cycle_start_s + cycle_duration_s
            if cycle_stop_s >= start_s:
                periods.append([cycle_start_s, cycle_stop_s, pid, cycle])
            cycle_start_s = cycle_stop_s
            cycle += 1
    else:  # single pass programs run only once a day
        if p_stop_s > start_s:
            periods.append([p_start_s, p_stop_s, pid, 1])
    return periods


def prog_data_to_prog_sched_all(start_s: int | None = None) -> list:
    """
    Get period list for **all program** running and upcoming periods in a specific day
    The period are sorted by start_time_s / stop_time_s / pid
    periods = [ [start_time_s, stop_time_s, pid, cycle], ... ]
    """
    periods = []
    for pid in range(len(gv.pd)):
        periods.extend(prog_data_to_prog_sched(pid, start_s))
    periods.sort(key=itemgetter(0, 1, 2))  # sort by start, stop time, pid
    return periods


def prog_sched_remove_program(pid: int | None = None) -> None:
    """
    Remove program (pid) associated periods from programs and station schedules lists.
    If pid is None, all program periods will be removed from the lists
    """
    with _prog_station_sched_lock:
        if pid is None:
            del _prog_sched_list[:]
            del _station_sched_list[:]
            return

        # Loop backwards from the last index to 0
        for index in range(len(_prog_sched_list) - 1, -1, -1):
            if _prog_sched_list[index][2] == pid:
                del _prog_sched_list[index]

        for index in range(len(_station_sched_list) - 1, -1, -1):
            if _station_sched_list[index][3] == pid:
                del _station_sched_list[index]


def prog_sched_add_program(pid: int | None = None, start_s: int | None = None) -> None:
    """
    If system enabled in auto mode, add or update currently active and
    upcoming periods until midnight to program's periods list.

    If pid is None, all programs will be processed
    """

    if not system_enabled_in_auto_mode():
        return  # System is not enabled in auto mode, no need to schedule programs

    # print(f"DEBUG: prog_sched add: {pid if pid else 'All'} ")

    prog_sched_remove_program(pid)  # Remove existing before adding

    with _prog_station_sched_lock:
        for l_pid in [pid] if pid else range(len(gv.pd)):
            # add new schedules
            _prog_sched_list.extend(prog_data_to_prog_sched(l_pid, start_s))

        # resort all schedules by start, stop, pnum
        _prog_sched_list.sort(key=itemgetter(0, 1, 2))


def prog_and_station_sched_remove_running_program(
    pid: int | None = None,
) -> None:
    """
    Disable running programs in gv.rs[] from rescheduling until next program schedule update.
    """
    r_pid_list = {}

    for st in gv.rs:
        r_pnum = st[3]
        if (0 < r_pnum < 98) and ((pid is None) or (pid == r_pnum - 1)):
            r_pid_list.add(r_pnum - 1)

    for r_pid in r_pid_list:
        prog_sched_remove_program(r_pid)


def prog_sched_to_station_sched(p_sched: list, from_s: int) -> list:
    """
    Produce station periods according to program cycle period start and stop time,
    and program data for the station (duration and order).
    Make adjustments based on water level and plugin adjustments and inter station delay.
    """
    p_start, p_stop, pid, cycle = p_sched

    if pid < 0 or pid > len(gv.pd):
        return  # Invalid program index

    p = gv.pd[pid]  # get program data

    if gv.sd["mas"]:
        masid = gv.sd["mas"] - 1  # master station index
    else:
        masid = None

    next_start = p_start
    pnum = pid + 1

    schedule_list = []

    # water level adjustment factor
    duration_adj = float((gv.sd["wl"]) / 100.0) * plugin_adjustment()

    # delay subtracted to stations stop and duration time running schedule
    isd_adj = int(gv.sd["sdt"])

    # check each station per boards listed in program up to number of boards in Options
    for b in range(gv.sd["nbrd"]):
        for s in range(8):
            sid = b * 8 + s

            if sid == masid:
                continue  # this is master station

            if gv.halted[sid]:
                continue  # station was halted by stop_stations()

            # station not scheduled in this program
            if not (p["station_mask"][b] & 1 << s):
                continue  # station not scheduled in this program

            if station_stop_on_rain(b, s):
                continue  # station don't schedule on rain

            if gv.sd["idd"]:  # individual duration per station.
                duration = int(p["duration_sec"][sid])
            else:
                duration = int(p["duration_sec"][0])

            # station duration is adjusted for water level.
            if not (gv.sd["iw"][b] & 1 << s):
                duration = int(duration * duration_adj)

            if not duration:
                continue  # schedule has no duration for this station

            # staged station start and stop time
            start = next_start
            stop = start + duration

            # running condition exclusion
            if start >= p_stop:
                continue  # will start after program period cycle stop time
            if gv.rs[sid][2] >= stop:
                continue  # Existing station schedule ending later

            # Adjust to fit into program cycle stop time (before isd_adj)
            stop = min(stop, p_stop)

            # adjust next start time
            if gv.sd["seq"]:
                next_start = stop  # start next station after this one

            # adjust stop time and duration for inter station / program duration delay (isd_adj)
            if gv.sd["seq"]:  # in sequential mode : inter station adjustment
                # delay is subtracted the duration of each station station within a program cycle
                stop -= isd_adj
            else:  # in concurrent mode: inter-program duration adjustment
                #  delay is subtracted to the station duration equal to the program cycle
                if stop == p_stop:
                    stop -= isd_adj

            # the final station duration
            duration = max(0, stop - start)
            if not duration:
                continue  # don't schedule station without duration

            # **new station schedule **
            schedule_list.append([start, stop, sid, pnum, cycle])

    return schedule_list


def station_sched_to_running_sched(s_sched: list, from_s: int) -> bool:
    """
    Use provided station periods to set/update running schedule for the station
    To be called just in time at the starting time of the station period

    Do:
      - Merge overlapping schedules coming from different programs running in parallel.
        On running schedule overlap, report schedule completed without interrupting the station
      - Update running schedule ( gv.rs[] ).
      - Update Web UI display ( gv.ps[] )
      - Report station activation (scheduled)

    """
    start, stop, sid, pnum, cycle = s_sched  # noqa: RUF059

    # Existing station schedule ending later
    if gv.rs[sid][2] >= stop:
        return False  # Don't schedule

    # Adjust to start at or after from_s
    start = max(start, from_s)

    # the final station duration
    duration = max(0, stop - start)

    # Don't schedule station without duration
    if not duration:
        return False

    # Don't reschedule when already running with the same stop time
    if stop == gv.rs[sid][1]:
        return False

    if gv.rs[sid][3] != 0:  # Changing a running station schedule
        run_schedule_completed(sid, gv.rs[sid][0], from_s, gv.rs[sid][3], False)

    # **new station schedule **
    gv.rs[sid] = [start, stop, duration, pnum]

    # update gv.ps for display
    gv.ps[sid] = [pnum, duration]

    report_station_scheduled(sid + 1)  # station activation event

    return True


def prog_station_sched_run() -> None:
    """
    Process the program schedule and station schedule to update the running schedule (gv.rs[]).

    Periods schedules will be processed if they match the current date and time.
    This function should be called from the main timing loop.

    It use the _prog_station_sched_next_time to determine when to run next.
        - Value == None:  means the schedules lists are empty and no need to run.
        - Value == 0: means the schedules lists are not empty and need to run now.
        - Value > 0: means the schedules lists are not empty and need to run at that time.

    On exit, will set the next time for the scheduler to run at the earliest between
    the next program or station schedule, or. set it to None if no more schedules are pending.
    """
    global _prog_station_sched_next_time

    if not system_enabled_in_auto_mode():
        return  # System is not enabled in auto mode, no need to schedule programs

    with _prog_station_sched_lock:
        now = gv.now  # current time in seconds since epoch

        if (
            _prog_station_sched_next_time is not None
            and 0 < _prog_station_sched_next_time
            and _prog_station_sched_next_time > now
        ):
            return  # Not time to run the scheduler yet

        # From program schedule to station schedule
        p_sched_processed_idx = []
        p_sched_next_run = None
        s_sched_len = len(_station_sched_list)
        for index, p_sched in enumerate(_prog_sched_list):
            if p_sched[0] > now:  # Period not started yet
                p_sched_next_run = p_sched[0]
                break
            else:
                # print(f"DEBUG: prog sched processing: {prog_sched_str(p_sched)}")
                _station_sched_list.extend(prog_sched_to_station_sched(p_sched, now))
                p_sched_processed_idx.append(index)

        # Sort only if added station schedule
        if s_sched_len != len(_station_sched_list):
            _station_sched_list.sort(
                key=itemgetter(0, 1, 2, 3)
            )  # resort all periods by start, stop, sid, pnum

        # From station schedule to running schedule
        s_sched_processed_idx = []
        s_sched_next_run = None
        set_busy = False
        for index, s_sched in enumerate(_station_sched_list):
            if s_sched[0] > now:
                s_sched_next_run = s_sched[0]
                break
            if station_sched_to_running_sched(s_sched, now):
                set_busy = True
            s_sched_processed_idx.append(index)

        # remove processed schedule from prog and station lists
        for index in sorted(p_sched_processed_idx, reverse=True):
            del _prog_sched_list[index]

        for index in sorted(s_sched_processed_idx, reverse=True):
            del _station_sched_list[index]

        # enable running station processing in timing_loop()
        if set_busy:
            gv.sd["bsy"] = 1

        # Set Next execution at the earliest between to the next program or station schedule
        _prog_station_sched_next_time = min(
            (x for x in (p_sched_next_run, s_sched_next_run) if x is not None),
            default=None,
        )
