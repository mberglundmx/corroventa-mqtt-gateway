#pragma once

#include "corroventa/protocol/ConfigBlock.hpp"
#include "corroventa/protocol/PacketKind.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <vector>

namespace corroventa::protocol {

struct KeepalivePacket {
  static constexpr PacketKind kind = PacketKind::Keepalive;
  static constexpr std::uint8_t length_byte = 0x07;

  std::uint8_t seq = 0;
};

struct PairingBeaconPacket {
  static constexpr PacketKind kind = PacketKind::PairingBeacon;
  static constexpr std::uint8_t length_byte = 0x0B;

  std::uint32_t device_id = 0;  // LE on wire
};

struct ConfigWritePacket {
  static constexpr PacketKind kind = PacketKind::ConfigWrite;
  static constexpr std::uint8_t length_byte = 0x0E;

  /// Pair-/device-specific addressing prefix (not a global constant).
  /// Hosts/Device Manager must supply this from observed air traffic.
  std::array<std::uint8_t, 7> header{};
  ConfigBlock config{};
};

struct PollPacket {
  static constexpr PacketKind kind = PacketKind::Poll;
  static constexpr std::uint8_t length_byte = 0x16;

  std::uint16_t year = 0;
  std::uint8_t month = 0;
  std::uint8_t day = 0;
  std::uint8_t hour = 0;
  std::uint8_t minute = 0;
  std::uint8_t second = 0;
  std::array<std::uint8_t, 6> link_blob{};
};

struct ConfigStatusPacket {
  static constexpr PacketKind kind = PacketKind::ConfigStatus;
  static constexpr std::uint8_t length_byte = 0x1D;

  ConfigBlock config{};
  std::uint32_t device_id = 0;
  std::array<std::uint8_t, 6> link_blob{};
};

struct TelemetryPacket {
  static constexpr PacketKind kind = PacketKind::Telemetry;
  static constexpr std::uint8_t length_byte = 0x22;

  float relative_humidity_percent = 0.0F;  // raw/10
  float temperature_c = 0.0F;              // raw/10
  bool fan_running = false;
  bool dehumidifying = false;
  std::uint8_t service_days = 0;
  std::uint16_t year = 0;
  std::uint8_t month = 0;
  std::uint8_t day = 0;
  std::uint8_t hour = 0;
  std::uint8_t minute = 0;
  std::uint8_t second = 0;
};

struct StatisticsPacket {
  static constexpr PacketKind kind = PacketKind::Statistics;
  static constexpr std::uint8_t length_byte = 0x37;

  /// Index 0 = current month, then previous months backward.
  std::array<std::uint16_t, 12> operating_hours{};
  std::array<std::uint8_t, 12> mean_temperature_c{};
  std::array<std::uint8_t, 12> mean_rh_percent{};
};

struct UnknownPacket {
  static constexpr PacketKind kind = PacketKind::Unknown;

  std::uint8_t length_byte = 0;
  std::vector<std::uint8_t> payload;  // bytes after length byte

};

}  // namespace corroventa::protocol
