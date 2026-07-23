from __future__ import annotations

import logging
import threading
import time
from typing import Callable

log = logging.getLogger(__name__)

FrameCallback = Callable[[bytes], None]

SUPPORTED_RADIO_MODES = frozenset({"ys1"})


class RadioBridge:
    """Southbound radio bridge. `radio_mode` selects the implementation (ys1 today)."""

    def __init__(self, mode: str = "ys1", enabled: bool = True) -> None:
        self.mode = mode
        self.enabled = enabled
        self._device = None
        self._receiver = None
        self._rx: threading.Thread | None = None
        self._stop = threading.Event()
        self._tx_lock = threading.Lock()
        self._on_frame: FrameCallback | None = None

    def start(self, on_frame: FrameCallback) -> None:
        self._on_frame = on_frame
        if not self.enabled:
            log.warning("Radio disabled — MQTT-only mode")
            return
        if self.mode not in SUPPORTED_RADIO_MODES:
            raise ValueError(
                f"Unsupported radio_mode={self.mode!r}; supported: {sorted(SUPPORTED_RADIO_MODES)}"
            )
        if self.mode == "ys1":
            self._start_ys1()
        else:
            raise AssertionError(f"unhandled radio_mode={self.mode}")

    def _start_ys1(self) -> None:
        from corroventa_radio_yardstick.radio import open_device
        from corroventa_radio_yardstick.receiver import YardStickReceiver

        self._device = open_device(0)
        self._receiver = YardStickReceiver(device=self._device)
        self._receiver.open()
        self._rx = threading.Thread(target=self._rx_loop, name="ys1-rx", daemon=True)
        self._rx.start()
        log.info("Radio RX started (radio_mode=ys1, Yard Stick One)")

    def stop(self) -> None:
        self._stop.set()
        if self._rx:
            self._rx.join(timeout=2)
        try:
            from corroventa_radio_yardstick.radio import idle_device

            idle_device(self._device)
        except Exception:
            pass
        self._device = None

    def transmit(self, frame: bytes, *, repeats: int = 1, gap_s: float = 0.3) -> None:
        if not self.enabled or self._device is None:
            log.warning("TX skipped (radio disabled): %s", frame.hex(" "))
            return
        if self.mode != "ys1":
            raise ValueError(f"TX not implemented for radio_mode={self.mode!r}")
        with self._tx_lock:
            from corroventa_radio_yardstick.radio import idle_device
            from corroventa_radio_yardstick.receiver import YardStickReceiver
            from corroventa_radio_yardstick.transmitter import YardStickTransmitter

            idle_device(self._device)
            tx = YardStickTransmitter(device=self._device)
            tx.open()
            tx.transmit(frame, repeats=repeats, gap_s=gap_s)
            idle_device(self._device)
            self._receiver = YardStickReceiver(device=self._device)
            self._receiver.open()

    def _rx_loop(self) -> None:
        assert self._on_frame is not None
        while not self._stop.is_set():
            try:
                if self._receiver is None:
                    time.sleep(0.2)
                    continue
                frames = self._receiver.receive(timeout_s=0.4)
            except Exception as exc:
                log.debug("RX error: %s", exc)
                time.sleep(0.2)
                continue
            for fr in frames:
                try:
                    self._on_frame(fr.data)
                except Exception:
                    log.exception("Frame callback failed")
