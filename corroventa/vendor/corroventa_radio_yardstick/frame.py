from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(frozen=True)
class RadioFrame:
    """Opaque on-air frame bytes (TRUE packing: sync + L + payload + CRC)."""

    data: bytes
    timestamp: float

    @property
    def length_byte(self) -> int:
        return self.data[4] if len(self.data) > 4 else -1

    def hex(self) -> str:
        return self.data.hex(" ")


def now_frame(data: bytes) -> RadioFrame:
    return RadioFrame(data=bytes(data), timestamp=time.time())
