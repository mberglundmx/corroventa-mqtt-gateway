from __future__ import annotations

import logging
import signal
import sys
import time

from corroventa_protocol import decode_frame

from .device_manager import DeviceManager
from .mqtt_ha import HaMqtt
from .radio import RadioBridge
from .settings import Settings

log = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run(settings: Settings | None = None) -> int:
    settings = settings or Settings.from_env()
    setup_logging(settings.log_level)
    log.info("Corroventa gateway starting (radio_enabled=%s)", settings.radio_enabled)

    radio = RadioBridge(enabled=settings.radio_enabled)
    mqtt: HaMqtt | None = None
    manager: DeviceManager | None = None

    def transmit(frame: bytes) -> None:
        radio.transmit(frame, repeats=settings.tx_repeats, gap_s=0.3)

    def on_config_command(device_id: int, patch: dict) -> None:
        assert manager is not None
        manager.handle_config_command(device_id, patch)

    mqtt = HaMqtt(settings, on_config_command=on_config_command)
    manager = DeviceManager(mqtt, transmit=transmit, tx_repeats=settings.tx_repeats)

    def on_raw_frame(raw: bytes) -> None:
        decoded = decode_frame(raw)
        if decoded is None:
            return
        log.debug("RX %s %s", decoded.kind, decoded.raw_hex[:48])
        manager.handle_frame(decoded)

    stop = False

    def _stop(*_args: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    mqtt.start()
    try:
        radio.start(on_raw_frame)
    except Exception:
        log.exception("Failed to start radio — continuing MQTT-only")
        settings = Settings(
            mqtt_host=settings.mqtt_host,
            mqtt_port=settings.mqtt_port,
            mqtt_username=settings.mqtt_username,
            mqtt_password=settings.mqtt_password,
            mqtt_client_id=settings.mqtt_client_id,
            log_level=settings.log_level,
            radio_enabled=False,
            discovery_prefix=settings.discovery_prefix,
            topic_prefix=settings.topic_prefix,
            device_model=settings.device_model,
            tx_repeats=settings.tx_repeats,
        )

    log.info("Gateway running")
    try:
        while not stop:
            time.sleep(0.5)
    finally:
        log.info("Shutting down")
        radio.stop()
        if manager and manager.primary_device_id is not None:
            mqtt.publish_availability(manager.primary_device_id, False)
        mqtt.stop()
        # rfcat/libusb often SIGSEGV on interpreter teardown
        import os

        os._exit(0)
    return 0


def main() -> None:
    raise SystemExit(run())
