#pragma once

#include "corroventa/protocol/ByteSpan.hpp"

#include <cstdint>

namespace corroventa::protocol {

/// CRC-16/CMS: poly 0x8005, init 0xFFFF, xorout 0, non-reflected.
/// Covers length byte + payload (sync excluded). Stored big-endian.
[[nodiscard]] std::uint16_t crc16Cms(ByteSpan data) noexcept;

[[nodiscard]] inline std::uint16_t crc16Cms(const std::uint8_t* data, std::size_t size) noexcept {
  return crc16Cms(ByteSpan(data, size));
}

}  // namespace corroventa::protocol
