# corroventa-protocol

Portable C++17 library for the Corroventa wireless protocol (TRUE-phase packing).

No radio, MQTT, or OS coupling — decode, encode, validate only.
Specification notes live in [`corroventa-engineering/protocol/`](https://github.com/mberglundmx/corroventa-engineering/tree/main/protocol).

## Build

With CMake:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Without CMake (fallback):

```bash
make test
```

## Layout

| Path | Role |
|------|------|
| `include/corroventa/protocol/` | Public headers |
| `src/` | CRC, frame decoder/encoder |
| `fixtures/` | Replay hex frames from captures |
| `tests/` | Unit + fixture regression tests |

## Packet classes (`L` = length byte)

`Keepalive` `0x07` · `PairingBeacon` `0x0B` · `ConfigWrite` `0x0E` · `Poll` `0x16` · `ConfigStatus` `0x1D` · `Telemetry` `0x22` · `Statistics` `0x37`

## Python bindings (pybind11)

```bash
cmake -S . -B build-python \
  -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON \
  -DCORROVENTA_PROTOCOL_BUILD_TESTS=OFF
cmake --build build-python -j
PYTHONPATH=build-python python3 -c "import corroventa_protocol as p; print(p.decode_frame)"
```

Module API: `decode_frame`, `encode_config_write`, `crc16_cms`, `ConfigBlock`.

## License

See repository license when published; currently private RE work.
