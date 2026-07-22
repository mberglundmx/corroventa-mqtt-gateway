from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from corroventa_protocol import ConfigBlock, DecodedFrame, encode_config_write

if TYPE_CHECKING:
    from .mqtt_ha import HaMqtt

log = logging.getLogger(__name__)

TransmitFn = Callable[[bytes], None]

# Shared across HV Keepalive / Poll / ConfigWrite on this air link:
#   Keepalive: F5 01 40 01 82 | 01 | seq
#   Poll:      F5 01 40 01 82 | 10 20 | …
#   ConfigWrite: F5 01 40 01 82 | 08 22 | config…
HV_HEADER_PREFIX_LEN = 5

# ConfigWrite-only trailing bytes after the shared HV prefix.
# Hypothesis (medium): class / command discriminator for ConfigWrite — not length
# (length is already L=0x0E). Semantics still unknown.
CONFIG_WRITE_CLASS_SUFFIX = bytes.fromhex("08 22")


@dataclass
class DeviceState:
    """Per-CTR runtime state owned by Device Manager (not the protocol lib)."""

    device_id: int
    config: ConfigBlock | None = None
    # Full ConfigWrite [5:12] if heard on air; else composed from HV prefix + class suffix.
    config_write_header: bytes | None = None
    link_blob: bytes | None = None


class DeviceManager:
    """Tracks CTR/HV identity/state and routes MQTT commands to ConfigWrite frames."""

    def __init__(self, mqtt: HaMqtt, transmit: TransmitFn, tx_repeats: int = 8) -> None:
        self._mqtt = mqtt
        self._transmit = transmit
        self._tx_repeats = tx_repeats
        self._lock = threading.Lock()
        self._devices: dict[int, DeviceState] = {}
        self._primary_device_id: int | None = None
        # Learned from Keepalive/Poll (and ConfigWrite): F5 01 40 01 82 …
        self._hv_header_prefix: bytes | None = None
        self._orphan_write_header: bytes | None = None

    @property
    def primary_device_id(self) -> int | None:
        return self._primary_device_id

    def _device(self, device_id: int) -> DeviceState:
        if device_id not in self._devices:
            self._devices[device_id] = DeviceState(device_id=device_id)
        return self._devices[device_id]

    def _learn_hv_prefix(self, raw: bytes, source: str) -> None:
        if len(raw) < 5 + HV_HEADER_PREFIX_LEN:
            return
        prefix = raw[5 : 5 + HV_HEADER_PREFIX_LEN]
        if self._hv_header_prefix == prefix:
            return
        self._hv_header_prefix = prefix
        log.info("Learned HV header prefix from %s: %s", source, prefix.hex(" "))
        # Refresh composed headers for devices that only had a synthesized one.
        composed = self._compose_config_write_header()
        if composed is None:
            return
        for dev in self._devices.values():
            if dev.config_write_header is None:
                dev.config_write_header = composed

    def _compose_config_write_header(self) -> bytes | None:
        if self._hv_header_prefix is None:
            return None
        return self._hv_header_prefix + CONFIG_WRITE_CLASS_SUFFIX

    def handle_frame(self, decoded: DecodedFrame) -> None:
        with self._lock:
            raw = bytes(decoded.raw) if decoded.raw else b""

            if decoded.kind in ("keepalive", "poll") and raw:
                self._learn_hv_prefix(raw, decoded.kind)

            if decoded.device_id is not None:
                self._primary_device_id = int(decoded.device_id)
            device_id = (
                int(decoded.device_id)
                if decoded.device_id is not None
                else self._primary_device_id
            )

            if decoded.kind == "config_write":
                header = bytes(decoded.config_write_header) if decoded.config_write_header else None
                if header is None and len(raw) >= 12:
                    header = raw[5:12]
                if header is not None:
                    if len(header) >= HV_HEADER_PREFIX_LEN:
                        self._hv_header_prefix = header[:HV_HEADER_PREFIX_LEN]
                    if device_id is not None:
                        self._device(device_id).config_write_header = header
                        log.info(
                            "Learned ConfigWrite header for device %s: %s",
                            device_id,
                            header.hex(" "),
                        )
                    else:
                        self._orphan_write_header = header
                        log.info("Learned orphan ConfigWrite header: %s", header.hex(" "))
                if decoded.config and device_id is not None:
                    self._device(device_id).config = decoded.config
                return

            if decoded.kind == "config_status" and decoded.config and device_id is not None:
                dev = self._device(device_id)
                dev.config = decoded.config
                if dev.config_write_header is None:
                    if self._orphan_write_header is not None:
                        dev.config_write_header = self._orphan_write_header
                    else:
                        composed = self._compose_config_write_header()
                        if composed is not None:
                            dev.config_write_header = composed
                            log.info(
                                "Composed ConfigWrite header for device %s from HV prefix: %s",
                                device_id,
                                composed.hex(" "),
                            )
                self._mqtt.publish_config(device_id, decoded.config)
                log.debug("ConfigStatus device=%s mgi=%s", device_id, decoded.config.mgi)
                return

            if device_id is None:
                log.debug("Skipping %s until device_id known", decoded.kind)
                return

            if decoded.kind == "telemetry" and decoded.telemetry:
                self._mqtt.publish_telemetry(device_id, decoded.telemetry.to_public_dict())
            elif decoded.kind == "statistics" and decoded.statistics:
                self._mqtt.publish_statistics(device_id, decoded.statistics.to_public_dict())

    def handle_config_command(self, device_id: int, patch: dict[str, Any]) -> None:
        with self._lock:
            dev = self._device(device_id)
            header = dev.config_write_header or self._compose_config_write_header()
            if header is None:
                log.error(
                    "No ConfigWrite header for device %s — need HV Keepalive/Poll "
                    "(prefix) or a ConfigWrite on air",
                    device_id,
                )
                return
            base = dev.config
            if base is None:
                log.warning("No ConfigStatus yet for %s — merging onto defaults", device_id)
                base = ConfigBlock()
            merged = base.merge_patch(patch)
            frame = encode_config_write(merged, header)
            log.info(
                "TX ConfigWrite device=%s header=%s mgi=%s",
                device_id,
                header.hex(" "),
                merged.mgi,
            )
        self._transmit(frame)
        with self._lock:
            self._device(device_id).config = merged
            if self._device(device_id).config_write_header is None:
                self._device(device_id).config_write_header = header
