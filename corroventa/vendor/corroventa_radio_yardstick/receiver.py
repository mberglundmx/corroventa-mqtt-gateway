from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from .frame import RadioFrame, now_frame
from .manchester import SYNC
from .phy import PhyConfig
from .radio import configure_rx, idle_device, open_device

_KNOWN_L = frozenset({0x07, 0x0B, 0x0E, 0x16, 0x1D, 0x22, 0x37})


def frames_from_hw_fifo(raw: bytes) -> list[bytes]:
    """Rebuild logical frames from VLEN+HW-CRC FIFO.

    CC1111 VLEN consumes the length byte and CRC; FIFO is payload only.
    Logical frame = sync ‖ len(raw) ‖ raw.
    """
    if not raw:
        return []
    length = len(raw)
    if length not in _KNOWN_L:
        return []
    return [SYNC + bytes([length]) + raw]


class YardStickReceiver:
    """HW Manchester + VLEN + HW CRC — yields logical frames (sync‖L‖payload)."""

    def __init__(
        self,
        phy: Optional[PhyConfig] = None,
        device_index: int = 0,
        device: Any = None,
    ) -> None:
        self.phy = phy or PhyConfig()
        self.device_index = device_index
        self._device = device
        self._owns_device = device is None

    def open(self) -> None:
        if self._device is None:
            self._device = open_device(self.device_index)
            self._owns_device = True
        configure_rx(self._device, self.phy)

    def close(self) -> None:
        idle_device(self._device)
        if self._owns_device:
            self._device = None

    def __enter__(self) -> "YardStickReceiver":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def receive(self, timeout_s: float = 0.4) -> list[RadioFrame]:
        if self._device is None:
            raise RuntimeError("YardStickReceiver is not open")
        try:
            pkt, _ts = self._device.RFrecv(timeout=int(timeout_s * 1000))
        except Exception:
            return []
        if not pkt:
            return []
        return [now_frame(fr) for fr in frames_from_hw_fifo(bytes(pkt))]

    def frames(self, seconds: float) -> Iterator[RadioFrame]:
        end = time.time() + seconds
        seen: set[str] = set()
        while time.time() < end:
            for fr in self.receive(timeout_s=0.4):
                key = fr.data.hex()
                if key in seen:
                    continue
                seen.add(key)
                yield fr
