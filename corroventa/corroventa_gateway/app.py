from __future__ import annotations

import logging
import signal
import sys
import time
from dataclasses import replace

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
    log.info(
        "Corroventa gateway starting (radio_enabled=%s radio_mode=%s "
        "tx_quiet=%.2fs coalesce=%.2fs ignore_status=%.1fs)",
        settings.radio_enabled,
        settings.radio_mode,
        settings.tx_quiet_s,
        settings.tx_coalesce_s,
        settings.tx_ignore_status_s,
    )

    radio = RadioBridge(mode=settings.radio_mode, enabled=settings.radio_enabled)
    mqtt: HaMqtt | None = None
    manager: DeviceManager | None = None

    def transmit(frame: bytes) -> None:
        radio.transmit(frame, repeats=settings.tx_repeats, gap_s=0.3)

    def on_config_command(device_id: int, patch: dict) -> None:
        assert manager is not None
        manager.handle_config_command(device_id, patch)

    mqtt = HaMqtt(settings, on_config_command=on_config_command)
    manager = DeviceManager(
        mqtt,
        transmit=transmit,
        tx_repeats=settings.tx_repeats,
        tx_quiet_s=settings.tx_quiet_s,
        tx_coalesce_s=settings.tx_coalesce_s,
        tx_ignore_status_s=settings.tx_ignore_status_s,
    )

    seen_kinds: set[str] = set()
    rx_ok = 0
    rx_fail = 0
    last_rx_summary = time.time()

    def on_raw_frame(raw: bytes) -> None:
        nonlocal rx_ok, rx_fail, last_rx_summary
        decoded = decode_frame(raw)
        if decoded is None:
            rx_fail += 1
            if rx_fail <= 5 or rx_fail % 50 == 0:
                log.info(
                    "RX undecoded (%d B) head=%s",
                    len(raw),
                    raw[:12].hex(" ") if raw else "-",
                )
            return
        rx_ok += 1
        if decoded.kind not in seen_kinds:
            seen_kinds.add(decoded.kind)
            log.info("First RX %s  %s", decoded.kind, decoded.raw_hex[:48])
        else:
            log.debug("RX %s %s", decoded.kind, decoded.raw_hex[:48])
        manager.handle_frame(decoded)
        now = time.time()
        if now - last_rx_summary >= 60.0:
            kinds = ",".join(sorted(seen_kinds)) or "-"
            log.info(
                "RX summary: ok=%s fail=%s kinds=%s device_id=%s",
                rx_ok,
                rx_fail,
                kinds,
                manager.primary_device_id,
            )
            if manager.primary_device_id is not None and "telemetry" not in seen_kinds:
                log.warning(
                    "Device %s known but no Telemetry yet — HA sensors "
                    "(temp/RH/fan) stay empty until a Telemetry frame is decoded",
                    manager.primary_device_id,
                )
            last_rx_summary = now
            rx_ok = 0
            rx_fail = 0


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
        settings = replace(settings, radio_enabled=False)

    log.info("Gateway running")
    try:
        while not stop:
            time.sleep(0.5)
    finally:
        log.info("Shutting down")
        if manager is not None:
            manager.stop()
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
