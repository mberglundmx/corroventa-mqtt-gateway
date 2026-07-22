#include "corroventa/protocol/FrameEncoder.hpp"

#include "corroventa/protocol/Crc16.hpp"
#include "corroventa/protocol/Sync.hpp"

namespace corroventa::protocol {
namespace {

void appendSync(std::vector<std::uint8_t>& out) {
  out.insert(out.end(), kSyncWord.begin(), kSyncWord.end());
}

void appendCrc(std::vector<std::uint8_t>& out, std::size_t crc_start) {
  const std::uint16_t crc = crc16Cms(ByteSpan(out.data() + crc_start, out.size() - crc_start));
  out.push_back(static_cast<std::uint8_t>((crc >> 8) & 0xFF));
  out.push_back(static_cast<std::uint8_t>(crc & 0xFF));
}

}  // namespace

std::vector<std::uint8_t> FrameEncoder::encode(const ConfigWritePacket& packet) const {
  std::vector<std::uint8_t> out;
  out.reserve(21);
  appendSync(out);
  const std::size_t crc_start = out.size();
  out.push_back(ConfigWritePacket::length_byte);
  out.insert(out.end(), packet.header.begin(), packet.header.end());
  out.push_back(static_cast<std::uint8_t>(packet.config.hyst_lo));
  out.push_back(static_cast<std::uint8_t>(packet.config.hyst_hi));
  out.push_back(static_cast<std::uint8_t>(packet.config.mgi));
  out.push_back(packet.config.static_rf);
  out.push_back(packet.config.alarm_rf);
  out.push_back(packet.config.continuous_fan ? 0x02 : 0x00);
  out.push_back(packet.config.mgi_mode ? 0x01 : 0x00);
  appendCrc(out, crc_start);
  return out;
}

std::vector<std::uint8_t> FrameEncoder::encode(const KeepalivePacket& packet) const {
  std::vector<std::uint8_t> out;
  out.reserve(14);
  appendSync(out);
  const std::size_t crc_start = out.size();
  out.push_back(KeepalivePacket::length_byte);
  const std::uint8_t header[] = {0xF5, 0x01, 0x40, 0x01, 0x82, 0x01};
  out.insert(out.end(), header, header + sizeof(header));
  out.push_back(packet.seq);
  appendCrc(out, crc_start);
  return out;
}

}  // namespace corroventa::protocol
