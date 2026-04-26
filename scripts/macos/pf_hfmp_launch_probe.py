import os
import sys

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import hfmp_s2.main as game_main


PROBE_PATH = "/tmp/pf_hfmp_launch_probe.txt"


def finish(marker):
    print(marker)
    with open(PROBE_PATH, "w") as probe_file:
        probe_file.write(marker + "\n")
    sys.stdout.flush()
    os._exit(0)


def on_update(user, event):
    del user
    del event
    finish("HFMP_LAUNCH_READY factions={0}".format(",".join(fac["name"] for fac in pf.get_factions_list())))


game_main.main()
pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)
