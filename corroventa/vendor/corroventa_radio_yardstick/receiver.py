from __future__ import annotations

import time
from typing import Any, Iterator, Literal, Optional

from .frame import RadioFrame, now_frame
from .manchester import SYNC_TRUE, soft_extract_frames
from .phy import PhyConfig
from .radio import configure_rx, idle_device, open_device

RxMode = Literal["soft", "hw"]


def _crc16_cms(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8) & 0xFFFF
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def _valid_frame(fr: bytes) -> bool:
    if len(fr) < 7 or fr[:4] != SYNC_TRUE:
        return False
    length = fr[4]
    total = 7 + length
    if len(fr) < total:
        return False
    cs = _crc16_cms(fr[4 : 5 + length])
    return fr[5 + length : 7 + length] == bytes([(cs >> 8) & 0xFF, cs & 0xFF])


def frames_from_hw_fifo(raw: bytes) -> list[bytes]:
    """Rebuild TRUE frames from HW FIFO after D391/D391 sync strip."""
    out: list[bytes] = []
    if not raw:
        return out

    length = raw[0]
    total = 1 + length + 2
    if total <= len(raw):
        fr = SYNC_TRUE + raw[:total]
        if _valid_frame(fr):
            out.append(fr)

    if length in (0x07, 0x0B, 0x0E, 0x16, 0x1D, 0x22, 0x37) and 1 + length <= len(raw):
        body = raw[: 1 + length]
        cs = _crc16_cms(body)
        fr = SYNC_TRUE + body + bytes([(cs >> 8) & 0xFF, cs & 0xFF])
        if _valid_frame(fr):
            out.append(fr)

    blob = raw
    i = 0
    while True:
        j = blob.find(SYNC_TRUE, i)
        if j < 0:
            break
        if j + 5 > len(blob):
            break
        length = blob[j + 4]
        total = 7 + length
        if j + total <= len(blob):
            fr = blob[j : j + total]
            if _valid_frame(fr):
                out.append(fr)
            i = j + total
        else:
            i = j + 4
    return out


class YardStickReceiver:
    """Opaque frame source using Yard Stick One.

    Modes:
      soft — 38.4 kchip/s, Manchester off, chip-sync AAAA (proven)
      hw   — 38.4 kchip/s + CC1111 Manchester on (→19.2 kbit), sync D391 30/32
             FLEN (not VLEN): VLEN stops after L payload bytes and drops CMS CRC

    Pass an existing ``device`` to share one RfCat handle with the transmitter
    (avoids USB reclaim / wedge when switching TX→RX in one process).
    """

    def __init__(
        self,
        phy: Optional[PhyConfig] = None,
        device_index: int = 0,
        mode: RxMode = "soft",
        hw_crc: bool = False,
        device: Any = None,
    ) -> None:
        self.phy = phy or PhyConfig()
        self.device_index = device_index
        self.mode: RxMode = mode
        self.hw_crc = hw_crc
        self._device = device
        self._owns_device = device is None

    def open(self) -> None:
        if self._device is None:
            self._device = open_device(self.device_index)
            self._owns_device = True
        configure_rx(self._device, self.phy, self.mode, hw_crc=self.hw_crc)

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
        raw = bytes(pkt)
        if self.mode == "hw":
            frames = frames_from_hw_fifo(raw)
        else:
            frames = [fr for fr in soft_extract_frames(raw) if _valid_frame(fr)]
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
