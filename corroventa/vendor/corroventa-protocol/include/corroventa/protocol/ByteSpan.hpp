#pragma once

#include <cstddef>
#include <cstdint>

namespace corroventa::protocol {

/// Non-owning view of bytes (C++17 stand-in for std::span).
class ByteSpan {
 public:
  constexpr ByteSpan() noexcept = default;
  constexpr ByteSpan(const std::uint8_t* data, std::size_t size) noexcept
      : data_(data), size_(size) {}

  template <std::size_t N>
  constexpr ByteSpan(const std::uint8_t (&arr)[N]) noexcept : data_(arr), size_(N) {}

  constexpr const std::uint8_t* data() const noexcept { return data_; }
  constexpr std::size_t size() const noexcept { return size_; }
  constexpr bool empty() const noexcept { return size_ == 0; }

  constexpr const std::uint8_t& operator[](std::size_t i) const noexcept { return data_[i]; }

  constexpr ByteSpan subspan(std::size_t offset, std::size_t count) const noexcept {
    return ByteSpan(data_ + offset, count);
  }

  constexpr ByteSpan subspan(std::size_t offset) const noexcept {
    return ByteSpan(data_ + offset, size_ - offset);
  }

  const std::uint8_t* begin() const noexcept { return data_; }
  const std::uint8_t* end() const noexcept { return data_ + size_; }

 private:
  const std::uint8_t* data_ = nullptr;
  std::size_t size_ = 0;
};

}  // namespace corroventa::protocol
