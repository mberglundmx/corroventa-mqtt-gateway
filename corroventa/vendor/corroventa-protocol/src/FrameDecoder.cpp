#include "corroventa/protocol/FrameDecoder.hpp"

#include "corroventa/protocol/ConfigBlock.hpp"
#include "corroventa/protocol/Sync.hpp"

#include <cstring>

namespace corroventa::protocol {
namespace {

bool hasSync(ByteSpan data) {
  if (data.size() < kSyncWord.size()) {
    return false;
  }
  return std::memcmp(data.data(), kSyncWord.data(), kSyncWord.size()) == 0;
}

std::uint16_t readU16Le(ByteSpan data, std::size_t offset) {
  return static_cast<std::uint16_t>(data[offset] | (static_cast<std::uint16_t>(data[offset + 1]) << 8));
}

std::uint32_t readU32Le(ByteSpan data, std::size_t offset) {
  return static_cast<std::uint32_t>(data[offset]) |
         (static_cast<std::uint32_t>(data[offset + 1]) << 8) |
         (static_cast<std::uint32_t>(data[offset + 2]) << 16) |
         (static_cast<std::uint32_t>(data[offset + 3]) << 24);
}

ConfigBlock readConfigBlock(ByteSpan frame) {
  ConfigBlock cfg;
  cfg.hyst_lo = asSigned(frame[12]);
  cfg.hyst_hi = asSigned(frame[13]);
  cfg.mgi = asSigned(frame[14]);
  cfg.static_rf = frame[15];
  cfg.alarm_rf = frame[16];
  cfg.continuous_fan = frame[17] == 0x02;
  cfg.mgi_mode = frame[18] == 0x01;
  return cfg;
}

DecodeResult fail(DecodeError error, std::size_t consumed = 0) {
  return DecodeFailure{error, consumed};
}

DecodeResult decodeInternal(ByteSpan data) {
  if (data.size() < 5) {
    return fail(DecodeError::TooShort);
  }
  if (!hasSync(data)) {
    return fail(DecodeError::BadSync);
  }

  const std::uint8_t length_byte = data[4];
  const std::size_t total = frameTotalLength(length_byte);
  if (data.size() < total) {
    return fail(DecodeError::Truncated, data.size());
  }

  const ByteSpan frame = data.subspan(0, total);
  PacketKind kind = packetKindFromFrame(frame);
  // Sanity: known kinds must carry their usual L (framing still uses L).
  if (kind != PacketKind::Unknown && length_byte != expectedLengthByte(kind)) {
    kind = PacketKind::Unknown;
  }

  DecodeSuccess ok;
  ok.kind = kind;
  ok.frame_size = total;

  switch (kind) {
    case PacketKind::Keepalive: {
      KeepalivePacket p;
      p.seq = frame[11];
      ok.packet = p;
      break;
    }
    case PacketKind::PairingBeacon: {
      PairingBeaconPacket p;
      p.device_id = readU32Le(frame, 11);
      ok.packet = p;
      break;
    }
    case PacketKind::ConfigWrite: {
      ConfigWritePacket p;
      for (std::size_t i = 0; i < p.header.size(); ++i) {
        p.header[i] = frame[5 + i];
      }
      p.config = readConfigBlock(frame);
      ok.packet = p;
      break;
    }
    case PacketKind::Poll: {
      PollPacket p;
      p.year = readU16Le(frame, 13);
      p.month = frame[15];
      p.day = frame[16];
      p.hour = frame[17];
      p.minute = frame[18];
      p.second = frame[19];
      for (std::size_t i = 0; i < p.link_blob.size(); ++i) {
        p.link_blob[i] = frame[20 + i];
      }
      ok.packet = p;
      break;
    }
    case PacketKind::ConfigStatus: {
      ConfigStatusPacket p;
      p.config = readConfigBlock(frame);
      p.device_id = readU32Le(frame, 19);
      for (std::size_t i = 0; i < p.link_blob.size(); ++i) {
        p.link_blob[i] = frame[23 + i];
      }
      ok.packet = p;
      break;
    }
    case PacketKind::Telemetry: {
      TelemetryPacket p;
      p.relative_humidity_percent = static_cast<float>(readU16Le(frame, 12)) / 10.0F;
      p.temperature_c = static_cast<float>(readU16Le(frame, 14)) / 10.0F;
      p.fan_running = frame[16] == 0x01;
      p.dehumidifying = frame[17] == 0x01;
      p.service_days = frame[23];
      p.year = readU16Le(frame, 25);
      p.month = frame[27];
      p.day = frame[28];
      p.hour = frame[29];
      p.minute = frame[30];
      p.second = frame[31];
      ok.packet = p;
      break;
    }
    case PacketKind::Statistics: {
      StatisticsPacket p;
      for (std::size_t i = 0; i < 12; ++i) {
        p.operating_hours[i] = readU16Le(frame, 12 + 2 * i);
        p.mean_temperature_c[i] = frame[36 + i];
        p.mean_rh_percent[i] = frame[48 + i];
      }
      ok.packet = p;
      break;
    }
    case PacketKind::Unknown: {
      UnknownPacket p;
      p.length_byte = length_byte;
      p.payload.assign(frame.begin() + 5, frame.begin() + 5 + length_byte);
      ok.packet = p;
      ok.kind = PacketKind::Unknown;
      break;
    }
  }

  return ok;
}

}  // namespace

DecodeResult FrameDecoder::decode(ByteSpan data) const {
  return decodeInternal(data);
}

DecodeResult FrameDecoder::decodeAllowUnknown(ByteSpan data) const {
  return decodeInternal(data);
}

}  // namespace corroventa::protocol
