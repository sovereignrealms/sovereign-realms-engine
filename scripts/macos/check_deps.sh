#!/bin/zsh

set -euo pipefail

plat="${1:-MACOS_X86_64}"

if [[ "$plat" != "MACOS_X86_64" && "$plat" != "MACOS_ARM64" ]]; then
  echo "Unsupported macOS platform: $plat" >&2
  exit 1
fi

missing=0

check_cmd() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf "[OK]   %s\n" "$label"
  else
    printf "[MISS] %s\n" "$label"
    missing=1
  fi
}

check_pkg() {
  local label="$1"
  shift
  if "$@" --exists "$label" >/dev/null 2>&1; then
    printf "[OK]   pkg-config %s\n" "$label"
  else
    printf "[MISS] pkg-config %s\n" "$label"
    missing=1
  fi
}

check_any_cmd() {
  local label="$1"
  shift
  local cmd
  for cmd in "$@"; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf "[OK]   %s -> %s\n" "$label" "$cmd"
      return 0
    fi
  done
  printf "[MISS] %s\n" "$label"
  missing=1
}

if [[ "$plat" == "MACOS_X86_64" ]]; then
  prefix="${HOMEBREW_X86_64_PREFIX:-/usr/local}"
  arch_prefix=(/usr/bin/arch -x86_64)
  brew_bin="$prefix/bin/brew"
  pkg_libdir="$prefix/lib/pkgconfig:$prefix/share/pkgconfig:$prefix/opt/openal-soft/lib/pkgconfig"
  pkg_cmd=(env "PKG_CONFIG_LIBDIR=$pkg_libdir" pkg-config)
  python_label="Python 2.7 config"
  python_candidates=(python2.7-config python2-config)
else
  prefix="${HOMEBREW_ARM64_PREFIX:-/opt/homebrew}"
  arch_prefix=()
  brew_bin="$prefix/bin/brew"
  pkg_libdir="$prefix/lib/pkgconfig:$prefix/share/pkgconfig:$prefix/opt/openal-soft/lib/pkgconfig"
  pkg_cmd=(env "PKG_CONFIG_LIBDIR=$pkg_libdir" pkg-config)
  python_label="Python 3.13 config"
  python_candidates=(python3.13-config python3-config)
fi

check_cmd "clang for $plat" "${arch_prefix[@]}" /usr/bin/clang --version
check_cmd "cmake" command -v cmake
check_cmd "Homebrew at $brew_bin" test -x "$brew_bin"
check_cmd "pkg-config" "${pkg_cmd[@]}" --version

check_pkg sdl2 "${pkg_cmd[@]}"
check_pkg openal "${pkg_cmd[@]}"
check_pkg mimalloc "${pkg_cmd[@]}"

check_any_cmd "$python_label" "${python_candidates[@]}"

if [[ $missing -ne 0 ]]; then
  echo
  if [[ "$plat" == "MACOS_X86_64" ]]; then
    echo "Expected x86_64 host libraries under $prefix and a shared Python 2.7 toolchain."
  else
    echo "Expected native arm64 host libraries under $prefix and a shared Python 3.13 toolchain."
  fi
  exit 1
fi
