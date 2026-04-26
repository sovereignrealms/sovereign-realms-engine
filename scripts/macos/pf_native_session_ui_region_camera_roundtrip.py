import os
import sys

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import common.constants
import rts.constants
import rts.globals
import rts.main as demo_main


SAVE_PATH = "tmp_native_session_ui_region_camera_roundtrip.pfsave"
PROBE_PATH = "/tmp/pf_native_session_ui_region_camera_probe.txt"
ERROR_PATH = "/tmp/pf_native_session_ui_region_camera_error.txt"

os.environ["PF_NATIVE_SESSION_PROBE"] = "1"
os.environ["PF_NATIVE_SESSION_PROBE_VERBOSE"] = "1"
os.environ["PF_NATIVE_SESSION_PROBE_PATH"] = PROBE_PATH
os.environ["PF_NATIVE_SESSION_PROBE_AUTOQUIT"] = "1"

STATE = {
    "created": False,
    "phase": "show_save",
    "ticks": 0,
}


def fail(reason):
    with open(ERROR_PATH, "w") as errfile:
        errfile.write(str(reason) + "\n")
    pf.global_event(pf.SDL_QUIT, None)


def ensure_scene_metadata():
    if STATE["created"]:
        return

    region = pf.Region(
        type=pf.REGION_RECTANGLE,
        name="native_ui_session_probe_region",
        position=(24.0, -24.0),
        dimensions=(18.0, 12.0),
    )
    camera = pf.Camera(
        name="native_ui_session_probe_camera",
        mode=pf.CAM_MODE_FREE,
        position=(48.0, 175.0, -48.0),
        pitch=-60.0,
        yaw=120.0,
    )

    rts.globals.scene_regions = [region]
    rts.globals.scene_cameras = [camera]
    STATE["created"] = True


def on_update(user, event):
    del user
    del event
    ensure_scene_metadata()
    STATE["ticks"] += 1

    if STATE["phase"] == "show_save":
        pf.global_event(rts.constants.EVENT_SESSION_SHOW, None)
        STATE["phase"] = "wait_save"
        STATE["ticks"] = 0
        return

    if STATE["phase"] == "wait_save" and STATE["ticks"] >= 45:
        pf.global_event(common.constants.EVENT_SESSION_SAVE_REQUESTED, SAVE_PATH)
        STATE["phase"] = "saving"
        return

    if STATE["phase"] == "show_load":
        pf.global_event(rts.constants.EVENT_SESSION_SHOW, None)
        STATE["phase"] = "wait_load"
        STATE["ticks"] = 0
        return

    if STATE["phase"] == "wait_load" and STATE["ticks"] >= 45:
        pf.global_event(common.constants.EVENT_SESSION_LOAD_REQUESTED, SAVE_PATH)
        STATE["phase"] = "loading"
        return

    if STATE["ticks"] >= 900:
        fail("Timed out waiting for Session UI region/camera roundtrip to finish")


def on_saved(user, event):
    del user
    del event
    STATE["phase"] = "show_load"
    STATE["ticks"] = 0


def on_save_fail(user, event):
    del user
    fail("SESSION_SAVE_FAIL={0}".format(event))


def on_load_fail(user, event):
    del user
    fail("SESSION_LOAD_FAIL={0}".format(event))


demo_main.main()

pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)
pf.register_ui_event_handler(pf.EVENT_SESSION_SAVED, on_saved, None)
pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_SAVE, on_save_fail, None)
pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_LOAD, on_load_fail, None)
