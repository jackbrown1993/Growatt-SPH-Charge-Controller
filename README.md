<h1 align="center">Growatt SPH Charge Controller</h1>

<p align="center">
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

<h2>Project Purpose</h2>

To provide an easy method of charging batteries connected to a Growatt SPH inverter using MQTT. This has only been tested on my Growatt SPH5000 with three GBLI6532 6.5kWh batteries connected. I suspect this will work for other Growatt hybrid inverters too.

<h2>Docker</h2>
docker-compose example using published image: docker-compose.yml

docker-compose example with image built locally: docker-compose.dev.yml

<h3>Inspirations and Credits</h3>

- https://github.com/jackbrown1993/growatt-weather-based-charger
- Tommy Fer over at https://community.home-assistant.io/t/esphome-modbus-growatt-shinewifi-s/369171/323