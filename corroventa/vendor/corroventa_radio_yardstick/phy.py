from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhyConfig:
    """RF parameters for Corroventa on Yard Stick One (HW Manchester path)."""

    frequency_hz: int = 868_387_500
    # CC1111 rate register = Manchester chip rate (→ 19.2 kbit/s after decode).
    chip_rate: int = 38_400
    deviation_hz: int = 19_200
    channel_bw_hz: int = 135_000
    # Max fixed RX length (host parses by L; air CRC trailer may follow in buffer).
    flen: int = 64
