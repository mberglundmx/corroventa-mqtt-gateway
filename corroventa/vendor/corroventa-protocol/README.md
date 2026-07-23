# corroventa-protocol

Portable C++17 library for the Corroventa wireless protocol.

No radio, MQTT, or OS coupling — decode/encode **logical frames** only:
`sync ‖ L ‖ payload`. CRC is **not** part of this library; the air interface
(CC1111 HW CRC) owns it. See air notes below and
[`corroventa-radio-yardstick`](https://github.com/mberglundmx/corroventa-radio-yardstick).

Field notes: [`corroventa-engineering/protocol/`](https://github.com/mberglundmx/corroventa-engineering/tree/main/protocol).

## Air interface (on the wire)

Documented here; implemented with HW flags in the Yard Stick transport.

| Parameter | Value |
|-----------|-------|
| Carrier | 868.3875 MHz (same TX and RX) |
| Modulation | 2-FSK |
| Manchester | **HW on** (`setEnableMdmManchester`) |
| Rate | 38.4 kchip/s → 19.2 kbit/s |
| Deviation | 19.2 kHz (TX and RX) |
| Preamble / sync | AA… + `D391` ×2 |
| Length mode | **VLEN** on RX (max `L=0x37`); FLEN on TX for `L‖payload` |
| CRC | **HW** TX and RX (`setEnablePktCRC`) over `L ‖ payload` |
| RX length | **VLEN** — radio uses `L`, checks CRC; FIFO = payload only |

On the air: `preamble ‖ sync ‖ L ‖ payload ‖ CRC16`.  
Logical (this library): `D3 91 D3 91 ‖ L ‖ payload` (`total = 5 + L`).

TX: transport sends `L ‖ payload` in the FIFO; radio appends CRC.  
RX: VLEN + HW CRC; host prepends sync and restores `L` from `len(FIFO)`.

## Logical frame

| Field | Role |
|-------|------|
| Sync `D3 91 D3 91` | Frame start |
| `L` | Payload length (framing + sanity check) |
| Payload | Header + command + body |

Legacy hex captures that still include a CRC trailer are accepted; the trailer is ignored.

### Payload header — **hypothesis**

| Offset | Guess |
|--------|-------|
| `[5]` | family: `F5` paired, `FF` pairing |
| `[6]` | always `01` here |
| `[7]`/`[8]` | from / to short RF addresses (mirrored by direction) |
| `[9]` | flags (`82` HV, `81` CTR, `51` pairing) |
| `[10]` | inner length `N = L − 6` |
| `[11…]` | command + body (`N==1` ⇒ keepalive seq only) |

Details: engineering [`addressing.md`](https://github.com/mberglundmx/corroventa-engineering/blob/main/protocol/addressing.md).

### Packet classification — **hypothesis**

Primary: **command at `[11]`**. Exceptions: `[5]==FF` → PairingBeacon; `[10]==01` → Keepalive.

| Kind | Discriminator | Usual `L` |
|------|---------------|-----------|
| PairingBeacon | family `FF` | `0x0B` |
| Keepalive | `N==1` | `0x07` |
| ConfigWrite | cmd `0x22` | `0x0E` |
| Poll | cmd `0x20` | `0x16` |
| ConfigStatus | cmd `0x1F` | `0x1D` |
| Telemetry | cmd `0x21` | `0x22` |
| Statistics | cmd `0x26` | `0x37` |

### Pairing

`PairingBeacon` decode only; pairing TX/join not implemented.

## Build

```bash
cmake -S . -B build && cmake --build build
ctest --test-dir build --output-on-failure
```

Fallback: `make test`.

## Python bindings

```bash
cmake -S . -B build-python \
  -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON \
  -DCORROVENTA_PROTOCOL_BUILD_TESTS=OFF
cmake --build build-python -j
```

API: `decode_frame`, `encode_config_write`, `ConfigBlock`.
