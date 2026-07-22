#pragma once

#include <array>
#include <cstdint>

namespace corroventa::protocol {

/// On-air sync word after Manchester demod (TRUE packing).
inline constexpr std::array<std::uint8_t, 4> kSyncWord{{0xD3, 0x91, 0xD3, 0x91}};

/// total_length = 4 (sync) + 1 (L) + L + 2 (CRC) = 7 + L
inline constexpr std::size_t frameTotalLength(std::uint8_t length_byte) noexcept {
  return static_cast<std::size_t>(7) + length_byte;
}

}  // namespace corroventa::protocol
