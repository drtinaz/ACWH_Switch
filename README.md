A python script that monitors the ac input source of a victron inverter and automatically switches the AC water heater switch on if the source is Grid or Shore, and switches it off otherwise. meant to operate on a cerbo gx but might work on other venus os devices as well. AC Water Heater must be controlled by one of the gx relays.

######## INSTALLATION #########

The water heater must be controlled by one of the GX devices relays, and that relay must have the name changed to "AC Water Heater" or "AC WH" in order for the service to discover it.

The easiest method of installation is using Kevin Windrem's setup helper. 
add this package to the packages list

Package name: ACWH_Switch
Tag or Branch: main
Github User: drtinaz
