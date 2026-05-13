#!/usr/bin/env python3
#
# Validate Sovereign unit readability metadata for team-color and far-view rules.
#

import argparse
import os
import sys


def _repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    parser = argparse.ArgumentParser(description="Validate Sovereign unit readability metadata.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat pending production masks as failures.",
    )
    parser.add_argument(
        "--basedir",
        default=_repo_root(),
        help="Repository root used to resolve asset paths.",
    )
    args = parser.parse_args()

    sys.path.insert(0, os.path.join(args.basedir, "scripts"))
    from sovereign.data.readability import summarize_unit_readability

    summary = summarize_unit_readability(basedir=args.basedir)
    for warning in summary["warnings"]:
        print("SOVEREIGN_READABILITY_WARNING {0}".format(warning), file=sys.stderr)
    for error in summary["errors"]:
        print("SOVEREIGN_READABILITY_ERROR {0}".format(error), file=sys.stderr)

    if summary["errors"] or (args.strict and summary["warnings"]):
        print(
            "SOVEREIGN_READABILITY_INVALID units={0} pending_team_masks={1}".format(
                len(summary["units"]), summary["pending_team_masks"]
            ),
            file=sys.stderr,
        )
        return 1

    print(
        "SOVEREIGN_READABILITY_VALID units={0} production_ready={1} pending_team_masks={2}".format(
            len(summary["units"]),
            summary["production_ready_units"],
            summary["pending_team_masks"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
