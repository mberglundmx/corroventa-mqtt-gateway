from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from corroventa_protocol import ConfigBlock, DecodedFrame, encode_config_write

if TYPE_CHECKING:
    from .mqtt_ha import HaMqtt

log = logging.getLogger(__name__)

TransmitFn = Callable[[bytes], None]

# Hypothesis: payload header (see corroventa-engineering/protocol/addressing.md)
FAMILY_PAIRED = 0xF5
HV_FLAGS_DEFAULT = 0x82
CONFIG_WRITE_N = 0x08
CONFIG_WRITE_CMD = 0x22

_HV_KINDS = frozenset({"keepalive", "poll", "config_write"})
_CTR_KINDS = frozenset({"config_status", "telemetry", "statistics", "pairing_beacon"})


@dataclass
class DeviceState:
    """Per-CTR runtime state owned by Device Manager (not the protocol lib)."""

    device_id: int
    config: ConfigBlock | None = None
    config_write_header: bytes | None = None
    link_blob: bytes | None = None
    short_addr: int | None = None  # CTR RF short address


class DeviceManager:
    """Tracks CTR/HV short addresses + state; routes MQTT → ConfigWrite.

    Config commands are coalesced on a TX worker: concurrent HA automations merge
    into one air write, and TX waits for a quiet gap on the channel.
    """

    def __init__(
        self,
        mqtt: HaMqtt,
        transmit: TransmitFn,
        tx_repeats: int = 8,
        tx_quiet_s: float = 0.25,
        tx_coalesce_s: float = 0.2,
        tx_ignore_status_s: float = 1.5,
    ) -> None:
        self._mqtt = mqtt
        self._transmit = transmit
        self._tx_repeats = tx_repeats
        self._tx_quiet_s = tx_quiet_s
        self._tx_coalesce_s = tx_coalesce_s
        self._tx_ignore_status_s = tx_ignore_status_s
        self._lock = threading.Lock()
        self._devices: dict[int, DeviceState] = {}
        self._primary_device_id: int | None = None
        self._hv_short_addr: int | None = None
        self._hv_flags: int = HV_FLAGS_DEFAULT
        self._pending_ctr_addr: int | None = None
        self._orphan_write_header: bytes | None = None
        self._last_rx_mono = 0.0
        self._pending_patches: dict[int, dict[str, Any]] = {}
        self._ignore_status_until: dict[int, float] = {}
        self._stop = threading.Event()
        self._tx_event = threading.Event()
        self._tx_thread = threading.Thread(
            target=self._tx_loop, name="config-tx", daemon=True
        )
        self._tx_thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._tx_event.set()
        self._tx_thread.join(timeout=2)

    @property
    def primary_device_id(self) -> int | None:
        return self._primary_device_id

    @property
    def hv_short_addr(self) -> int | None:
        return self._hv_short_addr

    def _device(self, device_id: int) -> DeviceState:
        if device_id not in self._devices:
            self._devices[device_id] = DeviceState(device_id=device_id)
        return self._devices[device_id]

    def _learn_short_addrs(self, raw: bytes, kind: str) -> None:
        if len(raw) < 10:
            return
        family, src, dst, flags = raw[5], raw[7], raw[8], raw[9]
        if family not in (FAMILY_PAIRED, 0xFF):
            return

        if kind in _HV_KINDS:
            hv, ctr = src, dst
            self._hv_flags = flags
        elif kind in _CTR_KINDS:
            ctr, hv = src, dst
        else:
            return

        if self._hv_short_addr != hv:
            self._hv_short_addr = hv
            log.info("Learned HV short addr 0x%02x (from %s)", hv, kind)

        if self._primary_device_id is not None:
            dev = self._device(self._primary_device_id)
            if dev.short_addr != ctr:
                dev.short_addr = ctr
                log.info(
                    "Learned CTR short addr 0x%02x for device %s (from %s)",
                    ctr,
                    self._primary_device_id,
                    kind,
                )
        elif self._pending_ctr_addr != ctr:
            self._pending_ctr_addr = ctr
            log.info("Pending CTR short addr 0x%02x (from %s, no UI id yet)", ctr, kind)

        self._refresh_composed_headers()

    def _compose_config_write_header(self, ctr_addr: int | None = None) -> bytes | None:
        if self._hv_short_addr is None:
            return None
        ctr = ctr_addr
        if ctr is None and self._primary_device_id is not None:
            ctr = self._device(self._primary_device_id).short_addr
        if ctr is None:
            ctr = self._pending_ctr_addr
        if ctr is None:
            return None
        return bytes(
            [
                FAMILY_PAIRED,
                0x01,
                self._hv_short_addr & 0xFF,
                ctr & 0xFF,
                self._hv_flags & 0xFF,
                CONFIG_WRITE_N,
                CONFIG_WRITE_CMD,
            ]
        )

    def _refresh_composed_headers(self) -> None:
        for dev in self._devices.values():
            if dev.config_write_header is not None:
                continue
            composed = self._compose_config_write_header(dev.short_addr)
            if composed is not None:
                dev.config_write_header = composed

    def handle_frame(self, decoded: DecodedFrame) -> None:
        with self._lock:
            self._last_rx_mono = time.monotonic()
            raw = bytes(decoded.raw) if decoded.raw else b""

            if raw:
                self._learn_short_addrs(raw, decoded.kind)

            if decoded.device_id is not None:
                self._primary_device_id = int(decoded.device_id)
                if self._pending_ctr_addr is not None:
                    self._device(self._primary_device_id).short_addr = self._pending_ctr_addr
                    self._pending_ctr_addr = None
                    self._refresh_composed_headers()

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
                    if len(header) >= 5:
                        self._hv_short_addr = header[2]
                        self._hv_flags = header[4]
                        if device_id is not None:
                            self._device(device_id).short_addr = header[3]
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
                ignore_until = self._ignore_status_until.get(device_id, 0.0)
                now = time.monotonic()
                if now < ignore_until:
                    log.info(
                        "Ignoring ConfigStatus %.2fs after TX device=%s "
                        "mgi=%s hyst=%s/%s alarm=%s fan=%s (echo window)",
                        ignore_until - now,
                        device_id,
                        decoded.config.mgi,
                        decoded.config.hyst_lo,
                        decoded.config.hyst_hi,
                        decoded.config.alarm_rf,
                        decoded.config.continuous_fan,
                    )
                    return
                dev = self._device(device_id)
                dev.config = decoded.config
                if dev.config_write_header is None:
                    if self._orphan_write_header is not None:
                        dev.config_write_header = self._orphan_write_header
                    else:
                        composed = self._compose_config_write_header(dev.short_addr)
                        if composed is not None:
                            dev.config_write_header = composed
                            log.info(
                                "Composed ConfigWrite header for device %s: %s",
                                device_id,
                                composed.hex(" "),
                            )
                self._mqtt.publish_config(device_id, decoded.config)
                log.info(
                    "ConfigStatus device=%s mgi=%s hyst=%s/%s alarm=%s fan=%s mode=%s",
                    device_id,
                    decoded.config.mgi,
                    decoded.config.hyst_lo,
                    decoded.config.hyst_hi,
                    decoded.config.alarm_rf,
                    decoded.config.continuous_fan,
                    "mgi" if decoded.config.mgi_mode else "static",
                )
                return

            if device_id is None:
                if decoded.kind in ("telemetry", "statistics", "config_status"):
                    log.info(
                        "Got %s but no UI device id yet — waiting for ConfigStatus/PairingBeacon",
                        decoded.kind,
                    )
                else:
                    log.debug("Skipping %s until device_id known", decoded.kind)
                return

            if decoded.kind == "telemetry" and decoded.telemetry:
                self._mqtt.publish_telemetry(device_id, decoded.telemetry.to_public_dict())
            elif decoded.kind == "statistics" and decoded.statistics:
                self._mqtt.publish_statistics(device_id, decoded.statistics.to_public_dict())
            elif decoded.kind == "telemetry":
                log.warning("Telemetry frame without payload device=%s", device_id)
            elif decoded.kind == "unknown":
                log.debug("Ignoring unknown frame L=0x%02x", raw[4] if len(raw) > 4 else -1)

    def handle_config_command(self, device_id: int, patch: dict[str, Any]) -> None:
        """Queue a config patch; TX worker coalesces and sends one ConfigWrite."""
        with self._lock:
            pending = self._pending_patches.setdefault(device_id, {})
            pending.update(patch)
            log.info(
                "Queued config patch device=%s patch=%s pending=%s",
                device_id,
                patch,
                dict(pending),
            )
        self._tx_event.set()

    def _take_pending(self) -> tuple[int, dict[str, Any]] | None:
        with self._lock:
            if not self._pending_patches:
                return None
            device_id = next(iter(self._pending_patches))
            patch = dict(self._pending_patches.pop(device_id))
            return device_id, patch

    def _wait_air_quiet(self) -> None:
        quiet = self._tx_quiet_s
        timeout = max(3.0, quiet * 12.0)
        deadline = time.monotonic() + timeout
        while not self._stop.is_set() and time.monotonic() < deadline:
            with self._lock:
                last = self._last_rx_mono
            now = time.monotonic()
            if last <= 0.0:
                # No RX yet — brief settle then send.
                time.sleep(min(quiet, 0.1))
                return
            if now - last >= quiet:
                return
            time.sleep(0.05)
        log.warning(
            "TX quiet-wait timed out after %.1fs (need %.2fs silence) — sending anyway",
            timeout,
            quiet,
        )

    def _send_merged(self, device_id: int, patch: dict[str, Any]) -> None:
        with self._lock:
            # Absorb any patches that arrived while waiting for quiet.
            extra = self._pending_patches.pop(device_id, None)
            if extra:
                patch = {**patch, **extra}
                log.info("Coalesced extra patch device=%s pending=%s", device_id, patch)

            dev = self._device(device_id)
            header = dev.config_write_header or self._compose_config_write_header(dev.short_addr)
            if header is None:
                log.error(
                    "No ConfigWrite header for device %s — need air traffic to learn "
                    "HV/CTR short addresses (or a ConfigWrite on air)",
                    device_id,
                )
                # Re-queue so a later attempt can succeed once header is known.
                pending = self._pending_patches.setdefault(device_id, {})
                pending.update(patch)
                return
            base = dev.config
            if base is None:
                log.warning("No ConfigStatus yet for %s — merging onto defaults", device_id)
                base = ConfigBlock()
            merged = base.merge_patch(patch)
            frame = encode_config_write(merged, header)
            log.info(
                "TX ConfigWrite device=%s mgi=%s hyst=%s/%s alarm=%s fan=%s mode=%s "
                "yy=0x%02x frame=%s",
                device_id,
                merged.mgi,
                merged.hyst_lo,
                merged.hyst_hi,
                merged.alarm_rf,
                merged.continuous_fan,
                "mgi" if merged.mgi_mode else "static",
                frame[17] if len(frame) > 17 else -1,
                frame.hex(" "),
            )

        self._transmit(frame)

        with self._lock:
            self._device(device_id).config = merged
            if self._device(device_id).config_write_header is None:
                self._device(device_id).config_write_header = header
            self._ignore_status_until[device_id] = (
                time.monotonic() + self._tx_ignore_status_s
            )
            self._mqtt.publish_config(device_id, merged)
            log.info(
                "TX done device=%s — ignoring ConfigStatus for %.1fs",
                device_id,
                self._tx_ignore_status_s,
            )

    def _tx_loop(self) -> None:
        while not self._stop.is_set():
            triggered = self._tx_event.wait(timeout=0.5)
            if self._stop.is_set():
                break
            if triggered:
                self._tx_event.clear()
            with self._lock:
                has_pending = bool(self._pending_patches)
            if not has_pending:
                continue

            # Let near-simultaneous automations land in the same pending dict.
            time.sleep(self._tx_coalesce_s)

            while not self._stop.is_set():
                item = self._take_pending()
                if item is None:
                    break
                device_id, patch = item
                log.info(
                    "TX worker: quiet-wait then send device=%s patch=%s",
                    device_id,
                    patch,
                )
                self._wait_air_quiet()
                if self._stop.is_set():
                    with self._lock:
                        pending = self._pending_patches.setdefault(device_id, {})
                        pending.update(patch)
                    break
                try:
                    self._send_merged(device_id, patch)
                except Exception:
                    log.exception("TX failed device=%s", device_id)
                    with self._lock:
                        pending = self._pending_patches.setdefault(device_id, {})
                        pending.update(patch)
