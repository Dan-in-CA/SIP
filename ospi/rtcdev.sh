#! /bin/sh
### BEGIN INIT INFO
# Provides:          rtcdev
# Required-Start:    kmod
# Required-Stop:
# Default-Start:     S
# Default-Stop:
# Short-Description: creates RTC device
### END INIT INFO

. /lib/lsb/init-functions

case "$1" in
  start)
        if [ ! -e /dev/rtc0 ]; then
            log_action_msg "Creating RTC device..."
            echo ds1307 0x68 > /sys/class/i2c-adapter/i2c-1/new_device
        fi
        ;;
  restart|reload|force-reload)
        echo "Error: argument '$1' not supported" >&2
        exit 3
        ;;
  stop)
        # No-op
        ;;
  *)
        echo "Usage: $0 start|stop" >&2
        exit 3
        ;;
esac
