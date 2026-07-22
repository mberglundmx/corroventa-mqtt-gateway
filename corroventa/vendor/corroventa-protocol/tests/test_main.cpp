#include <cstdlib>
#include <iostream>

int run_crc16_tests();
int run_decode_fixture_tests();
int run_encode_config_write_tests();

int main() {
  int failures = 0;
  failures += run_crc16_tests();
  failures += run_decode_fixture_tests();
  failures += run_encode_config_write_tests();
  if (failures != 0) {
    std::cerr << failures << " test(s) failed\n";
    return EXIT_FAILURE;
  }
  std::cout << "All tests passed\n";
  return EXIT_SUCCESS;
}
