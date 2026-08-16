#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
#
# Build Chiron.app — a double-clickable macOS bundle around the same binary
# `swift run` produces. The app still shells out to the vault's Python, so the
# bundle records which vault it was built against and passes it through as
# CHIRON_VAULT; a bundle carries no engine of its own.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
VAULT="$(cd "$HERE/.." && pwd)"
OUT="${1:-$HERE/build}"
# Build outside any iCloud-synced tree: the file provider stamps FinderInfo on
# fresh bundles and codesign refuses to sign them.
SCRATCH="${CHIRON_SCRATCH:-/tmp/chiron-build}"

echo "==> building release binary (scratch: $SCRATCH)"
swift build -c release --scratch-path "$SCRATCH" --package-path "$HERE"
BIN="$(swift build -c release --scratch-path "$SCRATCH" --package-path "$HERE" --show-bin-path)/chiron-app"

APP="$OUT/Chiron.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/Chiron"

echo "==> generating icon"
python3 "$HERE/make_icon.py" "$OUT/icon" >/dev/null
if [ -f "$OUT/icon.icns" ]; then
  cp "$OUT/icon.icns" "$APP/Contents/Resources/Chiron.icns"
  ICON_KEY='<key>CFBundleIconFile</key><string>Chiron</string>'
else
  echo "    (no icns produced — bundling without an icon)"
  ICON_KEY=''
fi

VERSION="$(cd "$VAULT" && git describe --tags --always 2>/dev/null || echo 0.0.0)"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Chiron Workstation</string>
  <key>CFBundleDisplayName</key><string>Chiron Workstation</string>
  <key>CFBundleExecutable</key><string>Chiron</string>
  <key>CFBundleIdentifier</key><string>com.jacobiannotti.chiron</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.developer-tools</string>
  ${ICON_KEY}
  <key>CHIRONVaultPath</key><string>${VAULT}</string>
</dict>
</plist>
PLIST

# A double-clicked bundle inherits no shell environment, so it cannot find the
# vault by walking up from a working directory. The launcher supplies the path
# this bundle was built against; the in-app folder picker overrides it.
mv "$APP/Contents/MacOS/Chiron" "$APP/Contents/MacOS/Chiron-bin"
cat > "$APP/Contents/MacOS/Chiron" <<LAUNCH
#!/bin/bash
export CHIRON_VAULT="\${CHIRON_VAULT:-${VAULT}}"
exec "\$(dirname "\$0")/Chiron-bin" "\$@"
LAUNCH
chmod +x "$APP/Contents/MacOS/Chiron"

xattr -cr "$APP" 2>/dev/null || true
codesign --force --deep --sign - "$APP" 2>/dev/null \
  && echo "==> ad-hoc signed" \
  || echo "==> WARNING: codesign failed; the app will still run locally"

echo "==> built $APP"
echo "    open \"$APP\""
