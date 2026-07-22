from __future__ import annotations

SYNC_TRUE = bytes.fromhex("d391d391")


def bits_from_bytes(data: bytes) -> list[int]:
    out: list[int] = []
    for b in data:
        for i in range(7, -1, -1):
            out.append((b >> i) & 1)
    return out


def manchester_decode(chips: list[int], convention: str = "10=1") -> list[int]:
    bits: list[int] = []
    for i in range(0, len(chips) - 1, 2):
        a, b = chips[i], chips[i + 1]
        if a == b:
            continue
        if convention == "10=1":
            bits.append(1 if (a, b) == (1, 0) else 0)
        else:
            bits.append(1 if (a, b) == (0, 1) else 0)
    return bits


def bits_to_bytes(bits: list[int], offset: int = 0) -> bytes:
    bb = bits[offset:]
    out = bytearray()
    for i in range(len(bb) // 8):
        val = 0
        for bit in bb[i * 8 : (i + 1) * 8]:
            val = (val << 1) | bit
        out.append(val)
    return bytes(out)


def bytes_to_bits_msb(data: bytes) -> list[int]:
    out: list[int] = []
    for b in data:
        for i in range(7, -1, -1):
            out.append((b >> i) & 1)
    return out


def manchester_encode(bits: list[int], convention: str = "10=1") -> list[int]:
    chips: list[int] = []
    for bit in bits:
        if convention == "10=1":
            chips.extend([1, 0] if bit else [0, 1])
        else:
            chips.extend([0, 1] if bit else [1, 0])
    return chips


def chips_to_bytes(chips: list[int]) -> bytes:
    while len(chips) % 8:
        chips.append(0)
    out = bytearray()
    for i in range(0, len(chips), 8):
        val = 0
        for bit in chips[i : i + 8]:
            val = (val << 1) | bit
        out.append(val)
    return bytes(out)


def extract_true_frames(payload: bytes) -> list[bytes]:
    """Find TRUE sync and slice sync+L+payload+CRC using length byte."""
    frames: list[bytes] = []
    i = 0
    while True:
        j = payload.find(SYNC_TRUE, i)
        if j < 0:
            break
        if j + 5 > len(payload):
            break
        length_byte = payload[j + 4]
        total = 7 + length_byte
        if j + total <= len(payload):
            frames.append(payload[j : j + total])
            i = j + total
        else:
            # truncated — skip this sync
            i = j + 4
    return frames


def soft_extract_frames(pkt: bytes) -> list[bytes]:
    """Software Manchester demod + TRUE frame extraction."""
    chips = bits_from_bytes(pkt)
    found: list[bytes] = []
    seen: set[str] = set()
    for phase in (0, 1):
        for conv in ("10=1", "01=1"):
            bits = manchester_decode(chips[phase:], conv)
            for off in range(8):
                data = bits_to_bytes(bits, off)
                for fr in extract_true_frames(data):
                    key = fr.hex()
                    if key not in seen:
                        seen.add(key)
                        found.append(fr)
    return found


def build_air_packet(
    frame: bytes,
    preamble_bits: int = 48,
    *,
    preamble: str = "01",
    convention: str = "10=1",
) -> bytes:
    """Manchester-encode soft preamble + frame for TX (HW Manchester off)."""
    if preamble == "01":
        pre = [i % 2 for i in range(preamble_bits)]
    elif preamble == "10":
        pre = [(i + 1) % 2 for i in range(preamble_bits)]
    elif preamble == "1":
        pre = [1] * preamble_bits
    elif preamble == "0":
        pre = [0] * preamble_bits
    else:
        raise ValueError(f"unknown preamble {preamble!r}")
    bits = pre + bytes_to_bits_msb(frame)
    return chips_to_bytes(manchester_encode(bits, convention))
