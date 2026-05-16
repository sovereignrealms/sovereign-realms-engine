#!/usr/bin/env python3
#
# Validate Sovereign asset provenance and license records.
#

import argparse
import datetime
import json
import os
import sys


MANIFEST_REL_PATH = os.path.join("assets", "sovereign", "LICENSES", "manifest.json")
ASSET_ROOT_REL_PATH = os.path.join("assets", "sovereign")
REQUIRED_FIELDS = (
    "path",
    "name",
    "type",
    "author",
    "source",
    "created_or_intake_date",
    "license",
    "third_party_base",
)
EXCLUDED_FILENAMES = frozenset(("README.md",))
EXCLUDED_DIRS = frozenset((os.path.join("assets", "sovereign", "LICENSES"),))


def _repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _rel(path, basedir):
    return os.path.relpath(path, basedir).replace(os.sep, "/")


def _load_manifest(basedir, errors):
    manifest_path = os.path.join(basedir, MANIFEST_REL_PATH)
    if not os.path.exists(manifest_path):
        errors.append("{0} is missing".format(MANIFEST_REL_PATH))
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as infile:
            return json.load(infile)
    except ValueError as exc:
        errors.append("{0} is not valid JSON: {1}".format(MANIFEST_REL_PATH, exc))
        return {}


def _is_excluded(relpath):
    if relpath in ("assets/sovereign/README.md",):
        return True
    for dirname in EXCLUDED_DIRS:
        if relpath == dirname or relpath.startswith(dirname.replace(os.sep, "/") + "/"):
            return True
    return os.path.basename(relpath) in EXCLUDED_FILENAMES and relpath.count("/") <= 2


def _discover_asset_files(basedir):
    root = os.path.join(basedir, ASSET_ROOT_REL_PATH)
    files = []
    if not os.path.isdir(root):
        return files
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(dirnames)
        for filename in sorted(filenames):
            relpath = _rel(os.path.join(dirpath, filename), basedir)
            if not _is_excluded(relpath):
                files.append(relpath)
    return files


def _valid_date(value):
    try:
        datetime.datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def _validate_manifest(manifest, basedir):
    errors = []
    warnings = []

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("default_license") != "MIT":
        errors.append("manifest default_license must be MIT")

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        errors.append("manifest assets must be a list")
        assets = []

    seen = set()
    covered = set()
    for index, record in enumerate(assets):
        label = "assets[{0}]".format(index)
        if not isinstance(record, dict):
            errors.append("{0} must be an object".format(label))
            continue

        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            errors.append("{0} missing required field(s): {1}".format(label, ", ".join(missing)))
            continue

        relpath = record["path"]
        if not isinstance(relpath, str) or not relpath.startswith("assets/sovereign/"):
            errors.append("{0}.path must be under assets/sovereign/".format(label))
            continue
        if relpath in seen:
            errors.append("{0}.path duplicates {1}".format(label, relpath))
        seen.add(relpath)
        covered.add(relpath)

        if not os.path.exists(os.path.join(basedir, relpath)):
            errors.append("{0}.path does not exist: {1}".format(label, relpath))
        if relpath.startswith("assets/sovereign/LICENSES/"):
            errors.append("{0}.path should not point at license manifest files".format(label))

        for field in ("name", "type", "author", "source", "license"):
            if not isinstance(record[field], str) or not record[field].strip():
                errors.append("{0}.{1} must be a non-empty string".format(label, field))
        if record["license"] != "MIT":
            errors.append("{0}.license must be MIT for Sovereign-created assets".format(label))
        if not _valid_date(record["created_or_intake_date"]):
            errors.append("{0}.created_or_intake_date must use YYYY-MM-DD".format(label))
        if not isinstance(record["third_party_base"], bool):
            errors.append("{0}.third_party_base must be true or false".format(label))
        elif record["third_party_base"] and not str(record.get("third_party_notes", "")).strip():
            errors.append("{0}.third_party_notes is required when third_party_base is true".format(label))

    discovered = set(_discover_asset_files(basedir))
    missing_records = sorted(discovered - covered)
    stale_records = sorted(covered - discovered)
    for relpath in missing_records:
        errors.append("missing manifest record for {0}".format(relpath))
    for relpath in stale_records:
        warnings.append("manifest record points at non-discovered path {0}".format(relpath))

    return errors, warnings, len(discovered), len(covered)


def main():
    parser = argparse.ArgumentParser(description="Validate Sovereign asset license manifest.")
    parser.add_argument(
        "--basedir",
        default=_repo_root(),
        help="Repository root used to resolve asset paths.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures.",
    )
    args = parser.parse_args()

    basedir = os.path.abspath(args.basedir)
    errors = []
    manifest = _load_manifest(basedir, errors)
    warnings = []
    discovered = 0
    covered = 0
    if manifest:
        manifest_errors, warnings, discovered, covered = _validate_manifest(manifest, basedir)
        errors.extend(manifest_errors)

    for warning in warnings:
        print("SOVEREIGN_ASSET_LICENSE_WARNING {0}".format(warning), file=sys.stderr)
    for error in errors:
        print("SOVEREIGN_ASSET_LICENSE_ERROR {0}".format(error), file=sys.stderr)

    if errors or (args.strict and warnings):
        print(
            "SOVEREIGN_ASSET_LICENSE_INVALID discovered={0} manifest_records={1}".format(
                discovered, covered
            ),
            file=sys.stderr,
        )
        return 1

    print(
        "SOVEREIGN_ASSET_LICENSE_VALID discovered={0} manifest_records={1}".format(
            discovered, covered
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
