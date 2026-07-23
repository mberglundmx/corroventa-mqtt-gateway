# Changelog

## 0.2.6

- Device time sensor: minute resolution + diagnostic (avoids HA logbook spam)

## 0.2.5

- Service days: uint16 LE at Telemetry `[23:25]` (was low byte only → e.g. 106 instead of 362)

## 0.2.4

- Reported config as HA sensors (MGI/mode/fan) alongside controls
- Log telemetry publish and warn when Telemetry never arrives
- Safer JSON publish for config state

## 0.2.3

- Log ConfigWrite fan/yy + full frame hex
- Publish config to MQTT immediately after TX (optimistic HA state)

## 0.2.2

- Discovery topic logging + MQTT `origin`
- Docs: no HA notification for discovery

## 0.2.1

- `radio_mode: ys1` (backend name, not hw/soft)

## 0.2.0

- VLEN + HW CRC RX path; first-RX kind logging

## 0.1.0

- Initial MQTT gateway + Home Assistant add-on scaffolding
- HA MQTT discovery for telemetry sensors and config controls
- ConfigWrite merge-on-command (state from ConfigStatus)
- Protocol via **pybind11** (`corroventa-protocol`), not a Python codec fork
- Vendored Yard Stick transport package
