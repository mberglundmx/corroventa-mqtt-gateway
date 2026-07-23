#include "corroventa/protocol/FrameEncoder.hpp"

#include "corroventa/protocol/Sync.hpp"

namespace corroventa::protocol {
namespace {

void appendSync(std::vector<std::uint8_t>& out) {
  out.insert(out.end(), kSyncWord.begin(), kSyncWord.end());
}

}  // namespace

std::vector<std::uint8_t> FrameEncoder::encode(const ConfigWritePacket& packet) const {
  std::vector<std::uint8_t> out;
  out.reserve(frameTotalLength(ConfigWritePacket::length_byte));
  appendSync(out);
  out.push_back(ConfigWritePacket::length_byte);
  out.insert(out.end(), packet.header.begin(), packet.header.end());
  out.push_back(static_cast<std::uint8_t>(packet.config.hyst_lo));
  out.push_back(static_cast<std::uint8_t>(packet.config.hyst_hi));
  out.push_back(static_cast<std::uint8_t>(packet.config.mgi));
  out.push_back(packet.config.static_rf);
  out.push_back(packet.config.alarm_rf);
  out.push_back(packet.config.continuous_fan ? 0x01 : 0x00);
  out.push_back(packet.config.mgi_mode ? 0x01 : 0x00);
  return out;
}

std::vector<std::uint8_t> FrameEncoder::encode(const KeepalivePacket& packet) const {
  std::vector<std::uint8_t> out;
  out.reserve(frameTotalLength(KeepalivePacket::length_byte));
  appendSync(out);
  out.push_back(KeepalivePacket::length_byte);
  const std::uint8_t header[] = {0xF5, 0x01, 0x40, 0x01, 0x82, 0x01};
  out.insert(out.end(), header, header + sizeof(header));
  out.push_back(packet.seq);
  return out;
}

}  // namespace corroventa::protocol
