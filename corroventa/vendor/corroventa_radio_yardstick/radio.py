from __future__ import annotations

from typing import Any, Optional

from .phy import PhyConfig


def configure_rx(d: Any, phy: PhyConfig) -> None:
    """HW Manchester RX with VLEN + HW CRC.

    After sync, CC1111 reads length byte L, then L payload bytes, checks CRC.
    FIFO delivers **payload only** (L is consumed by the radio; CRC stripped).
    Host rebuilds logical frame as sync ‖ L ‖ payload with L = len(FIFO).
    """
    from rflib import MOD_2FSK, SYNCM_CARRIER_30_of_32

    d.setModeIDLE()
    d.setFreq(phy.frequency_hz)
    d.setMdmModulation(MOD_2FSK)
    d.setMdmChanBW(phy.channel_bw_hz)
    d.setMdmDeviatn(phy.deviation_hz)
    d.setMdmDRate(phy.chip_rate)
    d.setEnableMdmManchester(True)
    d.setMdmSyncWord(0xD391)
    d.setMdmSyncMode(SYNCM_CARRIER_30_of_32)
    d.setEnablePktAppendStatus(False)
    # Length mode and CRC both touch PKTCTRL0 — set VLEN then re-assert CRC.
    d.makePktVLEN(phy.vlen_max)
    d.setEnablePktCRC(True)
    d.setModeRX()


def configure_tx(d: Any, phy: PhyConfig) -> None:
    """HW Manchester TX + HW CRC. FIFO = L‖payload; radio appends CRC."""
    from rflib import MFMCFG1_NUM_PREAMBLE_4, MOD_2FSK, SYNCM_30_of_32

    d.setModeIDLE()
    d.setFreq(phy.frequency_hz)
    d.setMdmModulation(MOD_2FSK)
    d.setMdmChanSpc(200_000)
    d.setMaxPower()
    d.setMdmDRate(phy.chip_rate)
    d.setMdmDeviatn(phy.deviation_hz)
    d.setEnableMdmManchester(True)
    d.setMdmSyncWord(0xD391)
    d.setMdmSyncMode(SYNCM_30_of_32)
    d.setMdmNumPreamble(MFMCFG1_NUM_PREAMBLE_4)
    d.setEnablePktCRC(True)


def open_device(device_index: int = 0) -> Any:
    from rflib import RfCat

    d = RfCat(idx=device_index)
    d.setModeIDLE()
    return d


def idle_device(d: Optional[Any]) -> None:
    if d is None:
        return
    try:
        d.setModeIDLE()
    except Exception:
        pass
