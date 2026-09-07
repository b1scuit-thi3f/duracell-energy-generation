# Duracell Energy Generation

Home Assistant custom integration for Duracell Energy monitoring systems.

## Features

- Live inverter, battery, grid, and load sensors
- Real-time flow and availability data
- Daily, monthly, and yearly energy statistics
- Current inverter fault monitoring
- Schedule register reading and updates, including setting charge and discharge schedules
- Authenticated local HTTP endpoints for stored chart data

## Installation

Install through HACS by adding this repository as a custom repository, or copy
`custom_components/duracell_energy_generation` into your Home Assistant
`custom_components` directory.

Then restart Home Assistant and add **Duracell Energy Generation** from
Settings > Devices & services.

## Schedule control

The integration exposes the inverter's charge and discharge schedules as
diagnostic sensors and provides these services:

- `duracell_energy_generation.refresh_schedule` refreshes the current schedules.
- `duracell_energy_generation.set_schedule` updates a schedule's frequency,
  charge or discharge times, power, and battery state-of-charge limits.

For example:

```yaml
action: duracell_energy_generation.set_schedule
data:
  schedule: 1
  frequency: Everyday
  charge_start_time: "01:00:00"
  charge_end_time: "05:00:00"
  charge_power_w: 6000
  charge_end_soc_percent: 100
```

## Requirements

The integration installs `pycryptodomex` automatically from its manifest.

## Disclaimer

This project is not affiliated with or endorsed by Duracell Energy.
