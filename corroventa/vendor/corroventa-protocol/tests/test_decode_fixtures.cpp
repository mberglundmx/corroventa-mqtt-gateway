#include "test_assert.hpp"

#include "corroventa/protocol/FrameDecoder.hpp"
#include "corroventa/protocol/Packet.hpp"

#include <cstdint>
#include <fstream>
#include <sstream>
#include <string>
#include <variant>
#include <vector>

namespace {

std::vector<std::uint8_t> parseHex(const std::string& text) {
  std::vector<std::uint8_t> out;
  std::stringstream ss(text);
  std::string token;
  while (ss >> token) {
    out.push_back(static_cast<std::uint8_t>(std::stoul(token, nullptr, 16)));
  }
  return out;
}

std::vector<std::uint8_t> loadFixture(const char* name) {
  const std::string path = std::string(CORROVENTA_PROTOCOL_FIXTURES_DIR) + "/" + name;
  std::ifstream in(path);
  EXPECT(in.good());
  std::stringstream buffer;
  buffer << in.rdbuf();
  return parseHex(buffer.str());
}

template <typename T>
const T* as(const corroventa::protocol::DecodeResult& result) {
  if (!std::holds_alternative<corroventa::protocol::DecodeSuccess>(result)) {
    return nullptr;
  }
  const auto& ok = std::get<corroventa::protocol::DecodeSuccess>(result);
  if (!std::holds_alternative<T>(ok.packet)) {
    return nullptr;
  }
  return &std::get<T>(ok.packet);
}

}  // namespace

int run_decode_fixture_tests() {
  using namespace corroventa::protocol;
  using namespace corroventa::protocol::test;

  FrameDecoder decoder;

  {
    const auto frame = loadFixture("config_write_mgi_m7.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<ConfigWritePacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT(p->config.mgi == -7);
      EXPECT(p->config.hyst_lo == -2);
      EXPECT(p->config.hyst_hi == 2);
      EXPECT(p->config.static_rf == 65);
      EXPECT(p->config.alarm_rf == 10);
      EXPECT(!p->config.continuous_fan);
      EXPECT(p->config.mgi_mode);
    }
  }

  {
    const auto frame = loadFixture("config_status_mgi_m7.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<ConfigStatusPacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT(p->config.mgi == -7);
      EXPECT(p->device_id == 1348002652U);
      EXPECT(p->link_blob[0] == 0x69);
      EXPECT(p->link_blob[1] == 0xFD);
    }
  }

  {
    const auto frame = loadFixture("telemetry_baseline.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<TelemetryPacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT_NEAR(p->relative_humidity_percent, 71.5F, 0.05F);
      EXPECT_NEAR(p->temperature_c, 18.2F, 0.05F);
      EXPECT(p->fan_running);
      EXPECT(p->dehumidifying);
      EXPECT(p->service_days == 0x6B);
    }
  }

  {
    const auto frame = loadFixture("statistics_baseline.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<StatisticsPacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT(p->operating_hours[0] == 15);
      EXPECT(p->operating_hours[1] == 68);
      EXPECT(p->operating_hours[5] == 0);
      EXPECT(p->operating_hours[10] == 212);
      EXPECT(p->mean_temperature_c[0] == 17);
      EXPECT(p->mean_rh_percent[0] == 71);
    }
  }

  {
    const auto frame = loadFixture("keepalive.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<KeepalivePacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT(p->seq == 0x1E);
    }
  }

  {
    const auto frame = loadFixture("poll.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<PollPacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT(p->year == 2026);
      EXPECT(p->month == 7);
      EXPECT(p->day == 20);
      EXPECT(p->link_blob[0] == 0x69);
    }
  }

  {
    const auto frame = loadFixture("pairing_beacon.hex");
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    const auto* p = as<PairingBeaconPacket>(result);
    EXPECT(p != nullptr);
    if (p) {
      EXPECT(p->device_id == 1348002652U);
    }
  }

  {
    auto frame = loadFixture("config_write_mgi_m7.hex");
    frame.back() ^= 0x01;
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    EXPECT(std::holds_alternative<DecodeFailure>(result));
    if (std::holds_alternative<DecodeFailure>(result)) {
      EXPECT(std::get<DecodeFailure>(result).error == DecodeError::BadCrc);
    }
  }

  return g_failures;
}
