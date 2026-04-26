import os
import sys

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import rts.main as demo_main


os.environ["PF_NATIVE_LAUNCH_PROBE"] = "1"
os.environ["PF_NATIVE_LAUNCH_PROBE_AUTOQUIT"] = "1"
os.environ["PF_NATIVE_LAUNCH_PROBE_PATH"] = "/tmp/pf_metal_launch_probe.txt"
os.environ["PF_NATIVE_LAUNCH_PROBE_QUIT_AFTER"] = "45"


demo_main.main()
