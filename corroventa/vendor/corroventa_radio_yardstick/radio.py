from __future__ import annotations

from typing import Any, Literal, Optional

from .phy import PhyConfig

RxMode = Literal["soft", "hw"]
TxMode = Literal["soft", "hw"]


def configure_rx(
    d: Any,
    phy: PhyConfig,
    mode: RxMode = "soft",
    *,
    hw_crc: bool = False,
) -> None:
    """Apply RX modem settings and enter RX (device already open)."""
    from rflib import MOD_2FSK, SYNCM_CARRIER_15_of_16, SYNCM_CARRIER_30_of_32

    d.setModeIDLE()
    d.setFreq(phy.frequency_hz)
    d.setMdmModulation(MOD_2FSK)
    d.setMdmChanBW(phy.channel_bw_hz)
    d.setEnablePktCRC(hw_crc if mode == "hw" else False)

    if mode == "hw":
        d.setMdmDeviatn(phy.rx_deviation_hz)
        d.setMdmDRate(phy.chip_rate)
        d.setEnableMdmManchester(True)
        d.setMdmSyncWord(0xD391)
        d.setMdmSyncMode(SYNCM_CARRIER_30_of_32)
        # FLEN: VLEN RX drops CMS trailer (length counts payload only).
        d.makePktFLEN(64)
    else:
        d.setMdmDeviatn(phy.rx_deviation_hz)
        d.setMdmDRate(phy.chip_rate)
        d.setEnableMdmManchester(False)
        d.makePktFLEN(phy.flen)
        if phy.chip_sync == 0:
            d.setMdmSyncMode(0)
        else:
            d.setMdmSyncWord(phy.chip_sync)
            d.setMdmSyncMode(SYNCM_CARRIER_15_of_16)

    d.setModeRX()


def configure_tx(
    d: Any,
    phy: PhyConfig,
    mode: TxMode = "soft",
    *,
    hw_crc: bool = True,
) -> None:
    """Apply TX modem settings (stays IDLE until RFxmit).

    HW path (proven CTR accept):
      - AA preamble + D391×2 sync (SYNC_MODE 30/32)
      - Manchester on, rate register = 38.4 kchip/s
      - FLEN + CRC_EN: FIFO = length+payload; HW appends CRC-16
        (poly 0x8005 init FFFF = Corroventa CMS) over the FIFO bytes
      - No soft crystal offset (hw_tx_freq_offset_hz=0)
    """
    from rflib import (
        MFMCFG1_NUM_PREAMBLE_4,
        MOD_2FSK,
        SYNCM_30_of_32,
        SYNCM_NONE,
    )

    d.setModeIDLE()
    offset = phy.hw_tx_freq_offset_hz if mode == "hw" else phy.soft_tx_freq_offset_hz
    d.setFreq(phy.frequency_hz + offset)
    d.setMdmModulation(MOD_2FSK)
    d.setMdmChanSpc(200_000)
    d.setMaxPower()

    if mode == "hw":
        d.setMdmDRate(phy.chip_rate)
        d.setMdmDeviatn(phy.tx_deviation_hz)
        d.setEnableMdmManchester(True)
        d.setMdmSyncWord(0xD391)
        d.setMdmSyncMode(SYNCM_30_of_32)
        d.setMdmNumPreamble(MFMCFG1_NUM_PREAMBLE_4)
        d.setEnablePktCRC(hw_crc)
        # FLEN size is set per packet in transmit(); VLEN TX did not accept.
    else:
        d.setMdmDRate(phy.chip_rate)
        d.setMdmDeviatn(phy.tx_deviation_hz)
        d.setEnableMdmManchester(False)
        d.setMdmSyncMode(SYNCM_NONE)
        d.setMdmNumPreamble(2)
        d.setEnablePktCRC(False)


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
