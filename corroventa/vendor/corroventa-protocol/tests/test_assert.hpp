#pragma once

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

namespace corroventa::protocol::test {

inline int g_failures = 0;

inline void expect(bool cond, const char* expr, const char* file, int line) {
  if (!cond) {
    std::cerr << "FAIL " << file << ":" << line << "  " << expr << "\n";
    ++g_failures;
  }
}

inline void expectNear(float a, float b, float eps, const char* file, int line) {
  if (std::fabs(a - b) > eps) {
    std::cerr << "FAIL " << file << ":" << line << "  " << a << " !~ " << b << "\n";
    ++g_failures;
  }
}

}  // namespace corroventa::protocol::test

#define EXPECT(cond) \
  ::corroventa::protocol::test::expect(static_cast<bool>(cond), #cond, __FILE__, __LINE__)

#define EXPECT_NEAR(a, b, eps) \
  ::corroventa::protocol::test::expectNear((a), (b), (eps), __FILE__, __LINE__)
