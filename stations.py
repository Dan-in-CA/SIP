__author__ = 'Rimco'

from options import options

class Station(object):
    SAVE_EXCLUDE = ['SAVE_EXCLUDE', 'index', 'activated']

    def __init__(self, outputs, index):
        self._outputs = outputs
        self._index = index
        self._is_master = False
        self._activate_master = False

        self.name = "Station %02d" % index
        self.enabled = False
        self.ignore_rain = False

        options.load(self, self._index)

    @property
    def index(self):
        return self._index

    @property
    def is_master(self):
        return self._is_master

    @is_master.setter
    def is_master(self, value):
        if self._is_master != value:
            self._is_master = value
            if value:
                self._outputs.master = self._index

    @property
    def activate_master(self):
        return self._activate_master

    @activate_master.setter
    def activate_master(self, value):
        self._activate_master = value
        self._outputs.check_master()

    @property
    def activated(self):
        return self._outputs.activated(self._index)

    @activated.setter
    def activated(self, value):
        if value:
            self._outputs.activate(self._index)
        else:
            self._outputs.deactivate(self._index)

    def __setattr__(self, key, value):
        super(Station, self).__setattr__(key, value)
        if not key.startswith('_') and key not in self.SAVE_EXCLUDE:
            options.save(self, self._index)


class DummyStations(object):
    def __init__(self, count):
        self._outputs = []
        self._state = [False] * count
        for i in range(count):
            self._outputs.append(Station(self, i))

    def resize(self, count):
        while len(self._outputs) < count:
            self._outputs.append(Station(self, len(self._outputs)))
            self._state.append(False)
        while len(self._outputs) > count:
            del self._outputs[-1]
            del self._state[-1]

    def count(self):
        return len(self._outputs)

    def get(self, index=None):
        if index is None:
            result = self._outputs[:]
        else:
            result = self._outputs[index]
        return result

    def activate(self, index):
        self._state[index] = True
        print "Output", index, "=", self._state[index]
        self.check_master()

    def deactivate(self, index):
        self._state[index] = False
        print "Output", index, "=", self._state[index]
        self.check_master()

    def activated(self, index=None):
        if index is None:
            result = self._state[:]
        else:
            result = self._state[index]
        return result

    def clear(self):
        for i in range(len(self._state)):
            self._state[i] = False

    @property
    def master(self):
        result = None
        for index, station in enumerate(self._outputs):
            if station.is_master:
                result = index
                break
        return result

    @master.setter
    def master(self, value):
        old_master = self.master
        if old_master is not None and self._state[old_master]:
            self._state[old_master] = False

        for index, station in enumerate(self._outputs):
            if index == value:
                station.is_master = True
            else:
                station.is_master = False
        self.check_master()

    def check_master(self):
        master = self.master
        if master is not None:
            for station in self._outputs:
                if station.activated and station.activate_master:
                    self._state[master] = True
                    break
            else:
                self._state[master] = False



class ShiftStations(DummyStations):
    def __init__(self, count):
        super(ShiftStations, self).__init__(count)
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

        self._activate()

    def _activate(self):
        """Set the state of each output pin on the shift register from the internal state."""
        self.check_master()
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
        super(ShiftStations, self).resize(count)
        self._activate()

    def activate(self, index):
        self._state[index] = True
        self._activate()

    def deactivate(self, index):
        self._state[index] = False
        self._activate()

    def clear(self):
        super(ShiftStations, self).clear()
        self._activate()


class RPiStations(ShiftStations):
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

        super(RPiStations, self).__init__(count)


class BBBStations(ShiftStations):
    def __init__(self, count):
        import Adafruit_BBIO.GPIO as GPIO  # Beagle Bone Black hardware

        self._io = GPIO
        self._io.setwarnings(False)
        self._io.cleanup()

        self._sr_dat = "P9_11"
        self._sr_clk = "P9_13"
        self._sr_noe = "P9_14"
        self._sr_lat = "P9_12"

        super(BBBStations, self).__init__(count)


try:
    stations = RPiStations(options.output_count)
except Exception:
    try:
        stations = BBBStations(options.output_count)
    except Exception:
        stations = DummyStations(options.output_count)