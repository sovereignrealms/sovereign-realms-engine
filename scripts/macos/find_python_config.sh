#!/bin/zsh

set -euo pipefail

plat="${1:-MACOS_X86_64}"

if [[ "$plat" == "MACOS_X86_64" ]]; then
  prefix="${HOMEBREW_X86_64_PREFIX:-/usr/local}"
  candidates=(
    python2.7-config
    python2-config
    "$prefix/bin/python2.7-config"
    "$prefix/bin/python2-config"
    "$HOME/.pyenv/shims/python2.7-config"
    "$HOME/.pyenv/shims/python2-config"
  )
else
  prefix="${HOMEBREW_ARM64_PREFIX:-/opt/homebrew}"
  candidates=(
    python3.13-config
    python3-config
    "$prefix/bin/python3.13-config"
    "$prefix/bin/python3-config"
    "$HOME/.pyenv/shims/python3.13-config"
    "$HOME/.pyenv/shims/python3-config"
  )
fi

for candidate in "${candidates[@]}"; do
  if [[ "$candidate" == /* ]]; then
    if [[ -x "$candidate" ]]; then
      printf "%s\n" "$candidate"
      exit 0
    fi
  elif command -v "$candidate" >/dev/null 2>&1; then
    command -v "$candidate"
    exit 0
  fi
done

exit 0
