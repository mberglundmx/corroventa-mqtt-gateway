# Fallback build when CMake is unavailable. Prefer: cmake -S . -B build && cmake --build build
CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Wpedantic -O2
INCLUDES := -Iinclude
FIXTURES := -DCORROVENTA_PROTOCOL_FIXTURES_DIR=\"$(CURDIR)/fixtures\"

LIB_SRCS := src/Crc16.cpp src/FrameDecoder.cpp src/FrameEncoder.cpp
TEST_SRCS := tests/test_main.cpp tests/test_crc16.cpp tests/test_decode_fixtures.cpp tests/test_encode_config_write.cpp

.PHONY: all test clean tools python

all: build/corroventa_protocol_tests build/frame_decode build/frame_encode

# Prefer CMake for the pybind11 module:
#   cmake -S . -B build-python -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON -DCORROVENTA_PROTOCOL_BUILD_TESTS=OFF
#   cmake --build build-python -j
python:
	@echo "Use CMake: cmake -S . -B build-python -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON && cmake --build build-python"

build:
	mkdir -p build

build/libcorroventa_protocol.a: $(LIB_SRCS) | build
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c src/Crc16.cpp -o build/Crc16.o
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c src/FrameDecoder.cpp -o build/FrameDecoder.o
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c src/FrameEncoder.cpp -o build/FrameEncoder.o
	ar rcs $@ build/Crc16.o build/FrameDecoder.o build/FrameEncoder.o

build/corroventa_protocol_tests: $(TEST_SRCS) build/libcorroventa_protocol.a | build
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(FIXTURES) $(TEST_SRCS) build/libcorroventa_protocol.a -o $@

build/frame_decode: tools/frame_decode.cpp build/libcorroventa_protocol.a | build
	$(CXX) $(CXXFLAGS) $(INCLUDES) tools/frame_decode.cpp build/libcorroventa_protocol.a -o $@

build/frame_encode: tools/frame_encode.cpp build/libcorroventa_protocol.a | build
	$(CXX) $(CXXFLAGS) $(INCLUDES) tools/frame_encode.cpp build/libcorroventa_protocol.a -o $@

tools: build/frame_decode build/frame_encode

test: build/corroventa_protocol_tests
	./build/corroventa_protocol_tests

clean:
	rm -rf build
