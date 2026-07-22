#include "test_assert.hpp"

#include "corroventa/protocol/Crc16.hpp"

int run_crc16_tests() {
  using namespace corroventa::protocol;
  using namespace corroventa::protocol::test;

  // ConfigWrite MGI -7 body [4:19]
  const std::uint8_t body[] = {
      0x0E, 0xF5, 0x01, 0x40, 0x01, 0x82, 0x08, 0x22, 0xFE, 0x02, 0xF9, 0x41, 0x0A, 0x00, 0x01};
  EXPECT(crc16Cms(body, sizeof(body)) == 0x690C);

  // Keepalive body
  const std::uint8_t ka[] = {0x07, 0xF5, 0x01, 0x40, 0x01, 0x82, 0x01, 0x1E};
  EXPECT(crc16Cms(ka, sizeof(ka)) == 0xF6FE);

  return g_failures;
}
