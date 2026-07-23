#pragma once

#include "corroventa/protocol/ByteSpan.hpp"
#include "corroventa/protocol/Packet.hpp"
#include "corroventa/protocol/PacketKind.hpp"

#include <optional>
#include <string>
#include <variant>

namespace corroventa::protocol {

enum class DecodeError {
  TooShort,
  BadSync,
  Truncated,
};

[[nodiscard]] constexpr const char* toString(DecodeError error) noexcept {
  switch (error) {
    case DecodeError::TooShort:
      return "TooShort";
    case DecodeError::BadSync:
      return "BadSync";
    case DecodeError::Truncated:
      return "Truncated";
  }
  return "Unknown";
}

struct DecodeSuccess {
  Packet packet;
  PacketKind kind = PacketKind::Unknown;
  std::size_t frame_size = 0;
};

struct DecodeFailure {
  DecodeError error = DecodeError::TooShort;
  std::size_t consumed = 0;
};

using DecodeResult = std::variant<DecodeSuccess, DecodeFailure>;

class FrameDecoder {
 public:
  /// Decode one logical frame: sync ‖ L ‖ payload.
  /// On-air captures that still include a 2-byte CRC trailer are accepted; trailer ignored.
  [[nodiscard]] DecodeResult decode(ByteSpan data) const;

  /// Like decode(), but UnknownPacket is returned for unrecognized L.
  [[nodiscard]] DecodeResult decodeAllowUnknown(ByteSpan data) const;
};

}  // namespace corroventa::protocol
