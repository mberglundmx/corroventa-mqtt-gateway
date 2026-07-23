#include "test_assert.hpp"

#include "corroventa/protocol/FrameDecoder.hpp"
#include "corroventa/protocol/FrameEncoder.hpp"
#include "corroventa/protocol/Packet.hpp"

#include <cstring>
#include <variant>
#include <vector>

int run_encode_config_write_tests() {
  using namespace corroventa::protocol;
  using namespace corroventa::protocol::test;

  ConfigWritePacket packet;
  packet.header = {0xF5, 0x01, 0x40, 0x01, 0x82, 0x08, 0x22};
  packet.config.hyst_lo = -2;
  packet.config.hyst_hi = 2;
  packet.config.mgi = -7;
  packet.config.static_rf = 65;
  packet.config.alarm_rf = 10;
  packet.config.continuous_fan = false;
  packet.config.mgi_mode = true;

  FrameEncoder encoder;
  const std::vector<std::uint8_t> frame = encoder.encode(packet);

  const std::uint8_t expected[] = {
      0xD3, 0x91, 0xD3, 0x91, 0x0E, 0xF5, 0x01, 0x40, 0x01, 0x82, 0x08,
      0x22, 0xFE, 0x02, 0xF9, 0x41, 0x0A, 0x00, 0x01};
  EXPECT(frame.size() == sizeof(expected));
  if (frame.size() == sizeof(expected)) {
    EXPECT(std::memcmp(frame.data(), expected, sizeof(expected)) == 0);
  }

  FrameDecoder decoder;
  const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
  EXPECT(std::holds_alternative<DecodeSuccess>(result));
  if (std::holds_alternative<DecodeSuccess>(result)) {
    const auto& ok = std::get<DecodeSuccess>(result);
    EXPECT(ok.kind == PacketKind::ConfigWrite);
    const auto& decoded = std::get<ConfigWritePacket>(ok.packet);
    EXPECT(decoded.config.mgi == -7);
  }

  packet.config.continuous_fan = true;
  const std::vector<std::uint8_t> fan_on = encoder.encode(packet);
  EXPECT(fan_on.size() == sizeof(expected));
  if (fan_on.size() == sizeof(expected)) {
    EXPECT(fan_on[17] == 0x01);  // canonical ON (ghost was 0x02)
    EXPECT(fan_on[18] == 0x01);
  }

  KeepalivePacket ka;
  ka.seq = 0x1E;
  const auto ka_frame = encoder.encode(ka);
  const auto ka_result = decoder.decode(ByteSpan(ka_frame.data(), ka_frame.size()));
  EXPECT(std::holds_alternative<DecodeSuccess>(ka_result));

  return g_failures;
}
