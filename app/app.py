import os
import sys
import logging
import asyncio
from pymodbus.client.sync import ModbusTcpClient

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s")
log = logging.getLogger("__name__")

# MQTT environment variables with default values
mqtt_port = int(os.environ.get("MQTT_PORT", 1883))
mqtt_ip = os.environ.get("MQTT_IP")
mqtt_user = os.environ.get("MQTT_USER")
mqtt_password = os.environ.get("MQTT_PASSWORD")
rs485_tcp_gateway_ip = os.environ.get("RS485_TCP_GATEWAY_IP")
rs485_tcp_gateway_port = os.environ.get("RS485_TCP_GATEWAY_PORT")

# Exit if required environment variables are not set
if not all([mqtt_ip, mqtt_user, mqtt_password, rs485_tcp_gateway_ip, rs485_tcp_gateway_port]):
    log.error("Missing required environment variables. Please check the configuration.")
    sys.exit(1)


async def start_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client("growatt-rs485-mqtt-client")
    mqtt_client.username_pw_set(username=mqtt_user, password=mqtt_password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish = on_publish
    mqtt_client.on_subscribe = on_subscribe

    try:
        mqtt_client.connect(mqtt_ip, mqtt_port)
        mqtt_client.loop_start()
        log.info("MQTT connection started.")
        
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


def on_connect(mqttc, obj, flags, rc):
    """Callback when connected to MQTT"""
    if rc == 0:
        log.info("Connected to MQTT broker.")
        mqtt_client.subscribe("growatt_rs485/growatt_battery_charge/set")
    else:
        log.error(f"Failed to connect to MQTT broker. Return code: {rc}")


def on_message(mqttc, obj, msg):
    """Callback when receiving an MQTT message"""
    log.info(f"MQTT message received: topic={msg.topic}, payload={msg.payload.decode()}")
    if msg.topic == "growatt_rs485/growatt_battery_charge/set":
        handle_battery_command(msg.payload.decode())


def on_disconnect(mqttc, obj, rc):
    """Callback when disconnected from MQTT"""
    if rc != 0:
        log.warning("Unexpected disconnection from MQTT broker.")
    else:
        log.info("Disconnected from MQTT broker.")


def on_publish(mqttc, obj, mid):
    """Callback when an MQTT message is published"""
    log.info(f"Message {mid} published to MQTT broker.")


def on_subscribe(mqttc, obj, mid, granted_qos):
    """Callback when an MQTT topic is subscribed to"""
    log.info(f"Subscribed to topic with message ID {mid}, QoS: {granted_qos}")


def handle_battery_command(command):
    """Handle incoming MQTT messages for battery control"""
    if command == "on":
        log.info("Starting battery charging.")
        charge_battery()
    elif command == "off":
        log.info("Stopping battery charging.")
        discharge_battery()
    else:
        log.error(f"Unhandled battery command: {command}")


def charge_battery():
    try:
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]
        client.write_registers(1100, on, unit=1)
        client.write_registers(1110, off, unit=1)
        client.write_registers(1080, off, unit=1)
    except Exception as e:
        log.error(f"Error during battery charging: {e}")
    finally:
        if client:
            client.close()


def discharge_battery():
    try:
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        on = [0, 23 * 256 + 59, 1]
        off = [0, 23 * 256 + 59, 0]
        client.write_registers(1100, off, unit=1)
        client.write_registers(1110, on, unit=1)
        client.write_registers(1080, off, unit=1)
    except Exception as e:
        log.error(f"Error during battery discharging: {e}")
    finally:
        if client:
            client.close()


def check_charge_status():
    try:
        client = ModbusTcpClient(rs485_tcp_gateway_ip, port=rs485_tcp_gateway_port)
        inverter_mode = client.read_holding_registers(1044, int=1, unit=1)
        if inverter_mode.registers[0] == 0:
            log.info("Inverter mode: Load First (Battery discharging)")
            mqtt_client.publish("growatt_rs485/growatt_battery_charge", payload="off")
        elif inverter_mode.registers[0] == 1:
            log.info("Inverter mode: Battery First (Battery charging)")
            mqtt_client.publish("growatt_rs485/growatt_battery_charge", payload="on")
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


async def start_app():
    await start_mqtt()
    try:
        while True:
            check_charge_status()
            await asyncio.sleep(5)
    except Exception as e:
        log.error(f"Error in main loop: {e}")
    finally:
        log.info("Shutting down MQTT client.")
        mqtt_client.disconnect()


if __name__ == "__main__":
    asyncio.run(start_app())
