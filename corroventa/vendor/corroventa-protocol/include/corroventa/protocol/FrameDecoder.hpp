#pragma once

#include "corroventa/protocol/ByteSpan.hpp"
#include "corroventa/protocol/Packet.hpp"
#include "corroventa/protocol/PacketKind.hpp"

#include <optional>
#include <string>

namespace corroventa::protocol {

enum class DecodeError {
  TooShort,
  BadSync,
  Truncated,
  BadCrc,
};

[[nodiscard]] constexpr const char* toString(DecodeError error) noexcept {
  switch (error) {
    case DecodeError::TooShort:
      return "TooShort";
    case DecodeError::BadSync:
      return "BadSync";
    case DecodeError::Truncated:
      return "Truncated";
    case DecodeError::BadCrc:
      return "BadCrc";
  }
  return "Unknown";
}

struct DecodeSuccess {
  Packet packet;
  PacketKind kind = PacketKind::Unknown;
  std::size_t frame_size = 0;
  bool crc_ok = true;
};

struct DecodeFailure {
  DecodeError error = DecodeError::TooShort;
  std::size_t consumed = 0;
};

using DecodeResult = std::variant<DecodeSuccess, DecodeFailure>;

class FrameDecoder {
 public:
  /// Decode one frame starting at data[0]. Requires full frame including CRC.
  [[nodiscard]] DecodeResult decode(ByteSpan data) const;

  /// Like decode(), but UnknownPacket is returned for unrecognized L (still CRC-checked).
  [[nodiscard]] DecodeResult decodeAllowUnknown(ByteSpan data) const;
};

}  // namespace corroventa::protocol
