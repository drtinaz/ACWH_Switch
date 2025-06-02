#!/usr/bin/env python3

import dbus
import logging
import os
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

# Define the log file path
LOG_FILE = '/data/ACWH_Switch/log'

# Ensure the log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Logging setup to write to the specified file
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=LOG_FILE)

# D-Bus service names and paths
SETTINGS_SERVICE_NAME = "com.victronenergy.settings"
SYSTEM_SERVICE = "com.victronenergy.system"
AC_ACTIVE_INPUT_SOURCE_PATH = "/Ac/ActiveIn/Source"
RELAY_PATH_BASE = "/Relay/"
CUSTOM_NAME_PATH_SUFFIX = "/CustomName"
STATE_PATH_SUFFIX = "/State"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"
SETTINGS_RELAY_BASE_PATH = "/Settings/Relay"

TARGET_CUSTOM_NAMES = ["AC Water Heater", "AC WH"] # you can add/remove/change custom names here that the service will look for
MAX_RELAY_NUMBER_TO_CHECK = 10  # Adjust this if you expect more relays

class WaterHeaterController:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.water_heater_relay_number = None
        self.previous_ac_source = None
        self.initial_state_set = False
        self.relay_found = False  # Flag to prevent repeated finding

        # Find the water heater relay at startup
        GLib.timeout_add_seconds(2, self._find_water_heater_relay)

    def _get_dbus_object(self, service_name, path):
        try:
            return self.bus.get_object(service_name, path)
        except dbus.exceptions.DBusException as e:
            logging.error(f"Error getting D-Bus object {service_name}{path}: {e}")
            return None

    def _get_dbus_value(self, service_name, path):
        obj = self._get_dbus_object(service_name, path)
        if obj:
            try:
                interface = dbus.Interface(obj, BUS_ITEM_INTERFACE)
                return interface.GetValue()
            except dbus.exceptions.DBusException as e:
                logging.error(f"Error getting value from {service_name}{path}: {e}")
        return None

    def _set_relay_state(self, relay_number, value):
        if relay_number is not None:
            path = f"{RELAY_PATH_BASE}{relay_number}{STATE_PATH_SUFFIX}"
            obj = self._get_dbus_object(SYSTEM_SERVICE, path)
            if obj:
                try:
                    interface = dbus.Interface(obj, BUS_ITEM_INTERFACE)
                    interface.SetValue(dbus.Int32(value))
                    logging.info(f"Set {SYSTEM_SERVICE}{path} to {value} (Water Heater Relay)")
                    return True
                except dbus.exceptions.DBusException as e:
                    logging.error(f"Error setting value for {SYSTEM_SERVICE}{path}: {e}")
        return False

    def _find_water_heater_relay(self):
        if self.relay_found:
            return False # Only run once

        for relay_number in range(MAX_RELAY_NUMBER_TO_CHECK):
            custom_name_path = f"{SETTINGS_RELAY_BASE_PATH}/{relay_number}{CUSTOM_NAME_PATH_SUFFIX}"
            custom_name = self._get_dbus_value(SETTINGS_SERVICE_NAME, custom_name_path)

            if custom_name in TARGET_CUSTOM_NAMES:
                self.water_heater_relay_number = relay_number
                logging.info(f"Found Water Heater Relay: Number {relay_number}")
                self.relay_found = True
                # Set initial AC source and then start monitoring
                GLib.timeout_add_seconds(1, self._initialize_monitoring)
                return False  # Stop further searching in this iteration

        logging.info(f"Could not find a relay with custom names: {TARGET_CUSTOM_NAMES}")
        return False # Keep running the timeout until found or script ends

    def _initialize_monitoring(self):
        if self.initial_state_set or self.water_heater_relay_number is None:
            return False # Only run once

        source_value = self._get_dbus_value(SYSTEM_SERVICE, AC_ACTIVE_INPUT_SOURCE_PATH)
        if source_value is not None:
            source_text = self._interpret_ac_source(source_value)
            if source_text in ["Grid", "Shore"]:
                self._set_relay_state(self.water_heater_relay_number, 1)  # Turn on
            else:
                self._set_relay_state(self.water_heater_relay_number, 0)  # Turn off
            self.previous_ac_source = source_value
            self.initial_state_set = True
            # Now start the periodic monitoring
            GLib.timeout_add_seconds(5, self._monitor_ac_input_source)
            return False # Don't run again
        return True # Try again if source is not available yet

    def _monitor_ac_input_source(self):
        if not self.initial_state_set or self.water_heater_relay_number is None:
            return True # Wait until initial state is set and relay is found

        source_value = self._get_dbus_value(SYSTEM_SERVICE, AC_ACTIVE_INPUT_SOURCE_PATH)
        if source_value is not None and source_value != self.previous_ac_source:
            source_text = self._interpret_ac_source(source_value)
            logging.info(f"AC Input Source changed to: {source_text} (Value: {source_value})")
            if source_text in ["Grid", "Shore"]:
                self._set_relay_state(self.water_heater_relay_number, 1)  # Turn on
            else:
                self._set_relay_state(self.water_heater_relay_number, 0)  # Turn off
            self.previous_ac_source = source_value
        elif source_value is None:
            logging.warning(f"Could not read AC input source.")
        return True  # Continue monitoring

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

def main():
    DBusGMainLoop(set_as_default=True)
    WaterHeaterController()
    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()
