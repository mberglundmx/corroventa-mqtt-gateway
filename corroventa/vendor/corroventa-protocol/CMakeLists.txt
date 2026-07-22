cmake_minimum_required(VERSION 3.16)
project(corroventa-protocol VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(CORROVENTA_PROTOCOL_BUILD_TESTS "Build protocol unit/replay tests" ON)
option(CORROVENTA_PROTOCOL_BUILD_PYTHON "Build pybind11 module corroventa_protocol" OFF)

add_library(corroventa_protocol
  src/Crc16.cpp
  src/FrameDecoder.cpp
  src/FrameEncoder.cpp
)
add_library(corroventa::protocol ALIAS corroventa_protocol)

target_include_directories(corroventa_protocol
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(corroventa_protocol PUBLIC cxx_std_17)
set_target_properties(corroventa_protocol PROPERTIES POSITION_INDEPENDENT_CODE ON)

if(MSVC)
  target_compile_options(corroventa_protocol PRIVATE /W4)
else()
  target_compile_options(corroventa_protocol PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(CORROVENTA_PROTOCOL_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

add_executable(frame_decode tools/frame_decode.cpp)
target_link_libraries(frame_decode PRIVATE corroventa::protocol)

add_executable(frame_encode tools/frame_encode.cpp)
target_link_libraries(frame_encode PRIVATE corroventa::protocol)

if(CORROVENTA_PROTOCOL_BUILD_PYTHON)
  set(PYBIND11_FINDPYTHON ON)
  include(FetchContent)
  FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.13.6
  )
  FetchContent_MakeAvailable(pybind11)

  pybind11_add_module(corroventa_protocol_py python/bindings.cpp)
  target_link_libraries(corroventa_protocol_py PRIVATE corroventa::protocol)
  set_target_properties(corroventa_protocol_py PROPERTIES OUTPUT_NAME "corroventa_protocol")

  # Convenience: also drop the module next to the build tree root for PYTHONPATH=build
  add_custom_command(
    TARGET corroventa_protocol_py
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:corroventa_protocol_py> ${CMAKE_BINARY_DIR}/
    COMMENT "Copy corroventa_protocol module to build/"
  )
endif()
