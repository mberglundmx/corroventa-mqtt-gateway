#include "test_assert.hpp"

int run_decode_fixture_tests();
int run_encode_config_write_tests();

int main() {
  int failures = 0;
  failures += run_decode_fixture_tests();
  failures += run_encode_config_write_tests();
  return failures == 0 ? 0 : 1;
}
