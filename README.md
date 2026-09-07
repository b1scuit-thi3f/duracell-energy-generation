# Duracell Energy Generation

Home Assistant custom integration for Duracell Energy monitoring systems.

## Features

- Live inverter, battery, grid, and load sensors
- Real-time flow and availability data
- Daily, monthly, and yearly energy statistics
- Current inverter fault monitoring
- Schedule register reading and updates
- Authenticated local HTTP endpoints for stored chart data

## Installation

Install through HACS by adding this repository as a custom repository, or copy
`custom_components/duracell_energy_generation` into your Home Assistant
`custom_components` directory.

Then restart Home Assistant and add **Duracell Energy Generation** from
Settings > Devices & services.

## Requirements

The integration installs `pycryptodomex` automatically from its manifest.

## Disclaimer

This project is not affiliated with or endorsed by Duracell Energy.
