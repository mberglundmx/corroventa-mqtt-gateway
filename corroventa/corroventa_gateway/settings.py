from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _normalize_radio_mode(raw: str) -> str:
    """Map radio_mode to a radio backend implementation.

    Legacy values hw/soft from early builds map to ys1 (soft path removed).
    """
    mode = raw.strip().lower()
    if mode in ("ys1", "yardstick", "yard_stick", "yard-stick-one", "hw", "soft"):
        return "ys1"
    return mode


@dataclass(frozen=True)
class Settings:
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_client_id: str = "corroventa-gateway"
    log_level: str = "info"
    radio_mode: str = "ys1"
    radio_enabled: bool = True
    discovery_prefix: str = "homeassistant"
    topic_prefix: str = "corroventa"
    device_model: str = "CTR300TT2"
    tx_repeats: int = 8
    tx_quiet_s: float = 0.25
    tx_coalesce_s: float = 0.2
    tx_ignore_status_s: float = 1.5

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mqtt_host=os.environ.get("MQTT_HOST", "127.0.0.1"),
            mqtt_port=int(os.environ.get("MQTT_PORT", "1883")),
            mqtt_username=os.environ.get("MQTT_USERNAME") or None,
            mqtt_password=os.environ.get("MQTT_PASSWORD") or None,
            mqtt_client_id=os.environ.get("MQTT_CLIENT_ID", "corroventa-gateway"),
            log_level=os.environ.get("LOG_LEVEL", "info").lower(),
            radio_mode=_normalize_radio_mode(os.environ.get("RADIO_MODE", "ys1")),
            radio_enabled=_env_bool("RADIO_ENABLED", True),
            discovery_prefix=os.environ.get("DISCOVERY_PREFIX", "homeassistant"),
            topic_prefix=os.environ.get("TOPIC_PREFIX", "corroventa"),
            device_model=os.environ.get("DEVICE_MODEL", "CTR300TT2"),
            tx_repeats=int(os.environ.get("TX_REPEATS", "8")),
            tx_quiet_s=float(os.environ.get("TX_QUIET_S", "0.25")),
            tx_coalesce_s=float(os.environ.get("TX_COALESCE_S", "0.2")),
            tx_ignore_status_s=float(os.environ.get("TX_IGNORE_STATUS_S", "1.5")),
        )
