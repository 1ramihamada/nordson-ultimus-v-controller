# Nordson Ultimus V Dispenser Controller

This project contains Python code to control the Nordson Ultimus V Precision Dispenser using RS-232 serial communication. It provides a command-line interface to control the dispenser settings, modes, and operations according to the Nordson communication protocol.

## Features
- Control dispensing modes (timed and steady).
- Set and adjust dispense pressure and vacuum levels.
- Read current settings such as pressure, time, and vacuum.
- Toggle between different modes and set time values.

## Requirements
- Python 3
- `pyserial` library (install with `pip install pyserial`)

## Setup
1. Connect the Nordson Ultimus V dispenser to your computer using a compatible RS-232 connection.
2. Install dependencies:
   ```bash
   pip install pyserial
   
## Commands
Below is a list of available commands you can use with this script:

- **start**: Start dispensing.
  - Sends the `DI  ` command to the dispenser.

- **stop**: Stop dispensing.
  - Sends the `DO  ` command to the dispenser.

- **pressure `<value>`**: Set the dispense pressure.
  - Replace `<value>` with a float:
    - psi: `0.0 - 100.0`
    - kPa: `0.0 - 689.5`
    - Bar: `0.000 - 6.895`
  - Sends the `PS  ` command with the formatted pressure value.

- **vacuum `<value>`**: Set the vacuum level.
  - Replace `<value>` with a float:
    - H2O: `0.0 - 18.0`
    - kPa: `0.00 - 4.48`
    - Hg: `0.00 - 1.32`
    - mmHg or Torr: `0.0 - 33.6`
  - Sends the `VS  ` command with the formatted vacuum value.

- **toggle_mode**: Toggle between timed and steady modes.
  - Sends the `TM  ` command.
  - Updates the internal state to reflect the current mode.

- **time `<value>`**: Set the dispense time.
  - Replace `<value>` with a float between `0.0000` and `9.9999` seconds.
  - Sends the `DS  ` command with the formatted time value.

- **read_values `<memory_location>`**: Read the pressure, time, and vacuum values from a specified memory location.
  - Replace `<memory_location>` with an integer between `0` and `399`.
  - Sends the `E8` command with the memory location and displays the retrieved values.

- **set_pressure_units `<unit>`**: Set the pressure units.
  - Replace `<unit>` with one of the following: `psi`, `bar`, `kpa`.
  - Sends the `E6  ` command with the unit code.

- **set_vacuum_units `<unit>`**: Set the vacuum units.
  - Replace `<unit>` with one of the following: `kpa`, `inches_h2o`, `inches_hg`, `mmhg`, `torr`.
  - Sends the `E7  ` command with the unit code.

- **exit**: Exit the script.
