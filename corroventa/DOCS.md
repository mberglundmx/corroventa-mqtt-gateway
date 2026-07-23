# Corroventa MQTT Gateway add-on

## What it does

Listens on 868 MHz (Yard Stick One) for Corroventa CTR frames, publishes
telemetry and configuration to MQTT, and accepts configuration changes from
Home Assistant via MQTT discovery entities.

## Requirements

- Home Assistant OS or Supervised
- Mosquitto (or other MQTT broker) + HA MQTT integration
- Yard Stick One plugged into the HA machine

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `log_level` | `info` | Use `debug` to see every RX frame |
| `radio_mode` | `ys1` | Radio backend (`ys1` = Yard Stick One; only option today) |
| `radio_enabled` | `true` | Set `false` for MQTT-only debugging |
| `tx_repeats` | `8` | ConfigWrite air repeats |
| `topic_prefix` | `corroventa` | MQTT root |
| `discovery_prefix` | `homeassistant` | HA discovery root |

MQTT credentials normally come from the Supervisor MQTT service. Optional
`mqtt_*` fields override that.

## Entities

After the first `ConfigStatus` from the CTR, discovery is published under the
MQTT integration. There is **no** notification bell — look in:

**Settings → Devices & services → MQTT → devices**

Device name: **Corroventa \<ui-id\>** (e.g. `Corroventa 1348002652`).

Discovery topics look like:
`homeassistant/sensor/corroventa_<id>/temperature/config`
