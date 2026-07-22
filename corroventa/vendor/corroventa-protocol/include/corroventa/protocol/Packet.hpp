#pragma once

#include "corroventa/protocol/Packets.hpp"

#include <type_traits>
#include <variant>

namespace corroventa::protocol {

using Packet = std::variant<KeepalivePacket,
                            PairingBeaconPacket,
                            ConfigWritePacket,
                            PollPacket,
                            ConfigStatusPacket,
                            TelemetryPacket,
                            StatisticsPacket,
                            UnknownPacket>;

[[nodiscard]] inline PacketKind packetKind(const Packet& packet) noexcept {
  return std::visit([](const auto& p) -> PacketKind { return std::decay_t<decltype(p)>::kind; },
                    packet);
}

}  // namespace corroventa::protocol
