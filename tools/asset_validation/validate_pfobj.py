#!/usr/bin/env python3
#
#  Lightweight PFOBJ validation for Sovereign Realms asset intake.
#

import argparse
import os
import sys


class PfobjError(Exception):
    pass


def _split(line, lineno, prefix):
    parts = line.strip().split()
    if not parts or parts[0] != prefix:
        raise PfobjError("line {0}: expected '{1}'".format(lineno, prefix))
    return parts


def _parse_int(value, lineno, name):
    try:
        return int(value)
    except ValueError:
        raise PfobjError("line {0}: invalid {1}: {2}".format(lineno, name, value))


def _parse_float(value, lineno, name):
    try:
        return float(value)
    except ValueError:
        raise PfobjError("line {0}: invalid {1}: {2}".format(lineno, name, value))


def _read_lines(path):
    with open(path, "r") as source:
        return source.readlines()


def _expect_parts(parts, count, lineno):
    if len(parts) != count:
        raise PfobjError(
            "line {0}: expected {1} fields, got {2}".format(lineno, count, len(parts))
        )


def _validate_weights(parts, lineno, num_joints, warnings):
    if len(parts) == 1:
        return
    if len(parts) > 5:
        warnings.append("line {0}: more than 4 skin weights".format(lineno))
    total = 0.0
    for token in parts[1:]:
        if "/" not in token:
            raise PfobjError("line {0}: malformed weight token".format(lineno))
        joint_text, weight_text = token.split("/", 1)
        joint = _parse_int(joint_text, lineno, "joint index")
        weight = _parse_float(weight_text, lineno, "skin weight")
        if joint < 0 or joint >= num_joints:
            raise PfobjError("line {0}: joint index out of range".format(lineno))
        if weight < 0.0:
            raise PfobjError("line {0}: negative skin weight".format(lineno))
        total += weight
    if total <= 0.0:
        warnings.append("line {0}: non-empty weights sum to zero".format(lineno))
    elif abs(total - 1.0) > 0.02:
        warnings.append("line {0}: skin weights sum to {1:.4f}".format(lineno, total))


def _validate_slash_tuple(value, lineno, name, count):
    parts = value.split("/")
    if len(parts) != count:
        raise PfobjError("line {0}: malformed {1}".format(lineno, name))
    for part in parts:
        _parse_float(part, lineno, name)


def _validate_bounds(parts, lineno, prefix):
    if len(parts) != 3 or parts[0] != prefix:
        raise PfobjError("line {0}: expected {1} bounds".format(lineno, prefix))
    low = _parse_float(parts[1], lineno, prefix)
    high = _parse_float(parts[2], lineno, prefix)
    if low > high:
        raise PfobjError("line {0}: {1} min is greater than max".format(lineno, prefix))


def validate_pfobj(path):
    lines = _read_lines(path)
    warnings = []
    idx = 0

    def next_line():
        nonlocal idx
        if idx >= len(lines):
            raise PfobjError("unexpected end of file")
        lineno = idx + 1
        line = lines[idx]
        idx += 1
        return lineno, line

    lineno, line = next_line()
    parts = _split(line, lineno, "version")
    _expect_parts(parts, 2, lineno)
    version = _parse_float(parts[1], lineno, "version")

    lineno, line = next_line()
    parts = _split(line, lineno, "num_verts")
    _expect_parts(parts, 2, lineno)
    num_verts = _parse_int(parts[1], lineno, "num_verts")

    lineno, line = next_line()
    parts = _split(line, lineno, "num_joints")
    _expect_parts(parts, 2, lineno)
    num_joints = _parse_int(parts[1], lineno, "num_joints")

    lineno, line = next_line()
    parts = _split(line, lineno, "num_materials")
    _expect_parts(parts, 2, lineno)
    num_materials = _parse_int(parts[1], lineno, "num_materials")

    lineno, line = next_line()
    parts = _split(line, lineno, "num_as")
    _expect_parts(parts, 2, lineno)
    num_anim_sets = _parse_int(parts[1], lineno, "num_as")

    lineno, line = next_line()
    parts = _split(line, lineno, "frame_counts")
    frame_counts = [_parse_int(part, lineno, "frame count") for part in parts[1:]]
    if len(frame_counts) != num_anim_sets:
        raise PfobjError(
            "line {0}: frame_counts has {1} entries for {2} animation sets".format(
                lineno, len(frame_counts), num_anim_sets
            )
        )

    lineno, line = next_line()
    parts = _split(line, lineno, "has_collision")
    _expect_parts(parts, 2, lineno)
    has_collision = _parse_int(parts[1], lineno, "has_collision")
    if has_collision not in (0, 1):
        raise PfobjError("line {0}: has_collision must be 0 or 1".format(lineno))

    if num_verts <= 0:
        raise PfobjError("num_verts must be positive")
    if num_materials <= 0:
        raise PfobjError("num_materials must be positive")

    for _ in range(num_verts):
        lineno, line = next_line()
        parts = _split(line, lineno, "v")
        _expect_parts(parts, 4, lineno)
        for axis in parts[1:]:
            _parse_float(axis, lineno, "vertex coordinate")

        lineno, line = next_line()
        parts = _split(line, lineno, "vt")
        _expect_parts(parts, 3, lineno)
        for coord in parts[1:]:
            _parse_float(coord, lineno, "texture coordinate")

        lineno, line = next_line()
        parts = _split(line, lineno, "vn")
        _expect_parts(parts, 4, lineno)
        for axis in parts[1:]:
            _parse_float(axis, lineno, "normal coordinate")

        lineno, line = next_line()
        parts = _split(line, lineno, "vw")
        _validate_weights(parts, lineno, num_joints, warnings)

        lineno, line = next_line()
        parts = _split(line, lineno, "vm")
        _expect_parts(parts, 2, lineno)
        material = _parse_int(parts[1], lineno, "material index")
        if material < 0 or material >= num_materials:
            raise PfobjError("line {0}: material index out of range".format(lineno))

    textures = []
    for _ in range(num_materials):
        lineno, line = next_line()
        parts = _split(line, lineno, "material")
        if len(parts) < 2:
            raise PfobjError("line {0}: material name is missing".format(lineno))

        lineno, line = next_line()
        parts = _split(line, lineno, "ambient")
        _expect_parts(parts, 2, lineno)
        _parse_float(parts[1], lineno, "ambient")

        lineno, line = next_line()
        parts = _split(line, lineno, "diffuse")
        _expect_parts(parts, 4, lineno)
        for channel in parts[1:]:
            _parse_float(channel, lineno, "diffuse channel")

        lineno, line = next_line()
        parts = _split(line, lineno, "specular")
        _expect_parts(parts, 4, lineno)
        for channel in parts[1:]:
            _parse_float(channel, lineno, "specular channel")

        lineno, line = next_line()
        parts = _split(line, lineno, "texture")
        if len(parts) != 2:
            raise PfobjError("line {0}: expected one texture filename".format(lineno))
        textures.append(parts[1])

    base_dir = os.path.dirname(path)
    for texture in textures:
        texture_path = os.path.join(base_dir, texture)
        if not os.path.isfile(texture_path):
            raise PfobjError("missing texture: {0}".format(texture_path))

    for _ in range(num_joints):
        lineno, line = next_line()
        parts = _split(line, lineno, "j")
        if len(parts) < 6:
            raise PfobjError("line {0}: malformed joint".format(lineno))

    for anim_index in range(num_anim_sets):
        lineno, line = next_line()
        parts = _split(line, lineno, "as")
        if len(parts) < 3:
            raise PfobjError("line {0}: malformed animation set".format(lineno))
        frame_count = _parse_int(parts[-1], lineno, "animation frame count")
        if frame_count != frame_counts[anim_index]:
            raise PfobjError(
                "line {0}: animation frame count {1} does not match header {2}".format(
                    lineno, frame_count, frame_counts[anim_index]
                )
            )
        for _ in range(frame_count):
            for _ in range(num_joints):
                lineno, line = next_line()
                parts = line.strip().split()
                if len(parts) != 4:
                    raise PfobjError("line {0}: malformed joint frame".format(lineno))
                joint = _parse_int(parts[0], lineno, "animation joint index")
                if joint < 1 or joint > num_joints:
                    raise PfobjError("line {0}: animation joint out of range".format(lineno))
                _validate_slash_tuple(parts[1], lineno, "animation scale", 3)
                _validate_slash_tuple(parts[2], lineno, "animation rotation", 4)
                _validate_slash_tuple(parts[3], lineno, "animation translation", 3)
            if has_collision:
                for prefix in ("x_bounds", "y_bounds", "z_bounds"):
                    lineno, line = next_line()
                    _validate_bounds(line.strip().split(), lineno, prefix)

    if has_collision:
        for prefix in ("x_bounds", "y_bounds", "z_bounds"):
            lineno, line = next_line()
            _validate_bounds(line.strip().split(), lineno, prefix)

    trailing = [line for line in lines[idx:] if line.strip()]
    if trailing:
        warnings.append("file has {0} non-empty trailing lines".format(len(trailing)))

    return {
        "version": version,
        "vertices": num_verts,
        "materials": num_materials,
        "joints": num_joints,
        "animation_sets": num_anim_sets,
        "has_collision": bool(has_collision),
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate a Permafrost PFOBJ asset.")
    parser.add_argument("pfobj", help="Path to the .pfobj file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings such as non-normalized skin weights as failures",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every warning instead of a short summary",
    )
    args = parser.parse_args()

    try:
        result = validate_pfobj(args.pfobj)
    except (IOError, PfobjError) as exc:
        print("PFOBJ_INVALID {0}: {1}".format(args.pfobj, exc), file=sys.stderr)
        return 1

    warnings = result["warnings"]
    warning_limit = len(warnings) if args.verbose else min(len(warnings), 20)
    for warning in warnings[:warning_limit]:
        print("PFOBJ_WARNING {0}: {1}".format(args.pfobj, warning), file=sys.stderr)
    if warnings and not args.verbose and len(warnings) > warning_limit:
        print(
            "PFOBJ_WARNING {0}: {1} additional warnings hidden; rerun with --verbose".format(
                args.pfobj, len(warnings) - warning_limit
            ),
            file=sys.stderr,
        )
    if args.strict and warnings:
        print("PFOBJ_INVALID {0}: strict warnings present".format(args.pfobj), file=sys.stderr)
        return 1

    print(
        "PFOBJ_VALID {path} version={version:.1f} vertices={vertices} materials={materials} "
        "joints={joints} animations={animation_sets} collision={collision}".format(
            path=args.pfobj,
            version=result["version"],
            vertices=result["vertices"],
            materials=result["materials"],
            joints=result["joints"],
            animation_sets=result["animation_sets"],
            collision=int(result["has_collision"]),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
