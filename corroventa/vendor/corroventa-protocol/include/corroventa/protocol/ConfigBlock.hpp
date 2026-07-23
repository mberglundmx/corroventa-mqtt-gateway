#pragma once

#include <cstdint>

namespace corroventa::protocol {

/// Shared config block used by ConfigWrite and ConfigStatus (offsets relative to frame start).
struct ConfigBlock {
  std::int8_t hyst_lo = 0;     // AA
  std::int8_t hyst_hi = 0;     // BB
  std::int8_t mgi = 0;         // MM
  std::uint8_t static_rf = 0;  // SS (%)
  std::uint8_t alarm_rf = 0;   // ZZ (%)
  bool continuous_fan = false; // yy: 0x00=OFF, 0x01=ON (ghost demod showed 0x02)
  bool mgi_mode = true;        // MODE: 0x01=MGI, 0x00=static RF
};

[[nodiscard]] inline std::int8_t asSigned(std::uint8_t v) noexcept {
  return static_cast<std::int8_t>(v);
}

}  // namespace corroventa::protocol
