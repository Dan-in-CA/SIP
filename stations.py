__author__ = 'Rimco'

from options import options


class _Station(object):
    SAVE_EXCLUDE = ['SAVE_EXCLUDE', 'index', 'active']

    def __init__(self, stations_instance, index):
        self._stations = stations_instance
        self.activate_master = False

        self.name = "Station %02d" % (index+1)
        self.enabled = False
        self.ignore_rain = False

        options.load(self, index)

    @property
    def index(self):
        return self._stations.get().index(self)

    @property
    def is_master(self):
        return self.index == self._stations.master

    @is_master.setter
    def is_master(self, value):
        if value:
            self._stations.master = self.index
        elif self.is_master:
            self._stations.master = None

    @property
    def active(self):
        return self._stations.active(self.index)

    @active.setter
    def active(self, value):
        if value:
            self._stations.activate(self.index)
        else:
            self._stations.deactivate(self.index)

    def __setattr__(self, key, value):
        try:
            super(_Station, self).__setattr__(key, value)
            if not key.startswith('_') and key not in self.SAVE_EXCLUDE:
                options.save(self, self.index)
        except ValueError:  # No index available yet
            pass


class _BaseStations(object):
    def __init__(self, count):
        self.master = None
        self._stations = []
        self._state = [False] * count
        for i in range(count):
            self._stations.append(_Station(self, i))
        self.clear()

    def resize(self, count):
        while len(self._stations) < count:
            self._stations.append(_Station(self, len(self._stations)))
            self._state.append(False)

        # Make sure we turn them off before they become unreachable
        if len(self._stations) > count:
            self.clear()

        while len(self._stations) > count:
            del self._stations[-1]
            del self._state[-1]

    def count(self):
        return len(self._stations)

    def get(self, index=None):
        if index is None:
            result = self._stations[:]
        else:
            result = self._stations[index]
        return result

    def activate(self, index):
        self._state[index] = True

    def deactivate(self, index):
        self._state[index] = False

    def active(self, index=None):
        if index is None:
            result = self._state[:]
        else:
            result = self._state[index]
        return result

    def clear(self):
        for i in range(len(self._state)):
            self._state[i] = False


class _DummyStations(_BaseStations):
    def resize(self, count):
        super(_DummyStations, self).resize(count)
        print "Output count =", count

    def activate(self, index):
        super(_DummyStations, self).activate(index)
        print "Activated output", index

    def deactivate(self, index):
        super(_DummyStations, self).deactivate(index)
        print "Deactivated output", index

    def clear(self):
        super(_DummyStations, self).clear()
        print "Cleared all outputs"


class _ShiftStations(_BaseStations):
    def __init__(self, count):
        self._io = None
        self._sr_dat = 0
        self._sr_clk = 0
        self._sr_noe = 0
        self._sr_lat = 0

        self._io.setup(self._sr_noe, self._io.OUT)
        self._io.output(self._sr_noe, self._io.HIGH)
        self._io.setup(self._sr_clk, self._io.OUT)
        self._io.output(self._sr_clk, self._io.LOW)
        self._io.setup(self._sr_dat, self._io.OUT)
        self._io.output(self._sr_dat, self._io.LOW)
        self._io.setup(self._sr_lat, self._io.OUT)
        self._io.output(self._sr_lat, self._io.LOW)

        super(_ShiftStations, self).__init__(count)

    def _activate(self):
        """Set the state of each output pin on the shift register from the internal state."""
        self._io.output(self._sr_noe, self._io.HIGH)
        self._io.output(self._sr_clk, self._io.LOW)
        self._io.output(self._sr_lat, self._io.LOW)
        for state in reversed(self._state):
            self._io.output(self._sr_clk, self._io.LOW)
            self._io.output(self._sr_dat, self._io.HIGH if state else self._io.LOW)
            self._io.output(self._sr_clk, self._io.HIGH)
        self._io.output(self._sr_lat, self._io.HIGH)
        self._io.output(self._sr_noe, self._io.LOW)

    def resize(self, count):
        super(_ShiftStations, self).resize(count)
        self._activate()

    def activate(self, index):
        super(_ShiftStations, self).activate(index)
        self._activate()

    def deactivate(self, index):
        super(_ShiftStations, self).deactivate(index)
        self._activate()

    def clear(self):
        super(_ShiftStations, self).clear()
        self._activate()


class _RPiStations(_ShiftStations):
    def __init__(self, count):
        import RPi.GPIO as GPIO  # RPi hardware

        self._io = GPIO
        self._io.setwarnings(False)
        self._io.cleanup()
        self._io.setmode(self._io.BOARD)  # IO channels are identified by header connector pin numbers. Pin numbers are always the same regardless of Raspberry Pi board revision.

        self._sr_dat = 13
        self._sr_clk = 7
        self._sr_noe = 11
        self._sr_lat = 15

        super(_RPiStations, self).__init__(count)


class _BBBStations(_ShiftStations):
    def __init__(self, count):
        import Adafruit_BBIO.GPIO as GPIO  # Beagle Bone Black hardware

        self._io = GPIO
        self._io.setwarnings(False)
        self._io.cleanup()

        self._sr_dat = "P9_11"
        self._sr_clk = "P9_13"
        self._sr_noe = "P9_14"
        self._sr_lat = "P9_12"

        super(_BBBStations, self).__init__(count)


try:
    stations = _RPiStations(options.output_count)
except Exception:
    try:
        stations = _BBBStations(options.output_count)
    except Exception:
        stations = _DummyStations(options.output_count)