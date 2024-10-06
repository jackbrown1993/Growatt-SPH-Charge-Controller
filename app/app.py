import os
import sys
import logging
import asyncio
from pymodbus.client.sync import ModbusTcpClient

import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
log = logging.getLogger("__name__")

# MQTT environment variables with default values
mqtt_port = int(os.environ.get("MQTT_PORT", 1883))  # Default MQTT port
mqtt_ip = os.environ.get("MQTT_IP")  # MQTT broker IP address
mqtt_user = os.environ.get("MQTT_USER")  # MQTT broker username
mqtt_password = os.environ.get("MQTT_PASSWORD")  # MQTT broker password
rs485_tcp_gateway_ip = os.environ.get("RS485_TCP_GATEWAY_IP")  # Modbus TCP gateway IP
rs485_tcp_gateway_port = os.environ.get(
    "RS485_TCP_GATEWAY_PORT"
)  # Modbus TCP gateway port

# Check if required environment variables are set
if not all(
    [mqtt_ip, mqtt_user, mqtt_password, rs485_tcp_gateway_ip, rs485_tcp_gateway_port]
):
    log.error("Missing required environment variables. Please check the configuration.")
    sys.exit(1)


# Initialize and start MQTT client
# Initialize and start MQTT client
async def start_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client("growatt-rs485-mqtt-client", callback_api_version=5)
    mqtt_client.username_pw_set(username=mqtt_user, password=mqtt_password)
    mqtt_client.on_connect = on_connect  # Set callback for connection
    mqtt_client.on_message = on_message  # Set callback for received messages
    mqtt_client.on_disconnect = on_disconnect  # Set callback for disconnection
    mqtt_client.on_publish = on_publish  # Set callback for publishing
    mqtt_client.on_subscribe = on_subscribe  # Set callback for subscribing

    try:
        mqtt_client.connect(mqtt_ip, mqtt_port)  # Connect to the MQTT broker
        mqtt_client.loop_start()  # Start the loop in a separate thread
        log.info("MQTT connection started.")

        # Publish initial messages to topics
        mqtt_client.publish(
            "growatt_rs485/growatt_battery_charge",
            payload="unknown",
            qos=0,
            retain=False,
        )
        mqtt_client.publish(
            "growatt_rs485/growatt_battery_charge/set",
            payload="unknown",
            qos=0,
            retain=False,
        )

    except Exception as e:
        log.error(f"Failed to connect to MQTT broker: {e}")



# Callback when successfully connected to the MQTT broker
def on_connect(mqttc, obj, flags, rc):
    if rc == 0:
        log.info("Connected to MQTT broker.")
        mqtt_client.subscribe(
            "growatt_rs485/growatt_battery_charge/set"
        )  # Subscribe to a topic
    else:
        log.error(f"Failed to connect to MQTT broker. Return code: {rc}")


# Callback when a message is received from MQTT
def on_message(mqttc, obj, msg):
    log.info(
        f"MQTT message received: topic={msg.topic}, payload={msg.payload.decode()}"
    )
    if msg.topic == "growatt_rs485/growatt_battery_charge/set":
        handle_battery_command(msg.payload.decode())  # Handle battery control command


# Callback when disconnected from the MQTT broker
def on_disconnect(mqttc, obj, rc):
    if rc != 0:
        log.warning("Unexpected disconnection from MQTT broker.")
    else:
        log.info("Disconnected from MQTT broker.")


# Callback when a message is successfully published to MQTT
def on_publish(mqttc, obj, mid):
    log.info(f"Message {mid} published to MQTT broker.")


# Callback when subscribing to an MQTT topic
def on_subscribe(mqttc, obj, mid, granted_qos):
    log.info(f"Subscribed to topic with message ID {mid}, QoS: {granted_qos}")


# Handle battery control commands received via MQTT
def handle_battery_command(command):
    if command == "on":
        log.info("Starting battery charging.")
        charge_battery()  # Charge the battery
    elif command == "off":
        log.info("Stopping battery charging.")
        discharge_battery()  # Stop charging (discharge battery)
    else:
        log.error(f"Unhandled battery command: {command}")


# Function to start battery charging
def charge_battery():
    try:
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]
        client.write_registers(
            1100, on, unit=1
        )  # (BF1) Send Modbus command to start charging
        client.write_registers(1110, off, unit=1)  # LF1
        client.write_registers(1080, off, unit=1)  # GF1
    except Exception as e:
        log.error(f"Error during battery charging: {e}")
    finally:
        if client:
            client.close()


# Function to discharge the battery (stop charging)
def discharge_battery():
    try:
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]
        client.write_registers(
            1100, off, unit=1
        )  # (BF1) Send Modbus command to stop charging
        client.write_registers(1110, on, unit=1)  # LF1
        client.write_registers(1080, off, unit=1)  # GF1
    except Exception as e:
        log.error(f"Error during battery discharging: {e}")
    finally:
        if client:
            client.close()


# Check the status of battery charging
def check_charge_status():
    try:
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        inverter_mode = client.read_holding_registers(1044, int=1, unit=1)
        # BF1 - Battery First Mode: battery charging
        if inverter_mode.registers[0] == 1:
            log.info("Inverter mode: Battery First (Battery charging)")
            mqtt_client.publish("growatt_rs485/growatt_battery_charge", payload="on")
        # LF1 - Load First Mode: battery discharging
        elif inverter_mode.registers[0] == 0:
            log.info("Inverter mode: Load First (Battery discharging)")
            mqtt_client.publish("growatt_rs485/growatt_battery_charge", payload="off")
        # GF1 - Grid First Mode: battery not in use
        elif inverter_mode.registers[0] == 2:
            log.info("Inverter mode: Grid First (Battery not in use)")
            mqtt_client.publish("growatt_rs485/growatt_battery_charge", payload="off")
        else:
            log.error("Unknown inverter mode")
    except Exception as e:
        log.error(f"Error checking charge status: {e}")
    finally:
        if client:
            client.close()


# Main application loop
async def start_app():
    await start_mqtt()  # Start the MQTT client
    try:
        while True:
            check_charge_status()  # Periodically check battery status
            await asyncio.sleep(5)  # Wait 5 seconds between checks
    except Exception as e:
        log.error(f"Error in main loop: {e}")
    finally:
        log.info("Shutting down MQTT client.")
        mqtt_client.disconnect()  # Gracefully disconnect from MQTT


# Entry point of the application
if __name__ == "__main__":
    asyncio.run(start_app())  # Start the application using asyncio
