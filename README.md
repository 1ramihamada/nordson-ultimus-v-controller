# Nordson Ultimus V Dispenser Controller

This project contains Python code to control the Nordson Ultimus V Precision Dispenser using RS-232 serial communication. It provides a command-line interface to control the dispenser settings, modes, and operations according to the Nordson communication protocol.

## Features
- Control dispensing modes (timed and steady).
- Set and adjust dispense pressure and vacuum levels.
- Read current settings such as pressure, time, and vacuum.
- Toggle between different modes and set time values.

## Requirements
- Python 3.x
- `pyserial` library (install with `pip install pyserial`)

## Setup
1. Connect the Nordson Ultimus V dispenser to your computer using a compatible RS-232 connection.
2. Install dependencies:
   ```bash
   pip install pyserial
