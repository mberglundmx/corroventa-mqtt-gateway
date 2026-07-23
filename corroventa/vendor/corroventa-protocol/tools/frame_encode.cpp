#include "corroventa/protocol/FrameEncoder.hpp"
#include "corroventa/protocol/Packets.hpp"

#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

void printHex(const std::vector<std::uint8_t>& frame) {
  for (std::size_t i = 0; i < frame.size(); ++i) {
    if (i) {
      std::cout << ' ';
    }
    std::cout << std::hex << std::setw(2) << std::setfill('0') << std::uppercase
              << static_cast<int>(frame[i]);
  }
  std::cout << std::dec << '\n';
}

void usage(const char* argv0) {
  std::cerr
      << "Usage:\n"
      << "  " << argv0
      << " config-write [--mgi N] [--hyst-lo N] [--hyst-hi N] [--rf N] [--alarm N]\n"
      << "              [--fan on|off] [--mode mgi|static]\n"
      << "  " << argv0 << " keepalive [--seq HEX]\n"
      << "\nPrints one logical frame as hex (sync‖L‖payload) on stdout.\n";
}

std::int8_t parseI8(const std::string& s) {
  return static_cast<std::int8_t>(std::stoi(s));
}

std::uint8_t parseU8(const std::string& s) {
  return static_cast<std::uint8_t>(std::stoul(s, nullptr, 0));
}

}  // namespace

int main(int argc, char** argv) {
  using namespace corroventa::protocol;

  if (argc < 2) {
    usage(argv[0]);
    return 2;
  }

  const std::string cmd = argv[1];
  FrameEncoder encoder;

  if (cmd == "config-write") {
    ConfigWritePacket packet;
    // Fixture header from captures (pair-specific — callers must set explicitly).
    packet.header = {0xF5, 0x01, 0x40, 0x01, 0x82, 0x08, 0x22};
    // Defaults match fixtures/config_write_mgi_m7.hex (paired HV baseline).
    packet.config.hyst_lo = -2;
    packet.config.hyst_hi = 2;
    packet.config.mgi = -7;
    packet.config.static_rf = 65;
    packet.config.alarm_rf = 10;
    packet.config.continuous_fan = false;
    packet.config.mgi_mode = true;

    for (int i = 2; i < argc; ++i) {
      const std::string arg = argv[i];
      auto need = [&](const char* name) -> std::string {
        if (i + 1 >= argc) {
          std::cerr << "missing value for " << name << "\n";
          std::exit(2);
        }
        return argv[++i];
      };
      if (arg == "--mgi") {
        packet.config.mgi = parseI8(need("--mgi"));
      } else if (arg == "--hyst-lo") {
        packet.config.hyst_lo = parseI8(need("--hyst-lo"));
      } else if (arg == "--hyst-hi") {
        packet.config.hyst_hi = parseI8(need("--hyst-hi"));
      } else if (arg == "--rf") {
        packet.config.static_rf = parseU8(need("--rf"));
      } else if (arg == "--alarm") {
        packet.config.alarm_rf = parseU8(need("--alarm"));
      } else if (arg == "--fan") {
        const std::string v = need("--fan");
        if (v == "on") {
          packet.config.continuous_fan = true;
        } else if (v == "off") {
          packet.config.continuous_fan = false;
        } else {
          std::cerr << "fan must be on|off\n";
          return 2;
        }
      } else if (arg == "--mode") {
        const std::string v = need("--mode");
        if (v == "mgi") {
          packet.config.mgi_mode = true;
        } else if (v == "static") {
          packet.config.mgi_mode = false;
        } else {
          std::cerr << "mode must be mgi|static\n";
          return 2;
        }
      } else if (arg == "-h" || arg == "--help") {
        usage(argv[0]);
        return 0;
      } else {
        std::cerr << "unknown arg: " << arg << "\n";
        usage(argv[0]);
        return 2;
      }
    }

    printHex(encoder.encode(packet));
    return 0;
  }

  if (cmd == "keepalive") {
    KeepalivePacket packet;
    packet.seq = 0x1E;
    for (int i = 2; i < argc; ++i) {
      const std::string arg = argv[i];
      if (arg == "--seq") {
        if (i + 1 >= argc) {
          std::cerr << "missing --seq value\n";
          return 2;
        }
        packet.seq = parseU8(argv[++i]);
      } else {
        std::cerr << "unknown arg: " << arg << "\n";
        return 2;
      }
    }
    printHex(encoder.encode(packet));
    return 0;
  }

  usage(argv[0]);
  return 2;
}
