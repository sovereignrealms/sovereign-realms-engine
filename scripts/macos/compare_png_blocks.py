#!/usr/bin/env python3

import argparse
import struct
import sys
import zlib


def _paeth(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _chunks(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png")
    off = 8
    while off < len(data):
        length = struct.unpack(">I", data[off:off + 4])[0]
        kind = data[off + 4:off + 8]
        payload = data[off + 8:off + 8 + length]
        yield kind, payload
        off += 12 + length


def _read_png_rgb(path):
    with open(path, "rb") as infile:
        data = infile.read()

    width = height = bit_depth = color_type = None
    idat = []
    for kind, payload in _chunks(data):
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            idat.append(payload)

    if bit_depth != 8 or color_type not in (0, 2, 6):
        raise ValueError("unsupported png format bit_depth={0} color_type={1}".format(bit_depth, color_type))

    channels = {0: 1, 2: 3, 6: 4}[color_type]
    row_bytes = width * channels
    raw = zlib.decompress(b"".join(idat))
    prev = bytearray(row_bytes)
    offset = 0
    pixels = []

    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset:offset + row_bytes])
        offset += row_bytes
        for i in range(row_bytes):
            left = row[i - channels] if i >= channels else 0
            up = prev[i]
            up_left = prev[i - channels] if i >= channels else 0
            if filter_type == 1:
                row[i] = (row[i] + left) & 0xff
            elif filter_type == 2:
                row[i] = (row[i] + up) & 0xff
            elif filter_type == 3:
                row[i] = (row[i] + ((left + up) >> 1)) & 0xff
            elif filter_type == 4:
                row[i] = (row[i] + _paeth(left, up, up_left)) & 0xff
            elif filter_type != 0:
                raise ValueError("unsupported png filter {0}".format(filter_type))

        rgb_row = []
        for px in range(width):
            base = px * channels
            if color_type == 0:
                rgb_row.append((row[base], row[base], row[base]))
            else:
                rgb_row.append((row[base], row[base + 1], row[base + 2]))
        pixels.append(rgb_row)
        prev = row

    return width, height, pixels


def _block_average(pixels, width, height, x, y, half):
    x0 = max(0, x - half)
    x1 = min(width - 1, x + half)
    y0 = max(0, y - half)
    y1 = min(height - 1, y + half)
    total = [0, 0, 0]
    count = 0
    for yy in range(y0, y1 + 1):
        row = pixels[yy]
        for xx in range(x0, x1 + 1):
            r, g, b = row[xx]
            total[0] += r
            total[1] += g
            total[2] += b
            count += 1
    return tuple(float(v) / count for v in total)


def _parse_point(value):
    x, y = value.split(",", 1)
    return int(x), int(y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_png")
    parser.add_argument("candidate_png")
    parser.add_argument("half", type=int)
    parser.add_argument("points", nargs="+")
    args = parser.parse_args()

    ref_w, ref_h, ref_pixels = _read_png_rgb(args.reference_png)
    cand_w, cand_h, cand_pixels = _read_png_rgb(args.candidate_png)
    if (ref_w, ref_h) != (cand_w, cand_h):
        raise ValueError("image size mismatch: {0}x{1} vs {2}x{3}".format(ref_w, ref_h, cand_w, cand_h))

    for token in args.points:
        x, y = _parse_point(token)
        ref = _block_average(ref_pixels, ref_w, ref_h, x, y, args.half)
        cand = _block_average(cand_pixels, cand_w, cand_h, x, y, args.half)
        ratio = tuple(cand[i] / ref[i] if ref[i] else 0.0 for i in range(3))
        print(
            "{0},{1} ref={2:.2f},{3:.2f},{4:.2f} cand={5:.2f},{6:.2f},{7:.2f} ratio={8:.2f},{9:.2f},{10:.2f}".format(
                x, y,
                ref[0], ref[1], ref[2],
                cand[0], cand[1], cand[2],
                ratio[0], ratio[1], ratio[2],
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
