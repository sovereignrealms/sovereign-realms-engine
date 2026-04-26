import json
import os
import sys

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import common.constants
import rts.main as demo_main


ORIGINAL_PATH = "/tmp/pf_native_settings_original.json"
PROBE_PATH = "/tmp/pf_native_settings_apply_probe.txt"
ERROR_PATH = "/tmp/pf_native_settings_apply_error.txt"

STATE = {
    "phase": "apply_video",
    "ticks": 0,
}

for path in (PROBE_PATH, ERROR_PATH, ORIGINAL_PATH):
    if os.path.exists(path):
        os.remove(path)


def finish(marker):
    print(marker)
    with open(PROBE_PATH, "w") as probe_file:
        probe_file.write(marker + "\n")
    sys.stdout.flush()
    STATE["phase"] = "done"
    pf.global_event(pf.SDL_QUIT, None)


def fail(reason):
    with open(ERROR_PATH, "w") as errfile:
        errfile.write(str(reason) + "\n")
    sys.stdout.flush()
    os._exit(1)


def target_state():
    return {
        "pf.video.vsync": False,
        "pf.game.healthbar_mode": int(pf.HB_MODE_NEVER),
    }


def current_state():
    return {
        "pf.video.vsync": bool(pf.settings_get("pf.video.vsync")),
        "pf.game.healthbar_mode": int(pf.settings_get("pf.game.healthbar_mode")),
    }


def on_update(user, event):
    del user
    del event

    STATE["ticks"] += 1
    settings_vc = demo_main.demo_vc._DemoVC__settings_vc
    video_vc, game_vc = settings_vc._TabBarVC__children

    if STATE["phase"] == "apply_video" and STATE["ticks"] >= 30:
        original = current_state()
        with open(ORIGINAL_PATH, "w") as original_file:
            json.dump(original, original_file, sort_keys=True)

        video_vc.view.vsync_idx = 1
        pf.global_event(common.constants.EVENT_SETTINGS_APPLY, None)
        STATE["phase"] = "switch_to_game"
        STATE["ticks"] = 0
        return

    if STATE["phase"] == "switch_to_game" and STATE["ticks"] >= 30:
        curr = current_state()
        if curr["pf.video.vsync"] is not False:
            fail("VIDEO_SETTING_APPLY_MISMATCH expected_vsync=False actual={0}".format(curr))
        pf.global_event(common.constants.EVENT_SETTINGS_TAB_SEL_CHANGED, 1)
        STATE["phase"] = "apply_game"
        STATE["ticks"] = 0
        return

    if STATE["phase"] == "apply_game" and STATE["ticks"] >= 30:
        game_vc.view.hb_idx = 1
        pf.global_event(common.constants.EVENT_SETTINGS_APPLY, None)
        STATE["phase"] = "verify"
        STATE["ticks"] = 0
        return

    if STATE["phase"] == "verify" and STATE["ticks"] >= 30:
        curr = current_state()
        expected = target_state()
        if curr != expected:
            fail("SETTINGS_APPLY_MISMATCH expected={0} actual={1}".format(expected, curr))
        finish("NATIVE_SETTINGS_APPLIED {0}".format(curr))
        return

    if STATE["ticks"] >= 300:
        fail("Timed out waiting for native settings apply probe to finish")


demo_main.main()
demo_main.demo_vc._DemoVC__settings_vc.activate()
pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)
