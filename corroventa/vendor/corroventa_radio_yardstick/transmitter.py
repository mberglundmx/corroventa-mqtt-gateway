from __future__ import annotations

import time
from typing import Any, Literal, Optional, Union

from .frame import RadioFrame
from .manchester import SYNC_TRUE, build_air_packet
from .phy import PhyConfig
from .radio import configure_tx, idle_device, open_device

TxMode = Literal["soft", "hw"]


def hw_tx_fifo(frame: bytes, *, hw_crc: bool) -> bytes:
    """Build CC1111 TX FIFO bytes from a TRUE-phase frame.

    With hw_crc (preferred): length + payload only; radio appends CRC over FIFO.
    Without: length + payload + software CRC trailer.
    """
    if len(frame) < 7 or frame[:4] != SYNC_TRUE:
        raise ValueError("expected TRUE-phase frame starting with D3 91 D3 91")
    length = frame[4]
    total = 7 + length
    if len(frame) < total:
        raise ValueError(f"truncated frame: need {total} bytes, got {len(frame)}")
    if hw_crc:
        return frame[4 : 5 + length]
    return frame[4:total]


class YardStickTransmitter:
    """Opaque frame sink using Yard Stick One.

    soft — soft Manchester chips @ 38.4 kchip/s, soft crystal offset
    hw   — HW AA preamble + D391×2 + Manchester + (default) HW CRC-16/CMS

    Pass an existing ``device`` to share one RfCat handle with the receiver.
    """

    def __init__(
        self,
        phy: Optional[PhyConfig] = None,
        device_index: int = 0,
        mode: TxMode = "hw",
        hw_crc: bool = True,
        device: Any = None,
    ) -> None:
        self.phy = phy or PhyConfig()
        self.device_index = device_index
        self.mode: TxMode = mode
        self.hw_crc = hw_crc
        self._device = device
        self._owns_device = device is None

    def open(self) -> None:
        if self._device is None:
            self._device = open_device(self.device_index)
            self._owns_device = True
        configure_tx(self._device, self.phy, self.mode, hw_crc=self.hw_crc)

    def close(self) -> None:
        idle_device(self._device)
        if self._owns_device:
            self._device = None

    def __enter__(self) -> "YardStickTransmitter":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def transmit(
        self,
        frame: Union[RadioFrame, bytes],
        *,
        repeats: int = 1,
        gap_s: float = 0.3,
        preamble_bits: Optional[int] = None,
        preamble: Optional[str] = None,
    ) -> None:
        if self._device is None:
            raise RuntimeError("YardStickTransmitter is not open")
        raw = frame.data if isinstance(frame, RadioFrame) else bytes(frame)
        if len(raw) < 7 or raw[:4] != SYNC_TRUE:
            raise ValueError("expected TRUE-phase frame starting with D3 91 D3 91")

        if self.mode == "hw":
            from rflib import SYNCM_30_of_32

            self._device.setMdmSyncMode(SYNCM_30_of_32)
            self._device.setEnablePktCRC(self.hw_crc)
            air = hw_tx_fifo(raw, hw_crc=self.hw_crc)
            self._device.makePktFLEN(len(air))
        else:
            air = build_air_packet(
                raw,
                preamble_bits=preamble_bits
                if preamble_bits is not None
                else self.phy.soft_preamble_bits,
                preamble=preamble if preamble is not None else self.phy.soft_preamble,
            )
            self._device.makePktFLEN(len(air))

        for i in range(repeats):
            self._device.RFxmit(air)
            if i + 1 < repeats:
                time.sleep(gap_s)
