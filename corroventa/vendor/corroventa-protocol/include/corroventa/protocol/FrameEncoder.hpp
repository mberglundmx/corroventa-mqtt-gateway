#pragma once

#include "corroventa/protocol/Packets.hpp"

#include <cstdint>
#include <vector>

namespace corroventa::protocol {

class FrameEncoder {
 public:
  /// Encode ConfigWrite as sync ‖ L ‖ payload (no CRC — air/HW appends on TX).
  [[nodiscard]] std::vector<std::uint8_t> encode(const ConfigWritePacket& packet) const;

  /// Encode Keepalive (tests / HV simulation).
  [[nodiscard]] std::vector<std::uint8_t> encode(const KeepalivePacket& packet) const;
};

}  // namespace corroventa::protocol
