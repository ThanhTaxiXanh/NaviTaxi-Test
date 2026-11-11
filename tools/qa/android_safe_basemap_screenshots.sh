#!/usr/bin/env bash
# Capture REAL Android MapLibre safe-fallback screenshots.
# Only unapproved debug APK and screen images; not evidence of sovereignty PASS.
set -euo pipefail
APP="vn.navitaxi.navi_taxi_test"
MAIN="vn.navitaxi.navi_taxi_test/.MainActivity"
OUT="build/qa/p0-safe-fallback"
mkdir -p "$OUT"

adb wait-for-device
adb install -r build/app/outputs/flutter-apk/app-debug.apk
adb shell settings put system screen_off_timeout 600000
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm size 1080x1920
adb shell wm density 320

start_app() {
  adb shell am force-stop "$APP" || true
  adb shell am start -W -n "$MAIN"
  # Flutter engine, MapLibre surface and asset checks initialize asynchronously.
  sleep 17
}

capture() {
  local name="$1"
  adb exec-out screencap -p > "$OUT/$name.png"
  python3 - "$OUT/$name.png" <<'PY'
import struct, sys
from pathlib import Path
p=Path(sys.argv[1])
raw=p.read_bytes()
if len(raw)<4096 or raw[:8]!=b"\x89PNG\r\n\x1a\n":
    raise SystemExit("Android emulator screenshot missing/invalid: "+str(p))
width,height=struct.unpack_from(">II",raw,16)
if width<400 or height<700:
    raise SystemExit("Screenshot unexpectedly small")
print(f"Verified screenshot {p.name}: {width}x{height} ({len(raw)} bytes)")
PY
}

# Normal boot. A blocked manifest must render an empty MapLibre style.
adb shell cmd uimode night no
adb shell settings put global airplane_mode_on 0
adb shell svc wifi enable || true
start_app
capture "blocked-light-online"

# Dark mode: screenshots of the same P0-safe fallback.
adb shell cmd uimode night yes
start_app
capture "blocked-dark-online"

# Airplane mode: unapproved sources must remain inactive without connectivity.
adb shell settings put global airplane_mode_on 1
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true || true
adb shell svc wifi disable || true
adb shell svc data disable || true
start_app
capture "blocked-dark-airplane"

# Restore connectivity to ensure the session does not depend on airplane mode.
adb shell settings put global airplane_mode_on 0
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false || true
adb shell svc wifi enable || true
adb shell cmd uimode night no
start_app
capture "blocked-light-restored"
