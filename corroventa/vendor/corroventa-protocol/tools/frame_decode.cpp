#include "corroventa/protocol/FrameDecoder.hpp"
#include "corroventa/protocol/Packet.hpp"

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

namespace {

std::vector<std::uint8_t> parseHexLine(const std::string& line) {
  std::vector<std::uint8_t> out;
  std::stringstream ss(line);
  std::string token;
  while (ss >> token) {
    if (token.size() >= 2 && token[0] == '0' && (token[1] == 'x' || token[1] == 'X')) {
      token = token.substr(2);
    }
    if (token.empty()) {
      continue;
    }
    out.push_back(static_cast<std::uint8_t>(std::stoul(token, nullptr, 16)));
  }
  return out;
}

void printPacket(const corroventa::protocol::DecodeSuccess& ok) {
  using namespace corroventa::protocol;
  std::cout << toString(ok.kind) << "  bytes=" << ok.frame_size;
  std::visit(
      [](const auto& p) {
        using T = std::decay_t<decltype(p)>;
        if constexpr (std::is_same_v<T, ConfigWritePacket>) {
          std::cout << "  mgi=" << static_cast<int>(p.config.mgi)
                    << " rf=" << static_cast<int>(p.config.static_rf)
                    << " mode=" << (p.config.mgi_mode ? "MGI" : "static");
        } else if constexpr (std::is_same_v<T, ConfigStatusPacket>) {
          std::cout << "  mgi=" << static_cast<int>(p.config.mgi)
                    << " id=" << p.device_id;
        } else if constexpr (std::is_same_v<T, TelemetryPacket>) {
          std::cout << std::fixed << std::setprecision(1)
                    << "  RH=" << p.relative_humidity_percent
                    << "% T=" << p.temperature_c << "C"
                    << " fan=" << (p.fan_running ? "on" : "off")
                    << " dehum=" << (p.dehumidifying ? "on" : "off")
                    << " service_d=" << static_cast<int>(p.service_days);
        } else if constexpr (std::is_same_v<T, StatisticsPacket>) {
          std::cout << "  hours0=" << p.operating_hours[0]
                    << " temp0=" << static_cast<int>(p.mean_temperature_c[0])
                    << " rh0=" << static_cast<int>(p.mean_rh_percent[0]);
        } else if constexpr (std::is_same_v<T, KeepalivePacket>) {
          std::cout << "  seq=0x" << std::hex << static_cast<int>(p.seq) << std::dec;
        } else if constexpr (std::is_same_v<T, PollPacket>) {
          std::cout << "  " << p.year << "-" << static_cast<int>(p.month) << "-"
                    << static_cast<int>(p.day) << " "
                    << static_cast<int>(p.hour) << ":" << static_cast<int>(p.minute) << ":"
                    << static_cast<int>(p.second);
        } else if constexpr (std::is_same_v<T, PairingBeaconPacket>) {
          std::cout << "  id=" << p.device_id;
        } else if constexpr (std::is_same_v<T, UnknownPacket>) {
          std::cout << "  L=0x" << std::hex << static_cast<int>(p.length_byte) << std::dec;
        }
      },
      ok.packet);
  std::cout << "\n";
}

}  // namespace

int main() {
  using namespace corroventa::protocol;
  FrameDecoder decoder;
  std::string line;
  int ok_n = 0;
  int fail_n = 0;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#') {
      continue;
    }
    const auto frame = parseHexLine(line);
    if (frame.empty()) {
      continue;
    }
    const auto result = decoder.decode(ByteSpan(frame.data(), frame.size()));
    if (std::holds_alternative<DecodeSuccess>(result)) {
      printPacket(std::get<DecodeSuccess>(result));
      ++ok_n;
    } else {
      const auto& err = std::get<DecodeFailure>(result);
      std::cout << "FAIL " << toString(err.error) << "\n";
      ++fail_n;
    }
  }
  std::cerr << "decoded_ok=" << ok_n << " fail=" << fail_n << "\n";
  return fail_n == 0 ? 0 : 1;
}
