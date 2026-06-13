# CLAUDE.md

Guidance for AI assistants (Claude Code) working in this repository.

## What this project is

**`gulrak/filesystem`** (CMake project name `ghcfilesystem`, current version
**1.5.15**) is a **header-only, single-file `std::filesystem`-compatible**
library. It implements the C++17 (and, when compiled as C++20, C++20) filesystem
API for compilers that only have **C++11/C++14**, while staying usable as a
drop-in on C++17/C++20 too.

- Everything lives under the namespace **`ghc::filesystem`** (so it never clashes
  with `std::filesystem` in a mixed environment). `ghc` = "gulrak's helper
  classes" — nothing to do with Haskell.
- It follows the **"UTF-8 Everywhere"** philosophy: all `std::string` are treated
  as UTF-8; `std::u16string` as UTF-16. This is the main intentional deviation
  from `std::filesystem`. See README "Differences in API".
- The entire implementation is in **`include/ghc/filesystem.hpp`** (~6000 lines).
  The other headers in `include/ghc/` are thin selection wrappers (see below).
- License: MIT (`LICENSE`). Author: Steffen Schümann.

This is a **library**, not an application. There is no app to run — the build
produces tests and small example binaries.

## Repository layout

```
include/ghc/             # the library (header-only)
  filesystem.hpp         # the actual implementation + the ghc::filesystem API
  fs_fwd.hpp             # forwarding header (declares GHC_FILESYSTEM_FWD)
  fs_impl.hpp            # implementation header (defines GHC_FILESYSTEM_IMPLEMENTATION)
  fs_std.hpp             # picks std::filesystem if available, else ghc; exposes namespace `fs`
  fs_std_fwd.hpp         # fwd variant of fs_std (declaration only)
  fs_std_impl.hpp        # impl variant of fs_std (no-op when std::filesystem is used)
test/                    # Catch2-based unit tests (catch.hpp vendored)
  filesystem_test.cpp    # the main test suite
  multi1.cpp/multi2.cpp  # multi-TU linkage test (fwd + impl across two files)
  fwd_test.cpp/impl_test.cpp  # fwd/impl split linkage test
  exception.cpp          # builds with -fno-exceptions
  cmake/ParseAndAddCatchTests.cmake
examples/                # dir.cpp (ls-like), du.cpp (disk-usage); optional benchmark.cpp
cmake/                   # GhcHelper.cmake (std-fs test helpers), config.cmake.in
.github/workflows/build_cmake.yml   # primary CI
.appveyor.yml / .cirrus.yml         # additional CI (Windows / FreeBSD etc.)
.ci/                     # unix-build.sh, unix-test.sh helper scripts
README.md                # extensive docs: usage, differences, release notes
```

## Choosing how to include the library

There are three usage modes — pick headers accordingly:

1. **Single-file header-only** (simplest): `#include <ghc/filesystem.hpp>`, use
   `namespace fs = ghc::filesystem;`. The implementation is emitted inline.
2. **Forwarding / implementation split** (avoid leaking system headers / faster
   builds): include `fs_fwd.hpp` everywhere; in exactly **one** `.cpp`, include
   `fs_impl.hpp` (or `#define GHC_FILESYSTEM_IMPLEMENTATION` before
   `filesystem.hpp`) to emit the implementation once.
3. **`std::filesystem` auto-switch**: include `fs_std.hpp` (or the
   `fs_std_fwd.hpp` + `fs_std_impl.hpp` split). It uses real `std::filesystem`
   when the compiler provides it (C++17 with `<filesystem>`, modern Apple OSes),
   otherwise falls back to `ghc::filesystem`. Either way the API is in
   namespace **`fs`**.

## Build (CMake)

The library target is an `INTERFACE` (header-only) library:
**`ghc_filesystem`**, aliased as **`ghcFilesystem::ghc_filesystem`**.

```bash
cmake -G Ninja -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Requires **CMake 3.7.2+**. Default `CMAKE_CXX_STANDARD` is **11** (configurable);
the project hard-errors if it is set below 11.

### CMake options (from top-level `CMakeLists.txt`)

When this is the top-level project, all default **ON**; as a subdirectory they
default **OFF**:

| Option | Default (top-level) | Effect |
|--------|--------------------|--------|
| `GHC_FILESYSTEM_BUILD_TESTING` | ON | build the test suite, `enable_testing()` |
| `GHC_FILESYSTEM_BUILD_EXAMPLES` | ON | build `examples/` |
| `GHC_FILESYSTEM_WITH_INSTALL` | ON | provide the install + CMake package export |
| `GHC_FILESYSTEM_BUILD_STD_TESTING` | = BUILD_TESTING | also build a `std::filesystem`-backed test binary |

Other recognized cache variables:

- `GHC_FILESYSTEM_TEST_COMPILE_FEATURES` — semicolon list like
  `"cxx_std_11;cxx_std_17;cxx_std_20"`; for each `cxx_std_NN` present, an extra
  `filesystem_test_cppNN` target is built and tested. Defaults to the compiler's
  detected features.
- `GHC_COVERAGE` — `ON` builds the test runner with `--coverage` (used by the CI
  coverage job).

### Consuming from another CMake project

As a git submodule / `add_subdirectory`, or via `find_package`, link the target:

```cmake
target_link_libraries(your_target PRIVATE ghcFilesystem::ghc_filesystem)
```

## Tests

Tests use **Catch2** (single-header `test/catch.hpp`, vendored). Individual
`TEST_CASE`s are registered with CTest via `ParseAndAddCatchTests`.

```bash
cd build
ctest --output-on-failure
# or run a binary directly:
./test/filesystem_test
```

Key test targets: `filesystem_test` (ghc backend), `std_filesystem_test` (real
`std::filesystem`, when `GHC_FILESYSTEM_BUILD_STD_TESTING`), `multifile_test`,
`fwd_impl_test`, `exception` (built `-fno-exceptions`), and on Windows
`filesystem_test_char`. The `.ci/unix-test.sh` helper runs `ctest -E Windows`.

Tests are compiled with **`-Werror`** plus `-Wall -Wextra -Wshadow -Wconversion
-Wsign-conversion -Wpedantic` (GCC/Clang) / `/WX` (MSVC) — keep changes
warning-clean across all those flags.

## Conventions, configuration macros & gotchas

- **Header-only**: there are no `.cpp` sources for the library itself. All API
  changes go into `include/ghc/filesystem.hpp`.
- **C++ standard / namespace**: minimum C++11; API in `ghc::filesystem`, with the
  `fs_std*` headers exposing it (or `std`) as `fs`.
- **Version macro**: `GHC_FILESYSTEM_VERSION` (currently `10515L`) must track the
  `project(... VERSION ...)` in `CMakeLists.txt`. Bump both together.
- **Compile-time feature/config macros** (all defined in `filesystem.hpp`, mostly
  auto-detected — override by defining before include):
  - `GHC_FILESYSTEM_IMPLEMENTATION` / `GHC_FILESYSTEM_FWD` — pick impl vs fwd mode.
  - `GHC_OS_*` — auto-detected platform (Windows/Linux/Apple/BSD/Solaris/Cygwin/
    Web/QNX/Haiku/Android).
  - `GHC_WIN_DISABLE_WSTRING_STORAGE_TYPE` — use `std::string`/`char` backend on
    Windows (pre-1.5 behavior) instead of the default `std::wstring` backend.
  - `GHC_RAISE_UNICODE_ERRORS` — throw on invalid Unicode instead of replacing
    (requires exceptions enabled).
  - `GHC_FILESYSTEM_ENFORCE_CPP17_API` — keep C++17 return types under C++20
    (e.g. `u8string()` returns `std::string`, not `std::u8string`).
  - `GHC_WIN_DISABLE_AUTO_PREFIXES` — disable automatic `\\?\` long-path prefixing.
  - `LWG_2682_BEHAVIOUR`, `LWG_2936_BEHAVIOUR`, `LWG_2937_BEHAVIOUR` (on) and
    `LWG_2935_BEHAVIOUR` (off) — toggle specific LWG defect resolutions.
- **Extras beyond `std::filesystem`**: `ghc::filesystem::ifstream/ofstream/
  fstream` (UTF-8 path-aware streams) and `ghc::filesystem::u8arguments` (RAII
  helper to get UTF-8 `argv` on Windows). See README "Documentation".
- **Code style**: `.clang-format` (Chromium base, 4-space indent, 256 col, custom
  brace wrapping). `.clang-tidy` disables `modernize-use-nodiscard`.
- **Repo is LF/UTF-8.** Build dirs (`*build*`) are gitignored.
- The single-file/multi-mode design means **the same header is included many
  ways** — when editing `filesystem.hpp`, keep the `GHC_EXPAND_IMPL` /
  `GHC_INLINE` / `GHC_FS_API` guards intact so all three usage modes still link
  (the `multifile_test` / `fwd_impl_test` targets exist to catch ODR/linkage
  regressions).

## CI

- **`.github/workflows/build_cmake.yml`** (primary): a matrix building with Ninja
  on Ubuntu 22.04/24.04 (GCC 11–13, Clang 15/18), Windows MSVC 2019/2022, Windows
  MSYS2 (mingw64/ucrt64/clang64), and macOS 14/15 (AppleClang ARM). Each configures
  with `GHC_FILESYSTEM_TEST_COMPILE_FEATURES="cxx_std_11;cxx_std_17;cxx_std_20"`,
  builds, then runs `ctest`. A Debug GCC 11 job sets `GHC_COVERAGE=ON` and uploads
  to Coveralls. A `legacy-compilers` job tests GCC 5–8 and Clang 6–9 in Docker
  (these are the documented minimum supported compilers).
- **`.appveyor.yml`** and **`.cirrus.yml`** add further (Windows / FreeBSD-style)
  coverage. `.drone.yml-disabled` is intentionally disabled.

There is no separate lint step; "tests pass" means a clean warning-free build and
a green `ctest` run across the configured C++ standards.
