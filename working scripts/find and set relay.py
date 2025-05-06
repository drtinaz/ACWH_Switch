#!/usr/bin/env python3

import dbus
import logging
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# D-Bus service names and paths
SETTINGS_SERVICE_NAME = "com.victronenergy.settings"
SYSTEM_SERVICE = "com.victronenergy.system"
RELAY_PATH_BASE = "/Relay/"
CUSTOM_NAME_PATH_SUFFIX = "/CustomName"
STATE_PATH_SUFFIX = "/State"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"
SETTINGS_RELAY_BASE_PATH = "/Settings/Relay"

TARGET_CUSTOM_NAMES = ["AC Water Heater", "AC WH"]
MAX_RELAY_NUMBER_TO_CHECK = 10  # Adjust this if you expect more relays

class WaterHeaterRelayController:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.water_heater_relay_number = None
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

    def _set_relay_state_on_system(self, relay_number, value):
        path = f"{RELAY_PATH_BASE}{relay_number}{STATE_PATH_SUFFIX}"
        obj = self._get_dbus_object(SYSTEM_SERVICE, path)
        if obj:
            try:
                interface = dbus.Interface(obj, BUS_ITEM_INTERFACE)
                interface.SetValue(dbus.Int32(value))
                logging.info(f"Set {SYSTEM_SERVICE}{path} to {value}")
                return True
            except dbus.exceptions.DBusException as e:
                logging.error(f"Error setting value for {SYSTEM_SERVICE}{path}: {e}")
        return False

    def _find_water_heater_relay(self):
        for relay_number in range(MAX_RELAY_NUMBER_TO_CHECK):
            custom_name_path = f"{SETTINGS_RELAY_BASE_PATH}/{relay_number}{CUSTOM_NAME_PATH_SUFFIX}"
            custom_name = self._get_dbus_value(SETTINGS_SERVICE_NAME, custom_name_path)

            if custom_name in TARGET_CUSTOM_NAMES:
                self.water_heater_relay_number = relay_number
                state_path_system = f"{RELAY_PATH_BASE}{relay_number}{STATE_PATH_SUFFIX}"
                state = self._get_dbus_value(SYSTEM_SERVICE, state_path_system)
                logging.info(f"Found Water Heater Relay:")
                logging.info(f"  Relay Number: {relay_number}")
                logging.info(f"  Custom Name (on {SETTINGS_SERVICE_NAME}): '{custom_name}'")
                logging.info(f"  Current State (on {SYSTEM_SERVICE}): {'on' if state == 1 else 'off'}")
                self._prompt_user_to_change_state(relay_number, state)
                return  # Found it, so stop

        logging.info(f"Could not find a relay with custom names: {TARGET_CUSTOM_NAMES} under {SETTINGS_RELAY_BASE_PATH}/<number>/CustomName (checking up to relay {MAX_RELAY_NUMBER_TO_CHECK})")
        GLib.MainLoop().quit() # Exit if not found

    def _prompt_user_to_change_state(self, relay_number, current_state):
        while True:
            action = input(f"Turn water heater relay {'off' if current_state == 1 else 'on'}? (y/n): ").lower()
            if action == 'y':
                new_state = 1 if current_state == 0 else 0
                if self._set_relay_state_on_system(relay_number, new_state):
                    print(f"Water heater relay turned {'on' if new_state == 1 else 'off'}.")
                break
            elif action == 'n':
                print("No change made.")
                break
            else:
                print("Invalid input. Please enter 'y' or 'n'.")
        GLib.MainLoop().quit()

def main():
    DBusGMainLoop(set_as_default=True)
    WaterHeaterRelayController()
    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()
