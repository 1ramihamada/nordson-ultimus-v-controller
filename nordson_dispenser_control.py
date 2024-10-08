import serial
import logging
import serial.tools.list_ports
import time

class DispenserController:
    def __init__(self):
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('DispenserController')
        
        self.ser = None
        self.connect()
        
        # Keep track of the current mode (Timed or Steady)
        self.is_timed_mode = True  # Assume starting in Timed Mode
        
        # Initialize start time variable
        self.start_time = None  # Will be set when a command is issued
        
        self.logger.info('Dispenser Controller Started')
    
    def connect(self):
        available_ports = list(serial.tools.list_ports.comports())
        
        if not available_ports:
            self.logger.error("No serial ports found. Running in simulation mode.")
            return

        self.logger.info("Available serial ports:")
        for port in available_ports:
            self.logger.info(f"  {port.device}: {port.description}")
        
        for port in available_ports:
            try:
                self.ser = serial.Serial(
                    port.device,
                    baudrate=115200,  # Correct baud rate as per manual
                    bytesize=serial.EIGHTBITS,  # 8 data bits (ASCII)
                    parity=serial.PARITY_NONE,   # No parity
                    stopbits=serial.STOPBITS_ONE,  # 1 stop bit
                    timeout=0.0001
                )
                self.logger.info(f'Connected to {port.device}')
                time.sleep(2)  # Wait for device to initialize
                return
            except serial.SerialException as e:
                self.logger.error(f"Error connecting to {port.device}: {e}")
                continue
        
        if not self.ser:
            self.logger.error("Could not connect to any port. Running in simulation mode.")

    def run(self):
        try:
            while True:
                command_str = input("Enter command: ")
                if command_str.lower() == 'exit':
                    break
                # Record the start time when the user presses Enter
                self.start_time = time.time()
                self.dispenser_callback(command_str)
        except KeyboardInterrupt:
            pass
        finally:
            self.destroy()
    
    def calculate_checksum_ascii(self, data_str):
        """
        Calculate the checksum as per the device's protocol.
        The checksum is calculated by subtracting the sum of the ASCII values from zero (0x00).
        The result is the two's complement of the sum, and the least significant byte is used.
        """
        checksum = (0 - sum(data_str.encode('ascii'))) & 0xFF
        return checksum

    def send_command(self, command_code, data, expect_response=False):
        if self.ser:
            try:
                # Send ENQ (0x05) before each command
                self.ser.write(b'\x05')
                self.logger.debug('Sent ENQ (0x05)')
                time.sleep(0.1)  # Wait a bit for the device to respond

                # Wait for ACK (0x06)
                ack_response = self.ser.read(1)
                if ack_response != b'\x06':
                    self.logger.warning("Did not receive ACK after ENQ. Communication may not be established.")
                    return
                self.logger.debug('Received ACK after ENQ')

                # Proceed to send the command packet
                STX = b'\x02'  # Start of Text as a single byte
                ETX = b'\x03'  # End of Text as a single byte

                # Convert command code and data to strings
                command_str = command_code  # Ensure command_code has spaces instead of hyphens
                data_str = data if data else ''

                # Correct Length: total number of characters in Command and Data
                length = len(command_str) + len(data_str)
                length_hex = f"{length:02X}"  # Zero-padded two-digit hexadecimal
                length_str = length_hex  # This is already ASCII representation

                # Data for checksum calculation
                checksum_input_str = length_str + command_str + data_str
                checksum_value = self.calculate_checksum_ascii(checksum_input_str)
                checksum_str = f"{checksum_value:02X}"  # Uppercase hexadecimal, two digits

                # Construct the full packet
                packet = (
                    STX +
                    length_str.encode('ascii') +
                    command_str.encode('ascii') +
                    data_str.encode('ascii') +
                    checksum_str.encode('ascii') +
                    ETX
                )

                # For debugging, print the packet being sent
                self.logger.debug(f'Sent packet: {packet.hex()}')

                # Send the command packet
                self.ser.write(packet)
                time.sleep(0.1)  # Wait for device to process

                # Wait for response from the dispenser
                response = self.ser.read(100)  # Read up to 100 bytes
                if response:
                    return self.check_response(response, expect_response)
                else:
                    self.logger.warning("No response from device after sending command. Command may not have been executed.")
            except serial.SerialException as e:
                self.logger.error(f"Error communicating with device: {e}")
        else:
            self.logger.info(f'Simulated command sent.')
            self.logger.info('Simulated successful response')
        return None

    def dispenser_callback(self, command_str):
        if command_str == 'start':
            # RS-232 command to start dispensing (DI  )
            self.send_command('DI  ', '')
        elif command_str == 'stop':
            # RS-232 command to stop dispensing (DO  )
            self.send_command('DI  ', '')
        elif command_str.startswith('pressure '):
            try:
                pressure_value = float(command_str.split(' ')[1])
                if 0.0 <= pressure_value <= 100.0:
                    formatted_pressure = f"{int(pressure_value * 10):04d}"
                    self.send_command('PS  ', formatted_pressure)
                else:
                    self.logger.error(f'Invalid pressure value: {pressure_value}. Must be between 0.0 and 100.0 psi')
            except (IndexError, ValueError):
                self.logger.error('Invalid pressure command format. Use: pressure <value>')
        elif command_str.startswith('vacuum '):
            try:
                vacuum_value = float(command_str.split(' ')[1])
                if 0.0 <= vacuum_value <= 18.0:
                    formatted_vacuum = f"{int(vacuum_value * 10):04d}"
                    self.send_command('VS  ', formatted_vacuum)
                else:
                    self.logger.error(f'Invalid vacuum value: {vacuum_value}. Must be between 0.0 and 18.0 inH2O')
            except (IndexError, ValueError):
                self.logger.error('Invalid vacuum command format. Use: vacuum <value>')
        elif command_str == 'toggle_mode':
            # RS-232 command to toggle between timed and steady mode (TM  )
            self.send_command('TM  ', '')
            
            if self.is_timed_mode:
                self.is_timed_mode = False
                self.logger.info('Switched to Steady Mode')
            else:
                self.is_timed_mode = True
                self.logger.info('Switched to Timed Mode')
        elif command_str.startswith('time '):
            # Set Dispense Time Command
            try:
                time_value = float(command_str.split(' ')[1])
                if 0.0000 <= time_value <= 9.9999:
                    # Remove decimal point and format as per the manual
                    if time_value < 1.0000:
                        formatted_time = f"T{int(time_value * 10000):04d}"
                    else:
                        formatted_time = f"T{int(time_value * 10000):05d}"
                    self.send_command('DS  ', formatted_time)
                else:
                    self.logger.error(f'Invalid time value: {time_value}. Must be between 0.0000 and 9.9999 seconds')
            except (IndexError, ValueError):
                self.logger.error('Invalid time command format. Use: time <value>')
        elif command_str.startswith('read_values'):
            # Read Pressure, Time, and Vacuum Command
            try:
                parts = command_str.split(' ')
                if len(parts) == 2:
                    memory_location = int(parts[1])
                else:
                    memory_location = 0  # Default to memory location 0 if not specified
                if 0 <= memory_location <= 399:
                    memory_location_str = f"{memory_location:03d}"
                    response_data = self.send_command('E8', memory_location_str, expect_response=True)
                    if response_data:
                        self.parse_read_values(response_data)
                else:
                    self.logger.error(f'Invalid memory location: {memory_location}. Must be between 0 and 399')
            except ValueError:
                self.logger.error('Invalid memory location format. Use: read_values <memory_location>')
        elif command_str.startswith('set_pressure_units '):
            units_map = {'psi': '00', 'bar': '01', 'kpa': '02'}
            try:
                unit = command_str.split(' ')[1].lower()
                if unit in units_map:
                    units_code = units_map[unit]
                    self.send_command('E6  ', units_code)
                else:
                    self.logger.error(f'Invalid pressure unit: {unit}. Must be one of {list(units_map.keys())}')
            except IndexError:
                self.logger.error('Invalid command format. Use: set_pressure_units <unit>')
        elif command_str.startswith('set_vacuum_units '):
            units_map = {'kpa': '00', 'inches_h2o': '01', 'inches_hg': '02', 'mmhg': '03', 'torr': '04'}
            try:
                unit = command_str.split(' ')[1].lower()
                if unit in units_map:
                    units_code = units_map[unit]
                    self.send_command('E7  ', units_code)
                else:
                    self.logger.error(f'Invalid vacuum unit: {unit}. Must be one of {list(units_map.keys())}')
            except IndexError:
                self.logger.error('Invalid command format. Use: set_vacuum_units <unit>')
        else:
            self.logger.error(f'Unknown command: {command_str}')
    
    def parse_read_values(self, data_str):
        """
        Parses the data received from the E8 command and displays the pressure, time, and vacuum values.
        """
        # Expected format: D0PDppppDTtttttVCvvvv
        try:
            if data_str.startswith('D0'):
                index = 2
                # Parse Pressure
                if data_str[index:index+2] == 'PD':
                    index += 2
                    pressure_value = data_str[index:index+4]
                    index += 4
                    # Convert pressure_value to float
                    pressure = int(pressure_value) / 10.0  # Assuming pressure unit is psi
                    # Parse Time
                    if data_str[index:index+2] == 'DT':
                        index += 2
                        time_value = data_str[index:index+5]
                        index += 5
                        # Convert time_value to float
                        time_sec = int(time_value) / 10000.0
                        # Parse Vacuum
                        if data_str[index:index+2] == 'VC':
                            index += 2
                            vacuum_value = data_str[index:index+4]
                            index += 4
                            # Convert vacuum_value to float
                            vacuum = int(vacuum_value) / 10.0  # Assuming vacuum unit is H2O
                            # Display the values
                            self.logger.info(f"Pressure: {pressure} psi")
                            self.logger.info(f"Time: {time_sec} seconds")
                            self.logger.info(f"Vacuum: {vacuum} H2O")
                        else:
                            self.logger.error("Invalid response format: Missing 'VC'")
                    else:
                        self.logger.error("Invalid response format: Missing 'DT'")
                else:
                    self.logger.error("Invalid response format: Missing 'PD'")
            else:
                self.logger.error("Invalid response format: Missing 'D0'")
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
    
    def check_response(self, response, expect_response=False):
        """
        Handle the response from the dispenser according to the protocol.

        - Parse and process all messages in the response buffer.
        - If the response is a Success Command (A0):
            - For Read commands (expect_response=True):
                - Send ACK (0x06) to indicate readiness to receive data
                - Wait for data response
                - Process data
                - Send EOT (0x04) to end the sequence
            - For Write commands (expect_response=False):
                - Send EOT (0x04) to end the sequence
        - If the response is a Failure Command (A2):
            - Send EOT (0x04) to end the sequence.
        """
        self.logger.debug(f'Received raw response: {response.hex()}')

        # Process response byte by byte
        index = 0
        while index < len(response):
            if response[index] == 0x02:  # STX
                # Start of a message
                index += 1
                # Read length (2 ASCII characters)
                if index + 1 >= len(response):
                    self.logger.warning("Incomplete length in response.")
                    break
                length_str = response[index:index+2].decode('ascii', errors='ignore')
                index += 2
                try:
                    length = int(length_str, 16)
                except ValueError:
                    self.logger.warning("Invalid length in response.")
                    break

                # Read command and data (length bytes)
                if index + length + 2 > len(response):
                    self.logger.warning("Incomplete command/data in response.")
                    break
                command_and_data = response[index:index+length].decode('ascii', errors='ignore')
                index += length

                # Read checksum (2 ASCII characters)
                checksum_str = response[index:index+2].decode('ascii', errors='ignore')
                index += 2

                # Read ETX
                if index >= len(response) or response[index] != 0x03:
                    self.logger.warning("Missing ETX in response.")
                    break
                index += 1  # Skip ETX

                # Verify checksum
                checksum_input_str = length_str + command_and_data
                calculated_checksum = self.calculate_checksum_ascii(checksum_input_str)
                try:
                    received_checksum = int(checksum_str, 16)
                except ValueError:
                    self.logger.warning("Invalid checksum in response.")
                    continue

                if received_checksum != calculated_checksum:
                    self.logger.warning("Checksum mismatch in response.")
                    continue

                # Get command code
                command_code = command_and_data[:2]

                # Handle Success Command (A0) or Failure Command (A2)
                if command_code == 'A0':
                    # Record the end time
                    end_time = time.time()
                    # Calculate the delay in milliseconds
                    if self.start_time:
                        delay = (end_time - self.start_time) * 1000  # Convert to milliseconds
                        self.logger.info(f'Delay time: {delay:.2f} milliseconds')
                    else:
                        self.logger.warning('Start time not recorded. Cannot calculate delay.')

                    self.logger.info('Received Success Command (A0).')
                    if expect_response:
                        # For Read commands
                        self.logger.debug('Sending ACK (0x06) to receive data.')
                        self.ser.write(b'\x06')  # Send ACK
                        time.sleep(0.1)
                        # Wait for data response
                        data_response = self.ser.read(100)
                        if data_response:
                            self.logger.debug(f'Received data response: {data_response.hex()}')
                            # Process data response
                            data_str = self.process_data_response(data_response)
                            # After processing data, send EOT to end the sequence
                            self.logger.debug('Sending EOT (0x04) to end the sequence.')
                            self.ser.write(b'\x04')
                            time.sleep(0.1)
                            return data_str
                        else:
                            self.logger.warning("No data response received.")
                            # Send EOT to end the sequence
                            self.logger.debug('Sending EOT (0x04) to end the sequence.')
                            self.ser.write(b'\x04')
                            time.sleep(0.1)
                    else:
                        # For Write commands
                        self.logger.debug('Sending EOT (0x04) to end the sequence.')
                        self.ser.write(b'\x04')  # Send EOT
                        time.sleep(0.1)
                elif command_code == 'A2':
                    # Record the end time
                    end_time = time.time()
                    # Calculate the delay in milliseconds
                    if self.start_time:
                        delay = (end_time - self.start_time) * 1000  # Convert to milliseconds
                        self.logger.info(f'Delay time: {delay:.2f} milliseconds')
                    else:
                        self.logger.warning('Start time not recorded. Cannot calculate delay.')

                    self.logger.info('Received Failure Command (A2). Sending EOT to end the sequence.')
                    self.ser.write(b'\x04')  # Send EOT
                    time.sleep(0.1)
                else:
                    self.logger.info(f'Received response with command code {command_code}: {command_and_data}')
            else:
                # Unexpected byte, skip
                index += 1
        return None

    def process_data_response(self, response):
        """
        Processes the data response received after sending ACK for a read command.
        """
        self.logger.debug(f'Processing data response: {response.hex()}')
        index = 0
        while index < len(response):
            if response[index] == 0x02:  # STX
                index += 1
                # Read length (2 ASCII characters)
                if index + 1 >= len(response):
                    self.logger.warning("Incomplete length in data response.")
                    break
                length_str = response[index:index+2].decode('ascii', errors='ignore')
                index += 2
                try:
                    length = int(length_str, 16)
                except ValueError:
                    self.logger.warning("Invalid length in data response.")
                    break

                # Read command and data (length bytes)
                if index + length + 2 > len(response):
                    self.logger.warning("Incomplete command/data in data response.")
                    break
                command_and_data = response[index:index+length].decode('ascii', errors='ignore')
                index += length

                # Read checksum (2 ASCII characters)
                checksum_str = response[index:index+2].decode('ascii', errors='ignore')
                index += 2

                # Read ETX
                if index >= len(response) or response[index] != 0x03:
                    self.logger.warning("Missing ETX in data response.")
                    break
                index += 1  # Skip ETX

                # Verify checksum
                checksum_input_str = length_str + command_and_data
                calculated_checksum = self.calculate_checksum_ascii(checksum_input_str)
                try:
                    received_checksum = int(checksum_str, 16)
                except ValueError:
                    self.logger.warning("Invalid checksum in data response.")
                    continue

                if received_checksum != calculated_checksum:
                    self.logger.warning("Checksum mismatch in data response.")
                    continue

                # Process the data
                self.logger.debug(f'Command and Data: {command_and_data}')
                return command_and_data
            else:
                # Unexpected byte, skip
                index += 1
        return None

    def destroy(self):
        if self.ser:
            self.ser.close()
        self.logger.info('Dispenser Controller Stopped')

def main():
    node = DispenserController()
    node.run()

if __name__ == '__main__':
    main()

# Documentation and Command Usage

# This Python script allows you to control the Ultimus V dispenser via RS-232 serial communication. It provides a command-line interface to send commands to the dispenser and receive responses according to the dispenser's communication protocol.

## Commands

# Below is a list of available commands you can use with this script:

# - **start**: Start dispensing.
#    - Sends the `DI  ` command to the dispenser.

# - **stop**: Stop dispensing.
#    - Sends the `DO  ` command to the dispenser.

# - **pressure `<value>`**: Set the dispense pressure.
#    - Replace `<value>` with a float
#    - psi: 0.0-100.0
#    - kPa: 0.0-689.5
#    - Bar: 0.000-6.895
#    - Sends the `PS  ` command with the formatted pressure value.

# - **vacuum `<value>`**: Set the vacuum level.
#    - Replace `<value>` with a float
#    - H2O: 0.0-18.0
#    - kPa: 0.00-4.48
#    - Hg 0.00-1.32
#    - mmHg or Torr: 0.0-33.6
#    - Sends the `VS  ` command with the formatted vacuum value.

# - **toggle_mode**: Toggle between timed and steady modes.
#    - Sends the `TM  ` command.
#    - Updates the internal state to reflect the current mode.

# - **time `<value>`**: Set the dispense time.
#    - Replace `<value>` with a float between `0.0000` and `9.9999` (seconds).
#    - Sends the `DS  ` command with the formatted time value.

# - **read_values `<memory_location>`**: Read the pressure, time, and vacuum values from a specified memory location.
#    - Replace `<memory_location>` with an integer between `0` and `399`.
#    - Sends the `E8` command with the memory location.
#    - Displays the retrieved values.

# - **set_pressure_units `<unit>`**: Set the pressure units.
#    - Replace `<unit>` with one of the following: `psi`, `bar`, `kpa`.
#    - Sends the `E6  ` command with the unit code.

# - **set_vacuum_units `<unit>`**: Set the vacuum units.
#    - Replace `<unit>` with one of the following: `kpa`, `inches_h2o`, `inches_hg`, `mmhg`, `torr`.
#    - Sends the `E7  ` command with the unit code.

# - **exit**: Exit the script.

## Notes

# - Ensure the dispenser is connected and the correct serial port is selected.
# - The script automatically searches for available serial ports and attempts to connect.
# - The communication protocol strictly follows the dispenser's RS-232 specifications.
# - Logging is set to `DEBUG` level to provide detailed information about the communication process.
# - Adjust `time.sleep()` durations if necessary to accommodate the dispenser's response times.

## Requirements

# - Python 3.x
# - `pyserial` library
#    ```
#    pip install pyserial
#    ```

## Running the Script

# Run the script using Python 3:

# ```bash
# python3 nordson_dispenser_controller.py