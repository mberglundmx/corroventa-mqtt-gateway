from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhyConfig:
    """RF parameters locked to IQ measurements (2026-07-21)."""

    frequency_hz: int = 868_387_500
    chip_rate: int = 38_400
    rx_deviation_hz: int = 12_000
    tx_deviation_hz: int = 19_200
    # Soft chip-stream TX needs YS1 crystal compensation; HW Manchester TX does not.
    soft_tx_freq_offset_hz: int = -5_800
    hw_tx_freq_offset_hz: int = 0
    channel_bw_hz: int = 135_000
    chip_sync: int = 0xAAAA
    flen: int = 220
    # Soft TX: alternating 01 chips, ~48 bit-times (HV-like); proven CTR accept.
    soft_preamble: str = "01"
    soft_preamble_bits: int = 48
