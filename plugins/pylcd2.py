import smbus
from time import sleep


# General i2c device class so that other devices can be added easily
class i2c_device:
    def __init__(self, addr, port):
        self.addr = addr
        self.bus = smbus.SMBus(port)

    def write(self, byte):
        self.bus.write_byte(self.addr, byte)

    def read(self):
        return self.bus.read_byte(self.addr)

    def read_nbytes_data(self, data, n):  # For sequential reads > 1 byte
        return self.bus.read_i2c_block_data(self.addr, data, n)


class lcd:
    #initializes objects and lcd
    """
    Reverse Codes:
    0: lower 4 bits of expander are commands bits
    1: top 4 bits of expander are commands bits AND P0-4 P1-5 P2-6
    2: top 4 bits of expander are commands bits AND P0-6 P1-5 P2-4
    """

    def __init__(self, addr, port, reverse=0):
        self.reverse = reverse
        self.lcd_device = i2c_device(addr, port)
        if self.reverse:
            self.lcd_device.write(0x30)
            self.lcd_strobe()
            sleep(0.0005)
            self.lcd_strobe()
            sleep(0.0005)
            self.lcd_strobe()
            sleep(0.0005)
            self.lcd_device.write(0x20)
            self.lcd_strobe()
            sleep(0.0005)
        else:
            self.lcd_device.write(0x03)
            self.lcd_strobe()
            sleep(0.0005)
            self.lcd_strobe()
            sleep(0.0005)
            self.lcd_strobe()
            sleep(0.0005)
            self.lcd_device.write(0x02)
            self.lcd_strobe()
            sleep(0.0005)

        self.lcd_write(0x28)
        self.lcd_write(0x08)
        self.lcd_write(0x01)
        self.lcd_write(0x06)
        self.lcd_write(0x0C)
        self.lcd_write(0x0F)

    # clocks EN to latch command
    def lcd_strobe(self):
        if self.reverse == 1:
            self.lcd_device.write((self.lcd_device.read() | 0x04))
            self.lcd_device.write((self.lcd_device.read() & 0xFB))
        if self.reverse == 2:
            self.lcd_device.write((self.lcd_device.read() | 0x01))
            self.lcd_device.write((self.lcd_device.read() & 0xFE))
        else:
            self.lcd_device.write((self.lcd_device.read() | 0x10))
            self.lcd_device.write((self.lcd_device.read() & 0xEF))

    # write a command to lcd
    def lcd_write(self, cmd):
        if self.reverse:
            self.lcd_device.write((cmd >> 4) << 4)
            self.lcd_strobe()
            self.lcd_device.write((cmd & 0x0F) << 4)
            self.lcd_strobe()
            self.lcd_device.write(0x0)
        else:
            self.lcd_device.write((cmd >> 4))
            self.lcd_strobe()
            self.lcd_device.write((cmd & 0x0F))
            self.lcd_strobe()
            self.lcd_device.write(0x0)

    # write a character to lcd (or character rom)
    def lcd_write_char(self, charvalue):
        if self.reverse == 1:
            self.lcd_device.write((0x01 | (charvalue >> 4) << 4))
            self.lcd_strobe()
            self.lcd_device.write((0x01 | (charvalue & 0x0F) << 4))
            self.lcd_strobe()
            self.lcd_device.write(0x0)
        if self.reverse == 2:
            self.lcd_device.write((0x04 | (charvalue >> 4) << 4))
            self.lcd_strobe()
            self.lcd_device.write((0x04 | (charvalue & 0x0F) << 4))
            self.lcd_strobe()
            self.lcd_device.write(0x0)
        else:
            self.lcd_device.write((0x40 | (charvalue >> 4)))
            self.lcd_strobe()
            self.lcd_device.write((0x40 | (charvalue & 0x0F)))
            self.lcd_strobe()
            self.lcd_device.write(0x0)

    # put char function
    def lcd_putc(self, char):
        self.lcd_write_char(ord(char))

    # put string function
    def lcd_puts(self, string, line):
        if line == 1:
            self.lcd_write(0x80)
        if line == 2:
            self.lcd_write(0xC0)
        if line == 3:
            self.lcd_write(0x94)
        if line == 4:
            self.lcd_write(0xD4)

        for char in string:
            self.lcd_putc(char)

    # clear lcd and set to home
    def lcd_clear(self):
        self.lcd_write(0x1)
        self.lcd_write(0x2)

    # add custom characters (0 - 7)
    def lcd_load_custon_chars(self, fontdata):
        self.lcd_device.bus.write(0x40)
        for char in fontdata:
            for line in char:
                self.lcd_write_char(line)

