import sys
import traceback
import os
import shlex


def _load_probe_env():
    env_path = os.environ.get("PF_EDITOR_APP_ENV_FILE", "/tmp/org.permafrostengine.editor.dev.env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = shlex.split(line)
            if len(parts) != 2 or parts[0] != "export" or "=" not in parts[1]:
                continue
            key, value = parts[1].split("=", 1)
            os.environ[key] = value


def _append_app_log(message):
    log_path = os.environ.get("PF_EDITOR_APP_LOG")
    if not log_path:
        return
    with open(log_path, "a") as log_file:
        log_file.write(message + "\n")

try:
    _load_probe_env()
    _append_app_log("Permafrost Editor launch")
    import pf

    sys.path.insert(0, pf.get_basedir() + "/scripts")
    sys.path.insert(0, pf.get_basedir() + "/scripts/editor")
    _append_app_log("runtime=" + pf.get_basedir())

    import editor.main  # noqa: F401
except BaseException:
    _append_app_log(traceback.format_exc())
    traceback.print_exc()
    raise
