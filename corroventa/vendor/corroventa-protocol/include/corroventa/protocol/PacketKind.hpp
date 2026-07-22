#pragma once

#include <cstdint>

namespace corroventa::protocol {

/// Wire discriminator is the length byte L (not a separate opcode).
enum class PacketKind : std::uint8_t {
  Keepalive = 0x07,
  PairingBeacon = 0x0B,
  ConfigWrite = 0x0E,
  Poll = 0x16,
  ConfigStatus = 0x1D,
  Telemetry = 0x22,
  Statistics = 0x37,
  Unknown = 0xFF,
};

[[nodiscard]] constexpr PacketKind packetKindFromLength(std::uint8_t length_byte) noexcept {
  switch (length_byte) {
    case 0x07:
      return PacketKind::Keepalive;
    case 0x0B:
      return PacketKind::PairingBeacon;
    case 0x0E:
      return PacketKind::ConfigWrite;
    case 0x16:
      return PacketKind::Poll;
    case 0x1D:
      return PacketKind::ConfigStatus;
    case 0x22:
      return PacketKind::Telemetry;
    case 0x37:
      return PacketKind::Statistics;
    default:
      return PacketKind::Unknown;
  }
}

[[nodiscard]] constexpr const char* toString(PacketKind kind) noexcept {
  switch (kind) {
    case PacketKind::Keepalive:
      return "Keepalive";
    case PacketKind::PairingBeacon:
      return "PairingBeacon";
    case PacketKind::ConfigWrite:
      return "ConfigWrite";
    case PacketKind::Poll:
      return "Poll";
    case PacketKind::ConfigStatus:
      return "ConfigStatus";
    case PacketKind::Telemetry:
      return "Telemetry";
    case PacketKind::Statistics:
      return "Statistics";
    case PacketKind::Unknown:
      return "Unknown";
  }
  return "Unknown";
}

}  // namespace corroventa::protocol
