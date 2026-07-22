#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "corroventa/protocol/Crc16.hpp"
#include "corroventa/protocol/FrameDecoder.hpp"
#include "corroventa/protocol/FrameEncoder.hpp"
#include "corroventa/protocol/Packet.hpp"

#include <algorithm>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

namespace py = pybind11;
using namespace corroventa::protocol;

namespace {

std::string kindSnake(PacketKind kind) {
  switch (kind) {
    case PacketKind::Keepalive:
      return "keepalive";
    case PacketKind::PairingBeacon:
      return "pairing_beacon";
    case PacketKind::ConfigWrite:
      return "config_write";
    case PacketKind::Poll:
      return "poll";
    case PacketKind::ConfigStatus:
      return "config_status";
    case PacketKind::Telemetry:
      return "telemetry";
    case PacketKind::Statistics:
      return "statistics";
    case PacketKind::Unknown:
      return "unknown";
  }
  return "unknown";
}

struct TelemetryView {
  float relative_humidity_percent = 0;
  float temperature_c = 0;
  bool fan_running = false;
  bool dehumidifying = false;
  std::uint8_t service_days = 0;
  std::uint16_t year = 0;
  std::uint8_t month = 0;
  std::uint8_t day = 0;
  std::uint8_t hour = 0;
  std::uint8_t minute = 0;
  std::uint8_t second = 0;

  py::dict to_public_dict() const {
    py::dict d;
    d["relative_humidity_percent"] = relative_humidity_percent;
    d["temperature_c"] = temperature_c;
    d["fan_running"] = fan_running;
    d["dehumidifying"] = dehumidifying;
    d["service_days"] = service_days;
    d["year"] = year;
    d["month"] = month;
    d["day"] = day;
    d["hour"] = hour;
    d["minute"] = minute;
    d["second"] = second;
    char buf[32];
    std::snprintf(buf,
                  sizeof(buf),
                  "%04u-%02u-%02uT%02u:%02u:%02u",
                  static_cast<unsigned>(year),
                  static_cast<unsigned>(month),
                  static_cast<unsigned>(day),
                  static_cast<unsigned>(hour),
                  static_cast<unsigned>(minute),
                  static_cast<unsigned>(second));
    d["datetime"] = buf;
    return d;
  }
};

struct StatisticsView {
  std::vector<std::uint16_t> operating_hours;
  std::vector<std::uint8_t> mean_temperature_c;
  std::vector<std::uint8_t> mean_rh_percent;

  py::dict to_public_dict() const {
    py::dict d;
    d["operating_hours"] = operating_hours;
    d["mean_temperature_c"] = mean_temperature_c;
    d["mean_rh_percent"] = mean_rh_percent;
    return d;
  }
};

struct DecodedFrame {
  std::string kind;
  std::optional<std::uint32_t> device_id;
  std::optional<ConfigBlock> config;
  /// ConfigWrite [5:12] — pair-specific; Device Manager must track per device.
  std::optional<py::bytes> config_write_header;
  std::optional<TelemetryView> telemetry;
  std::optional<StatisticsView> statistics;
  py::bytes raw;
};

std::vector<std::uint8_t> asBytes(const py::bytes& data) {
  const std::string buffer = data;
  return std::vector<std::uint8_t>(buffer.begin(), buffer.end());
}

py::bytes encode_config_write(const ConfigBlock& config, py::bytes header) {
  const std::vector<std::uint8_t> hdr = asBytes(header);
  if (hdr.size() != 7) {
    throw std::invalid_argument("ConfigWrite header must be exactly 7 bytes");
  }
  ConfigWritePacket packet;
  std::copy(hdr.begin(), hdr.end(), packet.header.begin());
  packet.config = config;
  const std::vector<std::uint8_t> frame = FrameEncoder{}.encode(packet);
  return py::bytes(reinterpret_cast<const char*>(frame.data()), frame.size());
}

std::optional<DecodedFrame> decode_frame(py::bytes data) {
  const std::vector<std::uint8_t> bytes = asBytes(data);
  if (bytes.empty()) {
    return std::nullopt;
  }

  const ByteSpan span(bytes.data(), bytes.size());
  const DecodeResult result = FrameDecoder{}.decode(span);
  if (!std::holds_alternative<DecodeSuccess>(result)) {
    return std::nullopt;
  }

  const DecodeSuccess& ok = std::get<DecodeSuccess>(result);
  DecodedFrame out;
  out.kind = kindSnake(ok.kind);
  out.raw = py::bytes(reinterpret_cast<const char*>(bytes.data()),
                      static_cast<py::ssize_t>(ok.frame_size));

  std::visit(
      [&](const auto& packet) {
        using T = std::decay_t<decltype(packet)>;
        if constexpr (std::is_same_v<T, ConfigStatusPacket>) {
          out.config = packet.config;
          out.device_id = packet.device_id;
        } else if constexpr (std::is_same_v<T, ConfigWritePacket>) {
          out.config = packet.config;
          out.config_write_header =
              py::bytes(reinterpret_cast<const char*>(packet.header.data()), 7);
        } else if constexpr (std::is_same_v<T, PairingBeaconPacket>) {
          out.device_id = packet.device_id;
        } else if constexpr (std::is_same_v<T, TelemetryPacket>) {
          TelemetryView tel;
          tel.relative_humidity_percent = packet.relative_humidity_percent;
          tel.temperature_c = packet.temperature_c;
          tel.fan_running = packet.fan_running;
          tel.dehumidifying = packet.dehumidifying;
          tel.service_days = packet.service_days;
          tel.year = packet.year;
          tel.month = packet.month;
          tel.day = packet.day;
          tel.hour = packet.hour;
          tel.minute = packet.minute;
          tel.second = packet.second;
          out.telemetry = tel;
        } else if constexpr (std::is_same_v<T, StatisticsPacket>) {
          StatisticsView stats;
          stats.operating_hours.assign(packet.operating_hours.begin(), packet.operating_hours.end());
          stats.mean_temperature_c.assign(packet.mean_temperature_c.begin(),
                                          packet.mean_temperature_c.end());
          stats.mean_rh_percent.assign(packet.mean_rh_percent.begin(), packet.mean_rh_percent.end());
          out.statistics = stats;
        }
      },
      ok.packet);

  return out;
}

std::uint16_t crc16_cms_py(py::bytes data) {
  const std::vector<std::uint8_t> bytes = asBytes(data);
  return crc16Cms(ByteSpan(bytes.data(), bytes.size()));
}

}  // namespace

PYBIND11_MODULE(corroventa_protocol, m) {
  m.doc() = "Python bindings for corroventa-protocol (C++17 TRUE-phase codec)";

  py::class_<ConfigBlock>(m, "ConfigBlock")
      .def(py::init<>())
      .def_readwrite("hyst_lo", &ConfigBlock::hyst_lo)
      .def_readwrite("hyst_hi", &ConfigBlock::hyst_hi)
      .def_readwrite("mgi", &ConfigBlock::mgi)
      .def_readwrite("static_rf", &ConfigBlock::static_rf)
      .def_readwrite("alarm_rf", &ConfigBlock::alarm_rf)
      .def_readwrite("continuous_fan", &ConfigBlock::continuous_fan)
      .def_readwrite("mgi_mode", &ConfigBlock::mgi_mode)
      .def(
          "to_public_dict",
          [](const ConfigBlock& c) {
            py::dict d;
            d["hyst_lo"] = c.hyst_lo;
            d["hyst_hi"] = c.hyst_hi;
            d["mgi"] = c.mgi;
            d["static_rf"] = c.static_rf;
            d["alarm_rf"] = c.alarm_rf;
            d["continuous_fan"] = c.continuous_fan;
            d["mgi_mode"] = c.mgi_mode ? "mgi" : "static";
            return d;
          })
      .def(
          "merge_patch",
          [](const ConfigBlock& self, py::dict patch) {
            ConfigBlock out = self;
            if (patch.contains("hyst_lo")) {
              out.hyst_lo = py::cast<std::int8_t>(patch["hyst_lo"]);
            }
            if (patch.contains("hyst_hi")) {
              out.hyst_hi = py::cast<std::int8_t>(patch["hyst_hi"]);
            }
            if (patch.contains("mgi")) {
              out.mgi = py::cast<std::int8_t>(patch["mgi"]);
            }
            if (patch.contains("static_rf")) {
              out.static_rf = py::cast<std::uint8_t>(patch["static_rf"]);
            }
            if (patch.contains("alarm_rf")) {
              out.alarm_rf = py::cast<std::uint8_t>(patch["alarm_rf"]);
            }
            if (patch.contains("continuous_fan")) {
              out.continuous_fan = py::cast<bool>(patch["continuous_fan"]);
            }
            if (patch.contains("mgi_mode")) {
              const py::object val = patch["mgi_mode"];
              if (py::isinstance<py::bool_>(val)) {
                out.mgi_mode = py::cast<bool>(val);
              } else {
                const std::string s = py::cast<std::string>(val);
                out.mgi_mode = (s == "mgi" || s == "true" || s == "1" || s == "on");
              }
            }
            return out;
          });

  py::class_<TelemetryView>(m, "Telemetry")
      .def_readonly("relative_humidity_percent", &TelemetryView::relative_humidity_percent)
      .def_readonly("temperature_c", &TelemetryView::temperature_c)
      .def_readonly("fan_running", &TelemetryView::fan_running)
      .def_readonly("dehumidifying", &TelemetryView::dehumidifying)
      .def_readonly("service_days", &TelemetryView::service_days)
      .def_readonly("year", &TelemetryView::year)
      .def_readonly("month", &TelemetryView::month)
      .def_readonly("day", &TelemetryView::day)
      .def_readonly("hour", &TelemetryView::hour)
      .def_readonly("minute", &TelemetryView::minute)
      .def_readonly("second", &TelemetryView::second)
      .def("to_public_dict", &TelemetryView::to_public_dict);

  py::class_<StatisticsView>(m, "Statistics")
      .def_readonly("operating_hours", &StatisticsView::operating_hours)
      .def_readonly("mean_temperature_c", &StatisticsView::mean_temperature_c)
      .def_readonly("mean_rh_percent", &StatisticsView::mean_rh_percent)
      .def("to_public_dict", &StatisticsView::to_public_dict);

  py::class_<DecodedFrame>(m, "DecodedFrame")
      .def_readonly("kind", &DecodedFrame::kind)
      .def_readonly("device_id", &DecodedFrame::device_id)
      .def_readonly("config", &DecodedFrame::config)
      .def_readonly("config_write_header", &DecodedFrame::config_write_header)
      .def_readonly("telemetry", &DecodedFrame::telemetry)
      .def_readonly("statistics", &DecodedFrame::statistics)
      .def_readonly("raw", &DecodedFrame::raw)
      .def_property_readonly("raw_hex", [](const DecodedFrame& f) {
        const auto raw = py::cast<std::string>(f.raw);
        std::string hex;
        hex.reserve(raw.size() * 3);
        static const char* digits = "0123456789abcdef";
        for (std::size_t i = 0; i < raw.size(); ++i) {
          if (i) {
            hex.push_back(' ');
          }
          const auto b = static_cast<unsigned char>(raw[i]);
          hex.push_back(digits[b >> 4]);
          hex.push_back(digits[b & 0x0F]);
        }
        return hex;
      });

  m.def("decode_frame", &decode_frame, py::arg("data"), "Decode one TRUE-phase frame; None if invalid");
  m.def("encode_config_write",
        &encode_config_write,
        py::arg("config"),
        py::arg("header"),
        "Encode ConfigWrite + CRC (header = 7 pair-specific bytes from Device Manager)");
  m.def("crc16_cms", &crc16_cms_py, py::arg("data"), "CRC-16/CMS over bytes");
}
