#!/usr/bin/env python3

import dbus
import logging
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# D-Bus service name and path
SYSTEM_SERVICE = "com.victronenergy.system"
AC_ACTIVE_INPUT_SOURCE_PATH = "/Ac/ActiveIn/Source"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"

class ACInputSourceMonitor:
    def __init__(self):
        self.bus = dbus.SystemBus()
        GLib.timeout_add_seconds(2, self._read_ac_input_source)
        GLib.timeout_add(5000, self._periodic_monitoring)

    def _get_dbus_value(self, service_name, path):
        try:
            obj = self.bus.get_object(service_name, path)
            interface = dbus.Interface(obj, BUS_ITEM_INTERFACE)
            return interface.GetValue()
        except Exception as e:
            logging.error(f"Error getting value from {service_name}{path}: {e}")
            return None

    def _read_ac_input_source(self):
        source_value = self._get_dbus_value(SYSTEM_SERVICE, AC_ACTIVE_INPUT_SOURCE_PATH)
        if source_value is not None:
            source_text = self._interpret_ac_source(source_value)
            logging.info(f"Active AC Input Source on {SYSTEM_SERVICE}{AC_ACTIVE_INPUT_SOURCE_PATH}: {source_text} (Value: {source_value})")
        else:
            logging.warning(f"Could not read the active AC input source from {SYSTEM_SERVICE}{AC_ACTIVE_INPUT_SOURCE_PATH}.")
        # Return True to keep the timeout running
        return True

    def _interpret_ac_source(self, value):
        if value == 0:
            return "Unavailable"
        elif value == 1:
            return "Grid"
        elif value == 2:
            return "Generator"
        elif value in [3, 4]:
            return "Shore"
        elif value == 240:
            return "Inverting"
        else:
            return f"Unknown ({value})"

    def _periodic_monitoring(self):
        # Just call the reading function again
        self._read_ac_input_source()
        return True

def main():
    DBusGMainLoop(set_as_default=True)
    ACInputSourceMonitor()
    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()
