#!/bin/bash
# Start the Chiron service, build the app if it is not present, then open it.
# Double-click this file.
#
# ChironMobile is a client: it reaches the local service over 127.0.0.1 and
# never spawns Python. That is what lets one target build for both macOS and
# iOS, where spawning a process is not possible. (The separate SwiftPM
# `chiron-app` under App/ is a different, macOS-only program that does invoke
# the vault directly.)
cd "$(dirname "$0")"
PORT=8765

if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "Chiron service already running on $PORT."
else
  echo "Starting the Chiron service on $PORT…"
  nohup python3 Chiron/service.py --port "$PORT" > /tmp/chiron-service.log 2>&1 &
  for _ in $(seq 1 20); do
    sleep 0.5
    curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
  done
fi

if ! curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "The service did not come up. Log: /tmp/chiron-service.log"
  tail -20 /tmp/chiron-service.log
  read -r -p "Press return to close."
  exit 1
fi

OPS=$(curl -s "http://127.0.0.1:$PORT/v1/capabilities" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["result"]["operations"]))')
echo "Service up: $OPS operations at http://127.0.0.1:$PORT"
# build/ is gitignored, so a fresh clone has no bundle. Build it rather than
# failing with "the file does not exist" on the first double-click.
if [ ! -d build/Chiron.app ]; then
  echo "No app bundle yet — building it (first run only, a few minutes)…"
  if ! xcodebuild -project iOS/ChironMobile.xcodeproj -scheme ChironMobile \
        -destination 'platform=macOS' -configuration Debug \
        -derivedDataPath build/dd CODE_SIGNING_ALLOWED=NO build >/dev/null 2>&1; then
    echo "Build failed. Run this to see why:"
    echo "  xcodebuild -project iOS/ChironMobile.xcodeproj -scheme ChironMobile -destination 'platform=macOS' build"
    read -r -p "Press return to close."
    exit 1
  fi
  mkdir -p build
  rm -rf build/Chiron.app
  cp -R build/dd/Build/Products/Debug/ChironMobile.app build/Chiron.app
  xattr -cr build/Chiron.app 2>/dev/null
  codesign --force --deep --sign - build/Chiron.app >/dev/null 2>&1
  echo "Built build/Chiron.app"
fi

echo "Opening Chiron…"
open build/Chiron.app
echo
echo "In the app: gear icon -> endpoint http://127.0.0.1:$PORT -> Done."
echo "Then use the Workbench tab."
