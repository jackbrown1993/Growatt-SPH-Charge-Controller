import os
import sys
import logging
import asyncio
from pymodbus.client.sync import ModbusTcpClient

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
log = logging.getLogger("__name__")

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

if "INVERTER_IP" not in os.environ:
    log.error(
        "Growatt inverter IP not provided, please provide IP address or hostname of your Growatt inverter."
    )
    sys.exit(1)
else:
    inverter_ip = os.environ.get("INVERTER_IP")

if "INVERTER_PORT" not in os.environ:
    log.error(
        "Growatt inverter port not provided, please provide port of your Growatt inverter."
    )
    sys.exit(1)
else:
    inverter_port = os.environ.get("INVERTER_PORT")

if "MQTT_PORT" not in os.environ:
    mqtt_port = 1883
else:
    mqtt_port = int(os.environ.get("MQTT_PORT"))


async def start_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client("growatt-charge-client")
    mqtt_client.username_pw_set(username=mqtt_user, password=mqtt_password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_ip, mqtt_port)
    mqtt_client.loop_start()

    mqtt_client.publish(
        "growatt_charge_script/charge_state/actual",
        payload="unknown",
        qos=0,
        retain=False,
    )

    mqtt_client.publish(
        "growatt_charge_script/charge_state/desired",
        payload="unknown",
        qos=0,
        retain=False,
    )

    # Subscribe to MQTT
    mqtt_client.subscribe("growatt_charge_script/charge_state/desired")


def on_connect(mqttc, obj, flags, rc):
    """This is triggered whenever we connect to MQTT"""
    log.info("Connected to MQTT.")


def on_message(mqttc, obj, msg):
    """This is triggered whenever we recieve a message on MQTT"""
    global spa
    log.info(
        "MQTT message received on topic: "
        + msg.topic
        + " with value: "
        + msg.payload.decode()
    )
    if msg.topic == "growatt_charge_script/charge_state/desired":
        new_state = msg.payload.decode()

        if new_state == "charge":
            log.info("Received request to start charging batteries.")
            charge_battery()
        elif new_state == "discharge":
            log.info("Received request to stop charging batteries.")
            discharge_battery()
        else:
            log.info("Unhandled MQTT message on topic {}.".format(msg.topic))
    else:
        log.debug("Unhandled MQTT message on topic {}.".format(msg.topic))


def charge_battery():
    try:
        # Connect to the Modbus TCP server (RS485 to TCP gateway)
        client = ModbusTcpClient(inverter_ip, port=inverter_port)

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
        client = ModbusTcpClient(inverter_ip, port=inverter_port)

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


async def start_app():
    global mqtt_client
    # Connect to MQTT
    await start_mqtt()

    try:
        # Run the event loop indefinitely to keep the script alive
        while True:
            await asyncio.sleep(1)  # Adjust sleep duration as needed
    finally:
        mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(start_app())
