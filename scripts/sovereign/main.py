#
#  Sovereign Realms game package scaffold.
#
#  This package is intentionally separate from scripts/rts so the production
#  game can grow without rewriting the Permafrost demo scripts.
#

import os
import sys


def main():
    print(
        "SOVEREIGN_SCAFFOLD_READY "
        "The Sovereign Realms package exists, but the playable vertical slice "
        "has not been implemented yet. Run scripts/rts/main.py for the current "
        "Permafrost demo."
    )
    sys.stdout.flush()
    if os.environ.get("PF_SOVEREIGN_SCAFFOLD_AUTOQUIT", "1") == "1":
        os._exit(0)


main()
