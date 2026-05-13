#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${1:-"$ROOT_DIR/qa-output/sovereign-ai-large-army-scale-1000-profile"}"
if [[ "$OUT_DIR" != /* ]]; then
  OUT_DIR="$ROOT_DIR/$OUT_DIR"
fi
TEMPLATE="${PF_PROFILE_TEMPLATE:-Time Profiler}"
UNITS_PER_SIDE="${PF_PROFILE_UNITS_PER_SIDE:-500}"
SETTLE_TICKS="${PF_PROFILE_SETTLE_TICKS:-300}"
SOAK_TICKS="${PF_PROFILE_SOAK_TICKS:-240}"
SAMPLE_EVERY="${PF_PROFILE_SAMPLE_EVERY:-30}"
SOFT_BUDGET_MS="${PF_PROFILE_SOFT_BUDGET_MS:-500}"
CAPTURE_PROOF="${PF_PROFILE_CAPTURE_PROOF:-1}"
CAPTURE_CLEARPATH_STATS="${PF_PROFILE_CLEARPATH_STATS:-0}"
CLEARPATH_FALLBACK_REMOVE_BATCH="${PF_PROFILE_CLEARPATH_FALLBACK_REMOVE_BATCH:-}"
CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS="${PF_PROFILE_CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS:-}"
CLEARPATH_FALLBACK_MAX_REMOVES="${PF_PROFILE_CLEARPATH_FALLBACK_MAX_REMOVES:-}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$OUT_DIR/run-$STAMP"
TRACE_PATH="$RUN_DIR/sovereign_${UNITS_PER_SIDE}x2_${TEMPLATE// /_}.trace"
TIME_PROFILE_XML="$RUN_DIR/time_profile.xml"
TIME_PROFILE_TOP="$RUN_DIR/time_profile_top.txt"
TIME_PROFILE_FOCUS="$RUN_DIR/time_profile_focus.txt"
TARGET_STDOUT="$RUN_DIR/target_stdout.txt"
SUMMARY_PATH="$RUN_DIR/summary_sovereign_ai_large_army_scale.json"
RUN_RECORD="$RUN_DIR/profile_run_summary.json"
CLEARPATH_STATS_PATH="$RUN_DIR/clearpath_stats.json"
TARGET_PID_FILE="$RUN_DIR/target_pid.txt"
ATTACH_DELAY_SEC="${PF_PROFILE_ATTACH_DELAY_SEC:-8}"
EXPORT_TIME_PROFILE="${PF_PROFILE_EXPORT_TIME_PROFILE:-1}"
PROFILE_REBUILD="${PF_PROFILE_REBUILD:-0}"
PROFILE_REBUILD_BACKEND="${PF_PROFILE_REBUILD_BACKEND:-METAL}"
PROFILE_REBUILD_TYPE="${PF_PROFILE_REBUILD_TYPE:-DEBUG}"
PROFILE_CFLAGS="${PF_PROFILE_CFLAGS:--g -fno-omit-frame-pointer -fno-optimize-sibling-calls}"

mkdir -p "$RUN_DIR"

echo "PROFILE_RUN_DIR $RUN_DIR"
echo "PROFILE_TEMPLATE $TEMPLATE"
echo "PROFILE_TRACE $TRACE_PATH"

cd "$ROOT_DIR"

if [[ "$PROFILE_REBUILD" != "0" ]]; then
  echo "PROFILE_REBUILD backend=$PROFILE_REBUILD_BACKEND type=$PROFILE_REBUILD_TYPE cflags=$PROFILE_CFLAGS"
  make -B pf \
    PLAT=MACOS_ARM64 \
    MACOS_ARM64_BUILD_READY=1 \
    RENDER_BACKEND="$PROFILE_REBUILD_BACKEND" \
    TYPE="$PROFILE_REBUILD_TYPE" \
    EXTRA_CFLAGS="$PROFILE_CFLAGS"
fi

TARGET_CMD=(
  ./bin/pf-arm64
  ./
  ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
  --output-dir "$RUN_DIR"
  --units-per-side "$UNITS_PER_SIDE"
  --settle-ticks "$SETTLE_TICKS"
  --soak-ticks "$SOAK_TICKS"
  --order-mode attack-move
  --budget-label "xctrace-${UNITS_PER_SIDE}x2"
  --sample-budget-every "$SAMPLE_EVERY"
  --soft-budget-ms-per-tick "$SOFT_BUDGET_MS"
)
if [[ "$CAPTURE_PROOF" != "0" ]]; then
  TARGET_CMD+=(--capture-proof --wide-zoom-height 1100)
fi
if [[ "$CAPTURE_CLEARPATH_STATS" != "0" ]]; then
  TARGET_CMD+=(--clearpath-stats-path "$CLEARPATH_STATS_PATH")
fi
if [[ -n "$CLEARPATH_FALLBACK_REMOVE_BATCH" ]]; then
  TARGET_CMD+=(--clearpath-fallback-remove-batch "$CLEARPATH_FALLBACK_REMOVE_BATCH")
fi
if [[ -n "$CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS" ]]; then
  TARGET_CMD+=(--clearpath-fallback-batch-min-neighbours "$CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS")
fi
if [[ -n "$CLEARPATH_FALLBACK_MAX_REMOVES" ]]; then
  TARGET_CMD+=(--clearpath-fallback-max-removes "$CLEARPATH_FALLBACK_MAX_REMOVES")
fi

"${TARGET_CMD[@]}" > "$TARGET_STDOUT" 2>&1 &
TARGET_PID="$!"
echo "$TARGET_PID" > "$TARGET_PID_FILE"
echo "PROFILE_TARGET_PID $TARGET_PID"
if [[ "$CAPTURE_CLEARPATH_STATS" != "0" ]]; then
  echo "PROFILE_CLEARPATH_STATS $CLEARPATH_STATS_PATH"
fi

sleep "$ATTACH_DELAY_SEC"

if ! kill -0 "$TARGET_PID" 2>/dev/null; then
  echo "PROFILE_TARGET_EXITED_BEFORE_ATTACH"
  cat "$TARGET_STDOUT"
  exit 1
fi

set +e
xcrun xctrace record \
  --quiet \
  --no-prompt \
  --template "$TEMPLATE" \
  --output "$TRACE_PATH" \
  --attach "$TARGET_PID"
XCTRACE_STATUS="$?"
set -e

if [[ "$XCTRACE_STATUS" -ne 0 ]]; then
  kill "$TARGET_PID" 2>/dev/null || true
  wait "$TARGET_PID" 2>/dev/null || true
  exit "$XCTRACE_STATUS"
fi

wait "$TARGET_PID"

if [[ "$EXPORT_TIME_PROFILE" != "0" && "$TEMPLATE" == "Time Profiler" ]]; then
  set +e
  xcrun xctrace export \
    --input "$TRACE_PATH" \
    --xpath '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]' \
    --output "$TIME_PROFILE_XML"
  EXPORT_STATUS="$?"
  set -e
  if [[ "$EXPORT_STATUS" -eq 0 ]]; then
    python3 - "$TIME_PROFILE_XML" "$TIME_PROFILE_TOP" "$TIME_PROFILE_FOCUS" <<'PY'
import collections
import xml.etree.ElementTree as ET
import sys

profile_xml, output_path, focus_path = sys.argv[1:4]
targets = [
    "inside_pcr",
    "compute_vo_xpoints",
    "G_ClearPath_NewVelocity",
    "move_velocity_work",
    "field_update_enemies",
    "PFM_Mat4x4_Mult4x4",
    "ray_ray_intersection_fast",
]
stacks = {}
leaf = collections.Counter()
leaf_parent = collections.Counter()
inclusive = collections.Counter()
target_parent = {target: collections.Counter() for target in targets}
target_child = {target: collections.Counter() for target in targets}
target_leaf_parent = {target: collections.Counter() for target in targets}
target_depth = {target: collections.Counter() for target in targets}
samples = 0

for _, elem in ET.iterparse(profile_xml, events=("end",)):
    if elem.tag == "tagged-backtrace":
        tag_id = elem.attrib.get("id")
        ref = elem.attrib.get("ref")
        frames = [
            frame.attrib.get("name")
            for frame in elem.iter("frame")
            if frame.attrib.get("name")
        ]
        if tag_id and frames:
            stacks[tag_id] = frames
        stack = frames or (stacks.get(ref) if ref else None)
        if stack:
            samples += 1
            leaf[stack[0]] += 1
            if len(stack) > 1:
                leaf_parent[(stack[0], stack[1])] += 1
            for name in set(stack):
                inclusive[name] += 1
            for target in targets:
                for idx, name in enumerate(stack):
                    if name != target:
                        continue
                    target_depth[target][idx] += 1
                    parent = stack[idx + 1] if idx + 1 < len(stack) else "<root>"
                    child = stack[idx - 1] if idx > 0 else "<leaf>"
                    target_parent[target][parent] += 1
                    target_child[target][child] += 1
                    if idx == 0:
                        target_leaf_parent[target][parent] += 1
                    break
        elem.clear()
    elif elem.tag == "row":
        elem.clear()

def write_counter(outfile, title, counter, limit=20):
    outfile.write(title + "\n")
    for key, count in counter.most_common(limit):
        if isinstance(key, tuple):
            key = "{0} <- {1}".format(key[0], key[1])
        pct = (count * 100.0 / samples) if samples else 0.0
        outfile.write("{0:8d} {1:6.2f}% {2}\n".format(count, pct, key))
    outfile.write("\n")

with open(output_path, "w") as outfile:
    outfile.write("samples {0}\n\n".format(samples))
    write_counter(outfile, "top_leaf", leaf)
    write_counter(outfile, "top_leaf_parent", leaf_parent)
    write_counter(outfile, "top_inclusive", inclusive, 30)
with open(focus_path, "w") as outfile:
    outfile.write("samples {0}\n\n".format(samples))
    for target in targets:
        outfile.write("## {0}\n".format(target))
        outfile.write("leaf_samples {0} {1:.2f}%\n".format(
            leaf[target], (leaf[target] * 100.0 / samples) if samples else 0.0))
        outfile.write("inclusive_samples {0} {1:.2f}%\n".format(
            inclusive[target], (inclusive[target] * 100.0 / samples) if samples else 0.0))
        write_counter(outfile, "parents", target_parent[target], 15)
        write_counter(outfile, "children", target_child[target], 15)
        write_counter(outfile, "leaf_parents", target_leaf_parent[target], 15)
        outfile.write("depths\n")
        for depth, count in sorted(target_depth[target].items()):
            pct = (count * 100.0 / samples) if samples else 0.0
            outfile.write("  depth {0}: {1} {2:.2f}%\n".format(depth, count, pct))
        outfile.write("\n")
PY
    echo "PROFILE_TIME_PROFILE_TOP $TIME_PROFILE_TOP"
    echo "PROFILE_TIME_PROFILE_FOCUS $TIME_PROFILE_FOCUS"
  else
    echo "PROFILE_TIME_PROFILE_EXPORT_FAILED $EXPORT_STATUS"
  fi
fi

python3 - "$SUMMARY_PATH" "$RUN_RECORD" "$TRACE_PATH" "$TEMPLATE" "$TIME_PROFILE_TOP" "$CLEARPATH_STATS_PATH" <<'PY'
import json
import os
import sys

summary_path, run_record, trace_path, template, time_profile_top, clearpath_stats_path = sys.argv[1:7]
if not os.path.exists(summary_path):
    payload = {
        "status": "missing_summary",
        "template": template,
        "trace_path": trace_path,
    }
else:
    summary = json.load(open(summary_path))
    budget = summary.get("budget", {})
    movement = summary.get("movement", {})
    combat = summary.get("combat", {})
    payload = {
        "status": summary.get("status"),
        "template": template,
        "trace_path": trace_path,
        "total_units": summary.get("scale", {}).get("total_units"),
        "budget": {
            "elapsed_wall_sec": budget.get("elapsed_wall_sec"),
            "sim_ticks_per_wall_sec": budget.get("sim_ticks_per_wall_sec"),
            "wall_ms_per_requested_tick": budget.get("wall_ms_per_requested_tick"),
            "tick_sample_summary": budget.get("tick_sample_summary"),
            "phase_tick_sample_summary": budget.get("phase_tick_sample_summary"),
            "warnings": budget.get("warnings", []),
        },
        "movement": {
            "moved_count": movement.get("moved_count"),
            "average_travel": movement.get("average_travel"),
            "active_animation_count": movement.get("active_animation_count"),
        },
        "combat": {
            "engine_damaged_unit_count": combat.get("engine_damaged_unit_count"),
            "player_live_count": combat.get("player_live_count"),
            "enemy_live_count": combat.get("enemy_live_count"),
        },
        "captures": [
            {"name": item.get("name"), "path": item.get("path"), "size": item.get("size")}
            for item in summary.get("captures", [])
        ],
    }
if os.path.exists(time_profile_top):
    payload["time_profile_top_path"] = time_profile_top
if os.path.exists(clearpath_stats_path):
    payload["clearpath_stats_path"] = clearpath_stats_path
    payload["clearpath_stats"] = json.load(open(clearpath_stats_path))
with open(run_record, "w") as outfile:
    json.dump(payload, outfile, indent=2, sort_keys=True)
    outfile.write("\n")
print("PROFILE_RUN_SUMMARY {0}".format(run_record))
PY
