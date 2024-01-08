from pymodbus.client.sync import ModbusTcpClient

# Define the RS485 to TCP gateway address
gateway_ip = "10.100.10.216"
gateway_port = 4257

# Define the Modbus device address and register range
device_address = 1  # Change this to your Modbus device address
start_register = 1000  # Change this to your start register
num_registers = 100  # Change this to the number of registers you want to read

# reading input registrar 1014 is battery soc
#


def charge_battery():
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(gateway_ip, port=gateway_port)

        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]

        # BF1
        client.write_registers(1100, on, unit=1)
        # LF1
        client.write_registers(1110, off, unit=1)
        # GF1
        client.write_registers(1080, off, unit=1)
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close the Modbus TCP connection
        if client:
            client.close()


def discharge_battery():
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(gateway_ip, port=gateway_port)

        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]

        # BF1
        client.write_registers(1100, off, unit=1)
        # LF1
        client.write_registers(1110, on, unit=1)
        # GF1
        client.write_registers(1080, off, unit=1)
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close the Modbus TCP connection
        if client:
            client.close()


def read_modbus_registers():
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(gateway_ip, port=gateway_port)

        # Read the specified range of registers from the Modbus device
        response = client.read_input_registers(
            start_register, num_registers, unit=device_address
        )

        client.write_register(1102, 0, unit=1)  # 'unit' is the Modbus unit ID

        # Check if the response is valid
        if response.isError():
            print(f"Modbus error: {response}")
        else:
            # Print the values of the read registers
            print(f"Read {num_registers} registers:")
            for i in range(num_registers):
                print(f"Register {start_register + i}: {response.registers[i]}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close the Modbus TCP connection
        if client:
            client.close()


if __name__ == "__main__":
    discharge_battery()
