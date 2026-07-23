from __future__ import annotations

import time
from typing import Any, Optional, Union

from .frame import RadioFrame
from .manchester import SYNC
from .phy import PhyConfig
from .radio import configure_tx, idle_device, open_device


def hw_tx_fifo(frame: bytes) -> bytes:
    """CC1111 TX FIFO = L ‖ payload (HW appends CRC)."""
    if len(frame) < 5 or frame[:4] != SYNC:
        raise ValueError("expected logical frame starting with D3 91 D3 91")
    length = frame[4]
    need = 5 + length
    if len(frame) < need:
        raise ValueError(f"truncated frame: need {need} bytes, got {len(frame)}")
    return frame[4:need]


class YardStickTransmitter:
    """HW Manchester + HW CRC — accepts logical frames (sync‖L‖payload)."""

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
        configure_tx(self._device, self.phy)

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
    ) -> None:
        if self._device is None:
            raise RuntimeError("YardStickTransmitter is not open")
        raw = frame.data if isinstance(frame, RadioFrame) else bytes(frame)
        if len(raw) < 5 or raw[:4] != SYNC:
            raise ValueError("expected logical frame starting with D3 91 D3 91")

        from rflib import SYNCM_30_of_32

        self._device.setMdmSyncMode(SYNCM_30_of_32)
        self._device.setEnablePktCRC(True)
        air = hw_tx_fifo(raw)
        self._device.makePktFLEN(len(air))
        for i in range(repeats):
            self._device.RFxmit(air)
            if i + 1 < repeats:
                time.sleep(gap_s)
