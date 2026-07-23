#pragma once

#include <array>
#include <cstdint>

namespace corroventa::protocol {

/// On-air sync word after Manchester demod.
inline constexpr std::array<std::uint8_t, 4> kSyncWord{{0xD3, 0x91, 0xD3, 0x91}};

/// Logical frame length: sync(4) + L(1) + payload(L). CRC is air/HW only.
inline constexpr std::size_t frameTotalLength(std::uint8_t length_byte) noexcept {
  return static_cast<std::size_t>(5) + length_byte;
}

}  // namespace corroventa::protocol
