cmake_minimum_required(VERSION 3.16)

add_executable(corroventa_protocol_tests
  test_main.cpp
  test_decode_fixtures.cpp
  test_encode_config_write.cpp
)

target_link_libraries(corroventa_protocol_tests PRIVATE corroventa::protocol)

target_compile_definitions(corroventa_protocol_tests
  PRIVATE
    CORROVENTA_PROTOCOL_FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../fixtures"
)

add_test(NAME corroventa_protocol_tests COMMAND corroventa_protocol_tests)
