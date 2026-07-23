#pragma once

#include "corroventa/protocol/ByteSpan.hpp"

#include <cstdint>

namespace corroventa::protocol {

/// Packet class. Command-bearing kinds use the on-air command byte at [11] as the
/// enumerator value. Keepalive / PairingBeacon have no command at [11].
enum class PacketKind : std::uint8_t {
  Keepalive = 0x00,       // N==1 at [10]; [11] is seq
  PairingBeacon = 0xFE,   // family [5]==0xFF; [11] starts UI id
  ConfigWrite = 0x22,     // command at [11]
  Poll = 0x20,
  ConfigStatus = 0x1F,
  Telemetry = 0x21,
  Statistics = 0x26,
  Unknown = 0xFF,
};

/// Family / mode byte at payload[0] == frame[5]. Hypothesis — see protocol docs.
inline constexpr std::uint8_t kFamilyPaired = 0xF5;
inline constexpr std::uint8_t kFamilyPairing = 0xFF;

/// Classify from logical frame bytes (sync ‖ L ‖ payload).
/// Primary discriminator: command at [11] (hypothesis). Exceptions: pairing family
/// and keepalive inner-length N==1. Length L is still used for framing and as a
/// sanity check against the known size for each kind.
[[nodiscard]] constexpr PacketKind packetKindFromFrame(ByteSpan frame) noexcept {
  if (frame.size() < 12) {
    return PacketKind::Unknown;
  }
  if (frame[5] == kFamilyPairing) {
    return PacketKind::PairingBeacon;
  }
  // Inner length N at [10]; N==1 ⇒ keepalive (body is seq only — no command).
  if (frame[10] == 0x01) {
    return PacketKind::Keepalive;
  }
  switch (frame[11]) {
    case static_cast<std::uint8_t>(PacketKind::ConfigWrite):
      return PacketKind::ConfigWrite;
    case static_cast<std::uint8_t>(PacketKind::Poll):
      return PacketKind::Poll;
    case static_cast<std::uint8_t>(PacketKind::ConfigStatus):
      return PacketKind::ConfigStatus;
    case static_cast<std::uint8_t>(PacketKind::Telemetry):
      return PacketKind::Telemetry;
    case static_cast<std::uint8_t>(PacketKind::Statistics):
      return PacketKind::Statistics;
    default:
      return PacketKind::Unknown;
  }
}

[[nodiscard]] constexpr std::uint8_t expectedLengthByte(PacketKind kind) noexcept {
  switch (kind) {
    case PacketKind::Keepalive:
      return 0x07;
    case PacketKind::PairingBeacon:
      return 0x0B;
    case PacketKind::ConfigWrite:
      return 0x0E;
    case PacketKind::Poll:
      return 0x16;
    case PacketKind::ConfigStatus:
      return 0x1D;
    case PacketKind::Telemetry:
      return 0x22;
    case PacketKind::Statistics:
      return 0x37;
    case PacketKind::Unknown:
      return 0;
  }
  return 0;
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
