#!/bin/bash
#
# Builds a self-contained eScriptorium.app (macOS, Apple Silicon) plus a .dmg.
#
# Usage:
#   packaging/macos/build.sh          build the .app and .dmg
#   packaging/macos/build.sh --test   additionally run a smoke test
#
# Prerequisites: Apple Silicon macOS 13+, Xcode command line tools,
# Homebrew, Node.js >= 20, curl, jq.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
BUILD="$HERE/build"
DIST="$BUILD/dist"
APP_NAME="eScriptorium"
PY_MINOR=12
PG_VERSION=18
REDIS_VERSION=7.4.3
JRE_MAJOR=21
VERSION_DATE="${VERSION_DATE:-UBMA-$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || date +%Y-%m-%d)}"
RUN_SMOKE_TEST=0
[ "${1:-}" = "--test" ] && RUN_SMOKE_TEST=1

fail() { echo "error: $*" >&2; exit 1; }

# --- prerequisites -----------------------------------------------------------
[ "$(uname -m)" = "arm64" ] || fail "this build must run on Apple Silicon"
for tool in curl jq npm node git hdiutil brew rsync swiftc; do
    command -v "$tool" >/dev/null || fail "required tool not found: $tool"
done

rm -rf "$BUILD" "$DIST"
mkdir -p "$BUILD/downloads" "$BUILD/work" "$DIST"

# --- bundled Python -----------------------------------------------------------
# Relocatable CPython from python-build-standalone (latest release).
# The runtime plus installed dependencies is cached in .cache/ and reused
# as long as app/requirements.txt is unchanged.
echo "==> Bundling Python 3.${PY_MINOR} (python-build-standalone)"
PYCACHE="$HERE/.cache/python-3.${PY_MINOR}"
REQ_HASH="$(shasum -a 256 "$REPO_ROOT/app/requirements.txt" | awk '{print $1}')"
if [ -x "$PYCACHE/bin/python" ] && [ "$(cat "${PYCACHE}.reqhash" 2>/dev/null)" = "$REQ_HASH" ]; then
    echo "    (using cached runtime)"
    cp -c -R "$PYCACHE" "$BUILD/work/python" 2>/dev/null || cp -R "$PYCACHE" "$BUILD/work/python"
else
    PBS_TAG="$(curl -fsSL https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest | jq -r .tag_name)"
    PY_NAME="$(curl -fsSL "https://api.github.com/repos/astral-sh/python-build-standalone/releases/tags/${PBS_TAG}" \
        | jq -r '.assets[].name' \
        | grep -E "^cpython-3\.${PY_MINOR}\.[0-9]+\+${PBS_TAG}-aarch64-apple-darwin-install_only\.tar\.gz$" \
        | head -1 || true)"
    [ -n "$PY_NAME" ] || fail "no python-build-standalone 3.${PY_MINOR} aarch64 macOS asset for tag ${PBS_TAG}"
    PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PY_NAME}"
    curl -fSL --retry 3 --retry-delay 2 --retry-all-errors --progress-bar -o "$BUILD/downloads/python.tar.gz" "$PY_URL"
    tar -xzf "$BUILD/downloads/python.tar.gz" -C "$BUILD/work"
    PY="$BUILD/work/python/bin/python"
    echo "==> Installing Python dependencies"
    # uWSGI is only used by the Docker deployment; the bundle serves via runserver.
    grep -v '^uWSGI' "$REPO_ROOT/app/requirements.txt" > "$BUILD/requirements-bundle.txt"
    "$PY" -m pip install --no-cache-dir --quiet -r "$BUILD/requirements-bundle.txt"
    rm -rf "$PYCACHE"
    mkdir -p "$HERE/.cache"
    cp -c -R "$BUILD/work/python" "$PYCACHE" 2>/dev/null || cp -R "$BUILD/work/python" "$PYCACHE"
    echo "$REQ_HASH" > "${PYCACHE}.reqhash"
fi
PY="$BUILD/work/python/bin/python"

# --- frontend ------------------------------------------------------------------
echo "==> Building frontend"
npm ci --prefix "$REPO_ROOT/front" --no-audit --no-fund
npm run production --prefix "$REPO_ROOT/front"

# --- PostgreSQL ----------------------------------------------------------------
# Copy the Homebrew keg and rewrite its dylib references so the tree is
# self-contained on machines without Homebrew.
echo "==> Vendoring PostgreSQL ${PG_VERSION}"
brew install --quiet "postgresql@${PG_VERSION}"
PG_PREFIX="$(brew --prefix "postgresql@${PG_VERSION}")"
# Trailing /. forces dereferencing: the keg prefix is a symlink and
# `cp -R` would otherwise copy the link itself.
cp -R "$PG_PREFIX/." "$BUILD/work/postgres"
rm -rf "$BUILD/work/postgres/include"

vendor_dylibs() {
    local dir="$1"
    local libdir="$dir/lib"
    local map="$dir/.dylibmap"
    mkdir -p "$libdir"
    : > "$map"
    local file ref base origin changed pass
    for pass in 1 2 3 4 5 6 7 8 9 10; do
        changed=0
        for file in "$dir"/bin/* "$libdir"/*; do
            [ -f "$file" ] || continue
            otool -L "$file" >/dev/null 2>&1 || continue
            while IFS= read -r ref; do
                [ -n "$ref" ] || continue
                case "$ref" in
                    /opt/homebrew/*)
                        base="$(basename "$ref")"
                        if [ ! -e "$libdir/$base" ]; then
                            cp "$ref" "$libdir/$base"
                            printf '%s\t%s\n' "$base" "$ref" >> "$map"
                            # warnings about invalidated code signatures are
                            # expected (re-signed ad-hoc below)
                            install_name_tool -id "@rpath/$base" "$libdir/$base" 2>/dev/null
                        fi
                        install_name_tool -change "$ref" "@rpath/$base" "$file" 2>/dev/null
                        changed=1
                        ;;
                    @loader_path/*)
                        # Sibling of a copied dylib: resolve it against the
                        # original keg location and copy it in, so the
                        # reference resolves inside the bundle.
                        base="${ref#@loader_path/}"
                        origin="$(awk -F'\t' -v b="$(basename "$file")" '$1 == b {print $2; exit}' "$map" 2>/dev/null)"
                        if [ -n "$origin" ] && [ -e "$(dirname "$origin")/$base" ] && [ ! -e "$libdir/$base" ]; then
                            cp "$(dirname "$origin")/$base" "$libdir/$base"
                            printf '%s\t%s\n' "$base" "$(dirname "$origin")/$base" >> "$map"
                            changed=1
                        fi
                        ;;
                esac
            done < <(otool -L "$file" 2>/dev/null | awk 'NR>1 {print $1}' | grep -E '^(/opt/homebrew/|@loader_path/)' || true)
        done
        [ "$changed" = 1 ] || break
    done
    rm -f "$map"
    for file in "$dir"/bin/*; do
        [ -f "$file" ] || continue
        otool -L "$file" >/dev/null 2>&1 || continue
        install_name_tool -add_rpath "@executable_path/../lib" "$file" 2>/dev/null || true
    done
    for file in "$libdir"/*; do
        [ -f "$file" ] || continue
        install_name_tool -add_rpath "@loader_path" "$file" 2>/dev/null || true
    done
    # install_name_tool invalidates the code signatures that Apple requires
    # on arm64; re-sign ad-hoc after modifying.
    for file in "$dir"/bin/* "$libdir"/*; do
        [ -f "$file" ] || continue
        codesign --force --sign - "$file" 2>/dev/null || true
    done
}
vendor_dylibs "$BUILD/work/postgres"

# --- Redis ---------------------------------------------------------------------
echo "==> Building Redis ${REDIS_VERSION}"
curl -fSL --retry 3 --retry-delay 2 --retry-all-errors --progress-bar -o "$BUILD/downloads/redis.tar.gz" \
    "https://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz"
tar -xzf "$BUILD/downloads/redis.tar.gz" -C "$BUILD/downloads"
# -Wno-implicit-const-int-float-conversion silences a benign warning in
# Redis' timeout.c when built with recent Clang (Xcode 16+).
make -C "$BUILD/downloads/redis-${REDIS_VERSION}" -j"$(sysctl -n hw.ncpu)" MALLOC=libc \
    CFLAGS="-Wno-implicit-const-int-float-conversion" >/dev/null
mkdir -p "$BUILD/work/redis"
cp "$BUILD/downloads/redis-${REDIS_VERSION}/src/redis-server" "$BUILD/work/redis/"
cp "$BUILD/downloads/redis-${REDIS_VERSION}/src/redis-cli" "$BUILD/work/redis/"

# --- Java (passim alignment) -----------------------------------------------------
echo "==> Bundling Temurin JRE ${JRE_MAJOR}"
JRE_URL="$(curl -fsSL "https://api.adoptium.net/v3/assets/latest/${JRE_MAJOR}/hotspot" \
    | jq -r '.[] | select(.binary.image_type == "jre" and .binary.architecture == "aarch64" and .binary.os == "mac") | .binary.package.link' \
    | head -1 || true)"
[ -n "$JRE_URL" ] || fail "could not resolve Temurin JRE ${JRE_MAJOR} aarch64 macOS URL"
curl -fSL --retry 3 --retry-delay 2 --retry-all-errors --progress-bar -o "$BUILD/downloads/jre.tar.gz" "$JRE_URL"
tar -xzf "$BUILD/downloads/jre.tar.gz" -C "$BUILD/downloads"
JRE_DIR="$(find "$BUILD/downloads" -maxdepth 1 -type d -name 'jdk-*jre' | head -1)"
[ -n "$JRE_DIR" ] || fail "JRE tarball did not extract as expected"
mkdir -p "$BUILD/work/jre/Contents"
mv "$JRE_DIR/Contents/Home" "$BUILD/work/jre/Contents/Home"

# --- assemble the .app ------------------------------------------------------------
echo "==> Assembling ${APP_NAME}.app"
APP="$DIST/${APP_NAME}.app"
rm -rf "$APP"
cp -R "$HERE/app-template/${APP_NAME}.app" "$APP"
PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION_DATE" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION_DATE" "$PLIST"
BUNDLE_RES="$APP/Contents/Resources"
mkdir -p "$BUNDLE_RES"

# --- menu bar agent ------------------------------------------------------------
echo "==> Compiling menu bar agent"
swiftc -O -o "$APP/Contents/MacOS/eScriptoriumAgent" "$HERE/agent/EScriptoriumAgent.swift"

# --- app icon ------------------------------------------------------------
echo "==> Generating app icon"
ICON_SRC="$REPO_ROOT/app/escriptorium/static/images/escriptorium_hd.png"
ICONSET="$BUILD/work/eScriptorium.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
icon_size() { sips -z "$2" "$2" "$ICON_SRC" --out "$ICONSET/$1" >/dev/null; }
icon_size icon_16x16.png 16
icon_size icon_16x16@2x.png 32
icon_size icon_32x32.png 32
icon_size icon_32x32@2x.png 64
icon_size icon_128x128.png 128
icon_size icon_128x128@2x.png 256
icon_size icon_256x256.png 256
icon_size icon_256x256@2x.png 512
icon_size icon_512x512.png 512
icon_size icon_512x512@2x.png 1024
iconutil -c icns "$ICONSET" -o "$BUNDLE_RES/eScriptorium.icns"

cp -R "$BUILD/work/postgres" "$BUNDLE_RES/postgres"
cp -R "$BUILD/work/redis" "$BUNDLE_RES/redis"
cp -R "$BUILD/work/jre" "$BUNDLE_RES/jre"
cp -R "$BUILD/work/python" "$BUNDLE_RES/python"
mkdir -p "$BUNDLE_RES/escriptorium/front"
# Exclude root-level directories only (anchored '/'); keep per-app static dirs.
# --- default recognition model ------------------------------------------------------------
echo "==> Bundling default recognition model (german_print)"
MODEL_CACHE="$HERE/.cache/models"
mkdir -p "$MODEL_CACHE"
DEFAULT_MODEL_URL="https://zenodo.org/records/10519596/files/german_print.mlmodel"
[ -f "$MODEL_CACHE/german_print.mlmodel" ] || \
    curl -fL --progress-bar -o "$MODEL_CACHE/german_print.mlmodel" "$DEFAULT_MODEL_URL"
mkdir -p "$BUNDLE_RES/models"
cp "$MODEL_CACHE/german_print.mlmodel" "$BUNDLE_RES/models/"

# --- default transcription fonts ------------------------------------------------------------
echo "==> Bundling default transcription fonts"
FONT_CACHE="$HERE/.cache/fonts"
mkdir -p "$FONT_CACHE" "$BUNDLE_RES/fonts"
fetch_font() {
    [ -f "$FONT_CACHE/$1" ] || curl -fL --progress-bar -o "$FONT_CACHE/$1" "$2"
}
# Gentium Plus (SIL, OFL): Latin/Greek/Cyrillic incl. full phonetic extensions
fetch_font "GentiumPlus-6.200.zip" \
    "https://github.com/silnrsi/font-gentium/releases/download/v6.200/GentiumPlus-6.200.zip"
unzip -p "$FONT_CACHE/GentiumPlus-6.200.zip" "GentiumPlus-6.200/GentiumPlus-Regular.ttf" \
    > "$BUNDLE_RES/fonts/Gentium Plus.ttf"
# Noto Sans Hebrew (Google, OFL): Hebrew coverage for the transcription font fallback
fetch_font "NotoSansHebrew-v3.001.zip" \
    "https://github.com/notofonts/hebrew/releases/download/NotoSansHebrew-v3.001/NotoSansHebrew-v3.001.zip"
unzip -p "$FONT_CACHE/NotoSansHebrew-v3.001.zip" "NotoSansHebrew/full/ttf/NotoSansHebrew-Regular.ttf" \
    > "$BUNDLE_RES/fonts/Noto Sans Hebrew.ttf"
# OpenDyslexic (antijingoist, OFL): dyslexia-friendly
fetch_font "OpenDyslexic-Regular.otf" \
    "https://raw.githubusercontent.com/antijingoist/opendyslexic/main/compiled/OpenDyslexic-Regular.otf"
cp "$FONT_CACHE/OpenDyslexic-Regular.otf" "$BUNDLE_RES/fonts/OpenDyslexic.otf"

rsync -a \
    --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
    --exclude '/media' --exclude '/test_media' --exclude '/static' --exclude '/logs' \
    "$REPO_ROOT/app/" "$BUNDLE_RES/escriptorium/app/"
rsync -a "$REPO_ROOT/front/dist/" "$BUNDLE_RES/escriptorium/front/dist/"
echo "$VERSION_DATE" > "$BUNDLE_RES/version.txt"
chmod +x "$APP/Contents/MacOS/$APP_NAME"

# --- disk image -------------------------------------------------------------------
# Plain hdiutil: app plus Applications alias, volume icon set on the mounted
# image. (create-dmg would add a nicer window layout, but it scripts Finder,
# which requires interactive Automation permission that is unavailable in
# headless/CI runs.)
echo "==> Creating disk image"
STAGE="$BUILD/dmg"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
DMG="$BUILD/${APP_NAME}-${VERSION_DATE}.dmg"
TMP_DMG="$BUILD/tmp.dmg"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -format UDRW -o "$TMP_DMG" >/dev/null
MOUNTED="$(hdiutil attach -nobrowse "$TMP_DMG" | awk -F'\t' 'NF >= 3 && $NF != "" { m = $NF } END { print m }')"
[ -n "$MOUNTED" ] || fail "could not mount $TMP_DMG"
cp "$BUNDLE_RES/eScriptorium.icns" "$MOUNTED/.VolumeIcon.icns"
SetFile -a C "$MOUNTED"
hdiutil detach "$MOUNTED" >/dev/null
hdiutil convert "$TMP_DMG" -format UDZO -ov -o "$DMG" >/dev/null
rm -f "$TMP_DMG"
# .dmg file icon shown by Finder in the enclosing folder. The resource
# fork format used here addresses the data with 16-bit offsets, so the
# icon must be a reduced icns (< ~64 KB; this one tops out at 128px).
DMG_ICNS="$BUILD/work/dmg_icon.icns"
DMG_ICONSET="$BUILD/work/dmg_icon.iconset"
rm -rf "$DMG_ICONSET"
mkdir -p "$DMG_ICONSET"
sips -z 16 16 "$ICON_SRC" --out "$DMG_ICONSET/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_SRC" --out "$DMG_ICONSET/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_SRC" --out "$DMG_ICONSET/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_SRC" --out "$DMG_ICONSET/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_SRC" --out "$DMG_ICONSET/icon_128x128.png" >/dev/null
iconutil -c icns "$DMG_ICONSET" -o "$DMG_ICNS"
/usr/bin/python3 "$HERE/set_dmg_icon.py" "$DMG" "$DMG_ICNS" icns
SetFile -a C "$DMG"

# --- smoke test ---------------------------------------------------------------------
if [ "$RUN_SMOKE_TEST" = 1 ]; then
    echo "==> Smoke test"
    # Non-default ports so the test cannot collide with a local dev server.
    TEST_WEB_PORT=18000
    TEST_DATA="$(mktemp -u)/eScriptorium"
    ESC_ENV="ESCR_DATA_DIR=$TEST_DATA ESCR_WEB_PORT=$TEST_WEB_PORT ESCR_PG_PORT=15433 ESCR_REDIS_PORT=16380"
    env $ESC_ENV "$APP/Contents/MacOS/$APP_NAME" start >/dev/null 2>&1 || {
        tail -50 "$TEST_DATA/logs/launcher.log" 2>/dev/null
        env $ESC_ENV "$APP/Contents/MacOS/$APP_NAME" stop >/dev/null 2>&1
        fail "smoke test: launcher failed to start"
    }
    ok=0
    for _ in $(seq 1 120); do
        if curl -fsS "http://127.0.0.1:${TEST_WEB_PORT}/health" >/dev/null 2>&1; then
            ok=1
            break
        fi
        sleep 2
    done
    if [ "$ok" != 1 ]; then
        tail -50 "$TEST_DATA/logs/web.log" 2>/dev/null
        env $ESC_ENV "$APP/Contents/MacOS/$APP_NAME" stop >/dev/null 2>&1
        fail "smoke test: /health never came up"
    fi
    # Verify the homepage renders and at least one static asset is served.
    HOME_URL="$(curl -fsS "http://127.0.0.1:${TEST_WEB_PORT}/" | grep -o '/static/[^"]*' | head -1 || true)"
    [ -n "$HOME_URL" ] || { env $ESC_ENV "$APP/Contents/MacOS/$APP_NAME" stop; fail "smoke test: no static URL found on homepage"; }
    curl -fsS "http://127.0.0.1:${TEST_WEB_PORT}${HOME_URL}" >/dev/null \
        || { env $ESC_ENV "$APP/Contents/MacOS/$APP_NAME" stop; fail "smoke test: static asset $HOME_URL not served"; }
    env $ESC_ENV "$APP/Contents/MacOS/$APP_NAME" stop >/dev/null 2>&1
    rm -rf "$(dirname "$TEST_DATA")"
    echo "==> Smoke test passed"
fi

echo "==> Done: $BUILD/${APP_NAME}-${VERSION_DATE}.dmg"
