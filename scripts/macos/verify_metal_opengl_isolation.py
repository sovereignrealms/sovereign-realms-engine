#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run(cmd):
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=30,
    )


def _fail(message):
    print("METAL_OPENGL_ISOLATION_FAIL {0}".format(message), file=sys.stderr)
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--binary",
        default=str(ROOT / "bin/pf-arm64"),
        help="Metal runtime binary to inspect.",
    )
    args = parser.parse_args()

    binary = Path(args.binary)
    if not binary.exists():
        return _fail("missing_binary path={0}".format(binary))

    otool = _run(["/usr/bin/otool", "-L", str(binary)])
    if otool.returncode != 0:
        return _fail("otool_failed stderr={0}".format(otool.stderr.strip()))
    if "OpenGL.framework" in otool.stdout:
        return _fail("linked_opengl_framework")

    nm = _run(["/usr/bin/nm", "-g", str(binary)])
    if nm.returncode != 0:
        return _fail("nm_failed stderr={0}".format(nm.stderr.strip()))

    symbol_re = re.compile(r"(_pf_gl[A-Za-z0-9_]*|_gl[A-Z][A-Za-z0-9_]*)\b")
    matches = []
    for line in nm.stdout.splitlines():
        match = symbol_re.search(line)
        if match:
            matches.append(line.strip())

    if matches:
        preview = ";".join(matches[:8])
        return _fail("live_gl_symbols count={0} symbols={1}".format(len(matches), preview))

    print("METAL_OPENGL_ISOLATION_PASS binary={0}".format(binary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
