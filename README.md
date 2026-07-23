# Corroventa MQTT Gateway

Reverse-engineered Corroventa CTR ↔ HomeVision RF bridge for Home Assistant.

Publishes telemetry/config over MQTT with **MQTT discovery**. Commands on
`config/set` are merged into a full `ConfigWrite` and sent via Yard Stick One.

## Install in Home Assistant (add-on repository)

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**
2. Add: `https://github.com/mberglundmx/corroventa-mqtt-gateway`
3. Refresh the store, install **Corroventa MQTT Gateway**
4. Install/configure **Mosquitto** (or another broker) + HA **MQTT** integration
5. Plug in a **Yard Stick One**, start the add-on
6. Watch logs for `Published HA discovery for device …` / learned HV prefix

### Update to a newer version

Supervisor does **not** auto-poll git every commit. After we bump `corroventa/config.yaml`:

1. **Settings → Add-ons → Add-on store → ⋮ → Check for updates**
2. Open **Corroventa MQTT Gateway** → **Update** (rebuilds the image)
3. Confirm the add-on page shows version **0.2.4** (or newer)

If it still says 0.1.0: remove the repository, re-add
`https://github.com/mberglundmx/corroventa-mqtt-gateway`, check for updates again.
A plain **Restart** does not pull new code.

USB passthrough is declared in the add-on (`usb`, `/dev/bus/usb`).

## Repository layout (HA convention)

```
repository.yaml          # add-on store metadata
corroventa/              # add-on slug (= folder name)
  config.yaml            # Supervisor options / schema
  build.yaml
  Dockerfile             # build context = this folder only
  run.sh                 # bashio → python -m corroventa_gateway
  requirements.txt       # paho-mqtt, pyusb, rfcat (rflib)
  corroventa_gateway/    # application
  vendor/                # protocol sources + yardstick transport
```

## MQTT (HA best practice)

Device id = CTR UI id (e.g. `1348002652`).

| Topic | Role |
|-------|------|
| `corroventa/device/<id>/availability` | `online` / `offline` |
| `corroventa/device/<id>/telemetry` | RO JSON (RH, temp, fan, …) |
| `corroventa/device/<id>/config` | Config **state** (from ConfigStatus) |
| `corroventa/device/<id>/config/set` | Config **command** → ConfigWrite |
| `corroventa/device/<id>/statistics` | RO JSON (12-month stats) |

Discovery prefix: `homeassistant/` (configurable).

Example command:

```bash
mosquitto_pub -t corroventa/device/1348002652/config/set -m '{"mgi": -7}'
```

## Dependencies

- **Protocol:** C++ `corroventa-protocol` via **pybind11** (built in the Dockerfile)
- **Radio:** vendored `corroventa_radio_yardstick` + **`rfcat`/`rflib`** (pip) + libusb

## Standalone (dev)

```bash
cmake -S ../corroventa-protocol -B ../corroventa-protocol/build-python \
  -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON -DCORROVENTA_PROTOCOL_BUILD_TESTS=OFF
cmake --build ../corroventa-protocol/build-python -j

cd corroventa
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="$(pwd):$(pwd)/vendor:../../corroventa-protocol/build-python"
export MQTT_HOST=127.0.0.1 MQTT_PORT=1883 RADIO_MODE=hw
python -m corroventa_gateway
```
