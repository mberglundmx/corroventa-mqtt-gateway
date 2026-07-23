from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from .frame import RadioFrame, now_frame
from .manchester import SYNC, extract_frames
from .phy import PhyConfig
from .radio import configure_rx, idle_device, open_device

# Known Corroventa length bytes (for body-only FIFO recovery).
_KNOWN_L = frozenset({0x07, 0x0B, 0x0E, 0x16, 0x1D, 0x22, 0x37})


def frames_from_hw_fifo(raw: bytes) -> list[bytes]:
    """Rebuild logical frames (sync‖L‖payload) from HW FIFO after sync strip.

    FIFO usually contains L‖payload‖CRC (CRC-check off). Trailer is dropped by
    length — no software CRC.
    """
    out: list[bytes] = []
    if not raw:
        return out

    length = raw[0]
    body = 1 + length
    # Prefer body without air CRC trailer when present.
    if body + 2 <= len(raw) and length in _KNOWN_L:
        out.append(SYNC + raw[:body])
    elif body <= len(raw) and length in _KNOWN_L:
        out.append(SYNC + raw[:body])

    blob = raw
    i = 0
    while True:
        j = blob.find(SYNC, i)
        if j < 0:
            break
        if j + 5 > len(blob):
            break
        length = blob[j + 4]
        logical = 5 + length
        on_air = 7 + length
        if j + on_air <= len(blob):
            out.append(blob[j : j + logical])
            i = j + on_air
        elif j + logical <= len(blob):
            out.append(blob[j : j + logical])
            i = j + logical
        else:
            i = j + 4
    return out


class YardStickReceiver:
    """HW Manchester frame source — yields logical frames (no CRC)."""

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
        frames = frames_from_hw_fifo(bytes(pkt))
        if not frames:
            frames = extract_frames(bytes(pkt))
        return [now_frame(fr) for fr in frames]

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
