#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="${PF_EDITOR_APP_NAME:-Permafrost Editor}"
BUNDLE_DIR="${PF_EDITOR_APP_BUNDLE_DIR:-$ROOT/dist/$APP_NAME.app}"
BUNDLE_ID="${PF_EDITOR_BUNDLE_ID:-org.permafrostengine.editor.dev}"
BACKEND="${RENDER_BACKEND:-METAL}"
SKIP_BUILD=0
LAUNCH=0
VERIFY=0
VERIFY_EDITING=0

usage() {
    cat <<'EOF'
Usage: scripts/macos/build_editor_app_bundle.sh [options]

Options:
  --backend METAL|OPENGL     Build backend to package (default: METAL)
  --bundle-dir PATH          Output .app bundle path (default: dist/Permafrost Editor.app)
  --skip-build               Reuse the existing bin/pf-arm64
  --launch                   Open the app and leave it running
  --verify                   Open the app, verify the editor process, then stop it
  --verify-editing           Run packaged editor feature/save-reload/visual QA
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend)
            BACKEND="${2:?missing backend}"
            shift 2
            ;;
        --bundle-dir)
            BUNDLE_DIR="${2:?missing bundle dir}"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=1
            shift
            ;;
        --launch)
            LAUNCH=1
            shift
            ;;
        --verify)
            VERIFY=1
            LAUNCH=1
            shift
            ;;
        --verify-editing)
            VERIFY_EDITING=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done

case "$BACKEND" in
    METAL|OPENGL) ;;
    *)
        echo "Unsupported backend: $BACKEND" >&2
        exit 2
        ;;
esac

if [[ "$SKIP_BUILD" -eq 0 ]]; then
    make -C "$ROOT" pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND="$BACKEND"
fi

if [[ ! -x "$ROOT/bin/pf-arm64" ]]; then
    echo "Missing executable: $ROOT/bin/pf-arm64" >&2
    exit 1
fi

MACOS_DIR="$BUNDLE_DIR/Contents/MacOS"
RESOURCES_DIR="$BUNDLE_DIR/Contents/Resources"
RUNTIME_DIR="$RESOURCES_DIR/permafrost"
rm -rf "$BUNDLE_DIR"
mkdir -p "$MACOS_DIR" "$RUNTIME_DIR"

cat > "$BUNDLE_DIR/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>pf-arm64</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

cat > "$BUNDLE_DIR/Contents/PkgInfo" <<'EOF'
APPL????
EOF

cp "$ROOT/bin/pf-arm64" "$MACOS_DIR/pf-arm64-bin"
cp "$ROOT/pf.conf" "$RUNTIME_DIR/pf.conf"
/bin/cp -R -X "$ROOT/assets" "$RUNTIME_DIR/assets"
/bin/cp -R -X "$ROOT/scripts" "$RUNTIME_DIR/scripts"
/bin/cp -R -X "$ROOT/shaders" "$RUNTIME_DIR/shaders"

cat > "$MACOS_DIR/permafrost-editor.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$(cd "$SCRIPT_DIR/../Resources/permafrost" && pwd)"
cd "$RUNTIME_DIR"
BUNDLE_ID="__PF_EDITOR_BUNDLE_ID__"
ENV_FILE="${PF_EDITOR_APP_ENV_FILE:-/tmp/$BUNDLE_ID.env}"
if [[ -f "$ENV_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$ENV_FILE"
fi
LOG_PATH="${PF_EDITOR_APP_LOG:-/tmp/permafrost-editor.log}"
mkdir -p "$(dirname "$LOG_PATH")"
{
    echo "Permafrost Editor launch $(date)"
    echo "runtime=$RUNTIME_DIR"
} >> "$LOG_PATH"
exec "$SCRIPT_DIR/pf-arm64-bin" ./ ./scripts/macos/pf_editor_app.py "$@" >> "$LOG_PATH" 2>&1
EOF
/usr/bin/sed -i '' "s|__PF_EDITOR_BUNDLE_ID__|$BUNDLE_ID|g" "$MACOS_DIR/permafrost-editor.sh"
chmod +x "$MACOS_DIR/permafrost-editor.sh"

cat > "$MACOS_DIR/pf-arm64.m" <<'EOF'
#include <Cocoa/Cocoa.h>
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char exe_path[PATH_MAX];
    uint32_t exe_size = sizeof(exe_path);
    if(_NSGetExecutablePath(exe_path, &exe_size) != 0)
        return 127;

    char real_path[PATH_MAX];
    if(realpath(exe_path, real_path) == NULL)
        return 127;

    char dir_buf[PATH_MAX];
    strlcpy(dir_buf, real_path, sizeof(dir_buf));
    char *macos_dir = dirname(dir_buf);

    char script_path[PATH_MAX];
    snprintf(script_path, sizeof(script_path), "%s/permafrost-editor.sh", macos_dir);

    char **args = calloc((size_t)argc + 2, sizeof(char *));
    if(args == NULL)
        return 127;

    args[0] = "/bin/bash";
    args[1] = script_path;
    for(int i = 1; i < argc; i++)
        args[i + 1] = argv[i];
    args[argc + 1] = NULL;

    execv("/bin/bash", args);
    perror("execv");
    return 127;
}
EOF
/usr/bin/cc "$MACOS_DIR/pf-arm64.m" -framework Cocoa -o "$MACOS_DIR/pf-arm64"
rm "$MACOS_DIR/pf-arm64.m"

/usr/bin/xattr -cr "$BUNDLE_DIR" 2>/dev/null || true

cat > "$RESOURCES_DIR/README.txt" <<EOF
Development app bundle for the Permafrost Engine editor.

This bundle stages pf-arm64 plus the assets, scripts, and shaders required by
the editor under Contents/Resources/permafrost so macOS privacy controls do not
block the app from reading the repository checkout on Desktop/Documents.
EOF

/usr/bin/dot_clean -m "$BUNDLE_DIR" 2>/dev/null || true
/usr/bin/xattr -cr "$BUNDLE_DIR" 2>/dev/null || true
/usr/bin/xattr -r -d com.apple.FinderInfo "$BUNDLE_DIR" 2>/dev/null || true
/usr/bin/xattr -r -d com.apple.ResourceFork "$BUNDLE_DIR" 2>/dev/null || true
if ! /usr/bin/codesign --force --deep --sign - "$BUNDLE_DIR"; then
    echo "EDITOR_APP_CODESIGN_WARNING ad-hoc signing failed; continuing with unsigned development bundle" >&2
fi

echo "EDITOR_APP_BUNDLE_READY path=$BUNDLE_DIR backend=$BACKEND"

if [[ "$LAUNCH" -eq 1 ]]; then
    /usr/bin/open -n "$BUNDLE_DIR"
fi

if [[ "$VERIFY" -eq 1 ]]; then
    MATCH="pf-arm64-bin .*scripts/macos/pf_editor_app.py"
    pid=""
    for _ in {1..80}; do
        pid="$(pgrep -f "$MATCH" | head -n 1 || true)"
        if [[ -n "$pid" ]]; then
            break
        fi
        sleep 0.25
    done
    if [[ -z "$pid" ]]; then
        echo "EDITOR_APP_LAUNCH_FAIL no editor process found" >&2
        exit 1
    fi
    echo "EDITOR_APP_LAUNCH_READY pid=$pid"
    pkill -9 -f "$MATCH" || true
fi

if [[ "$VERIFY_EDITING" -eq 1 ]]; then
    python3 "$ROOT/scripts/macos/verify_editor_app_bundle.py" \
        --bundle-dir "$BUNDLE_DIR" \
        --expect-backend "$BACKEND"
fi
