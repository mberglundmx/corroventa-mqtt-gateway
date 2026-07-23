from __future__ import annotations

SYNC = bytes.fromhex("d391d391")


def extract_frames(payload: bytes) -> list[bytes]:
    """Find sync and slice logical frames sync‖L‖payload (drop air CRC if present)."""
    frames: list[bytes] = []
    i = 0
    while True:
        j = payload.find(SYNC, i)
        if j < 0:
            break
        if j + 5 > len(payload):
            break
        length_byte = payload[j + 4]
        logical = 5 + length_byte
        on_air = 7 + length_byte
        if j + on_air <= len(payload):
            frames.append(payload[j : j + logical])
            i = j + on_air
        elif j + logical <= len(payload):
            frames.append(payload[j : j + logical])
            i = j + logical
        else:
            i = j + 4
    return frames
