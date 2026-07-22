#include "corroventa/protocol/Crc16.hpp"

namespace corroventa::protocol {

std::uint16_t crc16Cms(ByteSpan data) noexcept {
  std::uint16_t crc = 0xFFFF;
  for (std::size_t i = 0; i < data.size(); ++i) {
    crc ^= static_cast<std::uint16_t>(data[i]) << 8;
    for (int bit = 0; bit < 8; ++bit) {
      if ((crc & 0x8000U) != 0) {
        crc = static_cast<std::uint16_t>((crc << 1) ^ 0x8005U);
      } else {
        crc = static_cast<std::uint16_t>(crc << 1);
      }
    }
  }
  return crc;
}

}  // namespace corroventa::protocol
