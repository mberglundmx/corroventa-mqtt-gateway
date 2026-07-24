from __future__ import annotations

import json
import logging
from typing import Any, Callable

import paho.mqtt.client as mqtt

from corroventa_protocol import ConfigBlock

from .settings import Settings

log = logging.getLogger(__name__)


class HaMqtt:
    """MQTT client with Home Assistant MQTT discovery."""

    def __init__(
        self,
        settings: Settings,
        on_config_command: Callable[[int, dict[str, Any]], None],
    ) -> None:
        self.settings = settings
        self._on_config_command = on_config_command
        self._discovered: set[int] = set()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt_client_id,
        )
        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def start(self) -> None:
        log.info(
            "Connecting MQTT %s:%s",
            self.settings.mqtt_host,
            self.settings.mqtt_port,
        )
        import time

        delay = 1.0
        for attempt in range(1, 31):
            try:
                self._client.connect(
                    self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60
                )
                break
            except OSError as exc:
                log.warning("MQTT connect attempt %s failed: %s", attempt, exc)
                time.sleep(delay)
                delay = min(delay * 1.5, 10.0)
        else:
            raise RuntimeError("MQTT broker unreachable")
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def device_base(self, device_id: int) -> str:
        return f"{self.settings.topic_prefix}/device/{device_id}"

    def publish_availability(self, device_id: int, online: bool = True) -> None:
        topic = f"{self.device_base(device_id)}/availability"
        self._client.publish(topic, "online" if online else "offline", retain=True, qos=1)

    def publish_telemetry(self, device_id: int, payload: dict[str, Any]) -> None:
        self._ensure_discovery(device_id)
        topic = f"{self.device_base(device_id)}/telemetry"
        body = json.dumps(payload)
        self._client.publish(topic, body, retain=True, qos=1)
        log.info(
            "Published telemetry device=%s T=%s RH=%s fan=%s",
            device_id,
            payload.get("temperature_c"),
            payload.get("relative_humidity_percent"),
            payload.get("fan_running"),
        )

    def publish_config(self, device_id: int, config: ConfigBlock) -> None:
        self._ensure_discovery(device_id)
        topic = f"{self.device_base(device_id)}/config"
        payload = dict(config.to_public_dict())
        self._client.publish(topic, json.dumps(payload), retain=True, qos=1)

    def publish_statistics(self, device_id: int, payload: dict[str, Any]) -> None:
        self._ensure_discovery(device_id)
        topic = f"{self.device_base(device_id)}/statistics"
        self._client.publish(topic, json.dumps(payload), retain=True, qos=1)
        log.info("Published statistics device=%s", device_id)

    def _on_connect(self, client: mqtt.Client, *_args: Any) -> None:
        log.info("MQTT connected")
        # Commands for any known/future device id under our prefix.
        topic = f"{self.settings.topic_prefix}/device/+/config/set"
        client.subscribe(topic, qos=1)
        log.info("Subscribed %s", topic)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        parts = msg.topic.split("/")
        # corroventa/device/<id>/config/set
        if len(parts) < 5 or parts[-2:] != ["config", "set"]:
            return
        try:
            device_id = int(parts[-3])
            patch = json.loads(msg.payload.decode("utf-8"))
            if not isinstance(patch, dict):
                raise ValueError("command payload must be a JSON object")
        except Exception as exc:
            log.warning("Bad config command on %s: %s", msg.topic, exc)
            return
        log.info("Config command device=%s patch=%s", device_id, patch)
        self._on_config_command(device_id, patch)

    def _ensure_discovery(self, device_id: int) -> None:
        if device_id in self._discovered:
            return
        self._publish_discovery(device_id)
        self._discovered.add(device_id)
        self.publish_availability(device_id, True)

    def _publish_discovery(self, device_id: int) -> None:
        prefix = self.settings.discovery_prefix
        base = self.device_base(device_id)
        avail = f"{base}/availability"
        node = f"corroventa_{device_id}"
        device = {
            "identifiers": [node],
            "name": f"Corroventa {device_id}",
            "manufacturer": "Corroventa",
            "model": self.settings.device_model,
            "sw_version": "gateway-0.2.11",
        }
        origin = {
            "name": "Corroventa MQTT Gateway",
            "sw_version": "0.2.11",
            "support_url": "https://github.com/mberglundmx/corroventa-mqtt-gateway",
        }

        def pub(component: str, object_id: str, payload: dict[str, Any]) -> None:
            topic = f"{prefix}/{component}/{node}/{object_id}/config"
            payload = {
                **payload,
                "availability_topic": avail,
                "payload_available": "online",
                "payload_not_available": "offline",
                "device": device,
                "origin": origin,
                "unique_id": f"{node}_{object_id}",
            }
            self._client.publish(topic, json.dumps(payload), retain=True, qos=1)
            log.info("Discovery → %s", topic)

        tel = f"{base}/telemetry"
        cfg = f"{base}/config"
        cfg_set = f"{base}/config/set"
        stats = f"{base}/statistics"

        # Reported config as sensors (Controls are number/switch; these show under Sensors).
        pub(
            "sensor",
            "mgi_reported",
            {
                "name": "MGI reported",
                "state_topic": cfg,
                "value_template": "{{ value_json.mgi }}",
                "unit_of_measurement": "%",
                "state_class": "measurement",
            },
        )
        pub(
            "sensor",
            "mode_reported",
            {
                "name": "Control mode reported",
                "state_topic": cfg,
                "value_template": "{{ value_json.mgi_mode }}",
            },
        )
        pub(
            "binary_sensor",
            "continuous_fan_reported",
            {
                "name": "Continuous fan reported",
                "state_topic": cfg,
                "value_template": "{{ 'ON' if value_json.continuous_fan else 'OFF' }}",
                "payload_on": "ON",
                "payload_off": "OFF",
            },
        )
        pub(
            "sensor",
            "alarm_rf_reported",
            {
                "name": "Alarm RF reported",
                "state_topic": cfg,
                "value_template": "{{ value_json.alarm_rf }}",
                "unit_of_measurement": "%",
                "state_class": "measurement",
            },
        )
        pub(
            "sensor",
            "hyst_lo_reported",
            {
                "name": "Hysteresis low reported",
                "state_topic": cfg,
                "value_template": "{{ value_json.hyst_lo }}",
                "unit_of_measurement": "%",
                "state_class": "measurement",
            },
        )
        pub(
            "sensor",
            "hyst_hi_reported",
            {
                "name": "Hysteresis high reported",
                "state_topic": cfg,
                "value_template": "{{ value_json.hyst_hi }}",
                "unit_of_measurement": "%",
                "state_class": "measurement",
            },
        )
        pub(
            "sensor",
            "static_rf_reported",
            {
                "name": "Static RF reported",
                "state_topic": cfg,
                "value_template": "{{ value_json.static_rf }}",
                "unit_of_measurement": "%",
                "state_class": "measurement",
            },
        )

        # Live CTR telemetry (empty until first Telemetry frame)
        pub(
            "sensor",
            "temperature",
            {
                "name": "Temperature",
                "state_topic": tel,
                "value_template": "{{ value_json.temperature_c | round(1) }}",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            },
        )
        pub(
            "sensor",
            "humidity",
            {
                "name": "Humidity",
                "state_topic": tel,
                "value_template": "{{ value_json.relative_humidity_percent | round(1) }}",
                "unit_of_measurement": "%",
                "device_class": "humidity",
                "state_class": "measurement",
            },
        )
        pub(
            "binary_sensor",
            "fan_running",
            {
                "name": "Fan running",
                "state_topic": tel,
                "value_template": "{{ 'ON' if value_json.fan_running else 'OFF' }}",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device_class": "running",
            },
        )
        pub(
            "binary_sensor",
            "dehumidifying",
            {
                "name": "Dehumidifying",
                "state_topic": tel,
                "value_template": "{{ 'ON' if value_json.dehumidifying else 'OFF' }}",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device_class": "running",
            },
        )
        pub(
            "sensor",
            "service_days",
            {
                "name": "Service days",
                "state_topic": tel,
                "value_template": "{{ value_json.service_days }}",
                "unit_of_measurement": "d",
                "state_class": "measurement",
            },
        )
        pub(
            "sensor",
            "device_datetime",
            {
                "name": "Device time",
                "state_topic": tel,
                # Minute resolution — second ticks would flood the HA logbook.
                "value_template": "{{ value_json.datetime[:16] }}",
                "entity_category": "diagnostic",
            },
        )
        pub(
            "sensor",
            "hours_current_month",
            {
                "name": "Operating hours (month 0)",
                "state_topic": stats,
                "value_template": "{{ value_json.operating_hours[0] }}",
                "unit_of_measurement": "h",
                "state_class": "total_increasing",
            },
        )

        # Config: state from ConfigStatus, command → ConfigWrite merge
        pub(
            "number",
            "mgi",
            {
                "name": "MGI",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ value_json.mgi }}",
                "command_template": '{"mgi": {{ value }}}',
                "min": -40,
                "max": 40,
                "step": 1,
                "mode": "box",
            },
        )
        pub(
            "number",
            "hyst_lo",
            {
                "name": "Hysteresis low",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ value_json.hyst_lo }}",
                "command_template": '{"hyst_lo": {{ value }}}',
                "min": -20,
                "max": 20,
                "step": 1,
                "mode": "box",
            },
        )
        pub(
            "number",
            "hyst_hi",
            {
                "name": "Hysteresis high",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ value_json.hyst_hi }}",
                "command_template": '{"hyst_hi": {{ value }}}',
                "min": -20,
                "max": 20,
                "step": 1,
                "mode": "box",
            },
        )
        pub(
            "number",
            "static_rf",
            {
                "name": "Static RF",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ value_json.static_rf }}",
                "command_template": '{"static_rf": {{ value }}}',
                "min": 0,
                "max": 100,
                "step": 1,
                "unit_of_measurement": "%",
                "mode": "box",
            },
        )
        pub(
            "number",
            "alarm_rf",
            {
                "name": "Alarm RF",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ value_json.alarm_rf }}",
                "command_template": '{"alarm_rf": {{ value }}}',
                "min": 0,
                "max": 100,
                "step": 1,
                "unit_of_measurement": "%",
                "mode": "box",
            },
        )
        pub(
            "switch",
            "continuous_fan",
            {
                "name": "Continuous fan",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ 'ON' if value_json.continuous_fan else 'OFF' }}",
                "payload_on": '{"continuous_fan": true}',
                "payload_off": '{"continuous_fan": false}',
                "state_on": "ON",
                "state_off": "OFF",
            },
        )
        pub(
            "select",
            "mgi_mode",
            {
                "name": "MGI / Static RF",
                "state_topic": cfg,
                "command_topic": cfg_set,
                "value_template": "{{ value_json.mgi_mode }}",
                "command_template": '{"mgi_mode": "{{ value }}"}',
                "options": ["mgi", "static"],
            },
        )
        log.info(
            "Published HA discovery for device %s "
            "(controls: MGI, hyst, RF%%, fan, MGI/Static RF)",
            device_id,
        )
