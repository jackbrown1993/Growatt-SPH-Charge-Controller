import os
import sys
import logging
import asyncio
import paho.mqtt.client as mqtt
from pymodbus.client.sync import ModbusTcpClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
log = logging.getLogger("__name__")

# Check environment variables
if "MQTT_PORT" not in os.environ:
    mqtt_port = 1883
else:
    mqtt_port = int(os.environ.get("MQTT_PORT"))

if "MQTT_IP" not in os.environ:
    log.error(
        "MQTT IP not provided, please provide IP address or hostname of your MQTT server."
    )
    sys.exit(1)
else:
    mqtt_ip = os.environ.get("MQTT_IP")

if "MQTT_USER" not in os.environ:
    log.error("MQTT user not provided, please provide username of your MQTT server.")
    sys.exit(1)
else:
    mqtt_user = os.environ.get("MQTT_USER")

if "MQTT_PASSWORD" not in os.environ:
    log.error(
        "MQTT password not provided, please provide password of your MQTT server."
    )
    sys.exit(1)
else:
    mqtt_password = os.environ.get("MQTT_PASSWORD")

if "RS485_TCP_GATEWAY_IP" not in os.environ:
    log.error(
        "IP for the RS485 TCP Gateway not provided, please provide IP address or hostname of your RS485 to TCP adaptor / server."
    )
    sys.exit(1)
else:
    rs485_tcp_gateway_ip = os.environ.get("RS485_TCP_GATEWAY_IP")

if "RS485_TCP_GATEWAY_PORT" not in os.environ:
    log.error(
        "Port for the RS485 TCP Gateway not provided, please provide the port of your RS485 to TCP adaptor / server."
    )
    sys.exit(1)
else:
    rs485_tcp_gateway_port = int(
        os.environ.get("RS485_TCP_GATEWAY_PORT")
    )


async def start_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client("growatt-rs485-mqtt-client")
    mqtt_client.username_pw_set(username=mqtt_user, password=mqtt_password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_ip, mqtt_port)
    mqtt_client.loop_start()

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


def on_connect(mqttc, obj, flags, rc):
    """This is triggered whenever we connect to MQTT"""
    log.info("Connected to MQTT.")
    # Subscribe to MQTT
    mqtt_client.subscribe("growatt_rs485/growatt_battery_charge/set")


def on_message(mqttc, obj, msg):
    """This is triggered whenever we receive a message on MQTT"""
    log.info(
        "MQTT message received on topic: "
        + msg.topic
        + " with value: "
        + msg.payload.decode()
    )
    if msg.topic == "growatt_rs485/growatt_battery_charge/set":
        new_state = msg.payload.decode()

        if new_state == "on":
            log.info("Received request to start charging batteries.")
            asyncio.run(charge_battery())
        elif new_state == "off":
            log.info("Received request to stop charging batteries.")
            asyncio.run(discharge_battery())
        else:
            log.info("Unhandled MQTT message on topic {}.".format(msg.topic))
    else:
        log.debug("Unhandled MQTT message on topic {}.".format(msg.topic))


async def charge_battery():
    client = None
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        client.connect()  # Ensure the client is connected

        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]

        # BF1
        client.write_registers(1100, on, unit=1)
        # LF1
        client.write_registers(1110, off, unit=1)
        # GF1
        client.write_registers(1080, off, unit=1)
    except Exception as e:
        log.error(f"Error while charging battery: {e}")

    finally:
        # Close the Modbus TCP connection
        if client:
            client.close()


async def discharge_battery():
    client = None
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        client.connect()  # Ensure the client is connected

        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]

        # BF1
        client.write_registers(1100, off, unit=1)
        # LF1
        client.write_registers(1110, on, unit=1)
        # GF1
        client.write_registers(1080, off, unit=1)
    except Exception as e:
        log.error(f"Error while discharging battery: {e}")

    finally:
        # Close the Modbus TCP connection
        if client:
            client.close()


async def check_charge_status():
    client = None
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        client.connect()  # Ensure the client is connected

        # 0 = Load First (Battery Discharging)
        # 1 = Battery First (Battery Charging)
        # 2 = Grid First
        inverter_mode = client.read_holding_registers(1044, count=1, unit=1)

        if inverter_mode.registers[0] == 0:
            log.info(
                "Inverter mode is 'Load First', so battery is serving load / charging from PV."
            )
            mqtt_client.publish(
                "growatt_rs485/growatt_battery_charge",
                payload="off",
                qos=0,
                retain=False,
            )
        elif inverter_mode.registers[0] == 1:
            log.info(
                "Inverter mode is 'Battery First', so battery is charging from grid."
            )
            mqtt_client.publish(
                "growatt_rs485/growatt_battery_charge",
                payload="on",
                qos=0,
                retain=False,
            )
        elif inverter_mode.registers[0] == 2:
            log.info("Inverter mode is 'Grid First', so battery isn't being used.")
            mqtt_client.publish(
                "growatt_rs485/growatt_battery_charge",
                payload="off",
                qos=0,
                retain=False,
            )
        else:
            log.error("Unable to determine battery charge status.")

    except Exception as e:
        log.error(f"Error while checking charge status: {e}")

    finally:
        # Close the Modbus TCP connection
        if client:
            client.close()


async def start_app():
    global mqtt_client
    # Connect to MQTT
    await start_mqtt()

    try:
        # Run the event loop indefinitely to keep the script alive
        while True:
            await check_charge_status()
            await asyncio.sleep(5)  # Adjust sleep duration as needed
    finally:
        log.info("Disconnecting from MQTT")
        mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(start_app())
