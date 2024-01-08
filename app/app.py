import os
import sys
import logging

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
    if msg.topic == "homie/growatt/set_charge-state/set":
        new_state = msg.payload.decode()

        if (new_state == 'charge'):
            start_charge()
        else:
            stop_charge
    else:
        log.debug("Unhandled MQTT message on topic {}.".format(msg.topic))


def start_charge():
    # Tell SPH to immediately start charging batteries
    return True


def stop_charge():
    # Tell SPH to immediately stop charging batteries
    return True
