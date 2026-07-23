from __future__ import annotations

from typing import Any, Optional

from .phy import PhyConfig


def configure_rx(d: Any, phy: PhyConfig) -> None:
    """HW Manchester RX; FLEN buffer; CRC-check off so trailer stays for strip-by-L.

    Variable Corroventa lengths cannot use HW CRC-check with a single max FLEN
    (radio would wait for FLEN bytes). Trailer is discarded by length in the
    host — no software CRC algorithm.
    """
    from rflib import MOD_2FSK, SYNCM_CARRIER_30_of_32

    d.setModeIDLE()
    d.setFreq(phy.frequency_hz)
    d.setMdmModulation(MOD_2FSK)
    d.setMdmChanBW(phy.channel_bw_hz)
    d.setMdmDeviatn(phy.deviation_hz)
    d.setMdmDRate(phy.chip_rate)
    d.setEnableMdmManchester(True)
    d.setEnablePktCRC(False)
    d.setMdmSyncWord(0xD391)
    d.setMdmSyncMode(SYNCM_CARRIER_30_of_32)
    d.makePktFLEN(phy.flen)
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
