#pragma once

#include "corroventa/protocol/Packets.hpp"

#include <cstdint>
#include <optional>
#include <vector>

namespace corroventa::protocol {

class FrameEncoder {
 public:
  /// Encode a ConfigWrite including sync + CRC (TRUE packing).
  [[nodiscard]] std::vector<std::uint8_t> encode(const ConfigWritePacket& packet) const;

  /// Encode Keepalive (for tests / HV simulation).
  [[nodiscard]] std::vector<std::uint8_t> encode(const KeepalivePacket& packet) const;
};

}  // namespace corroventa::protocol
