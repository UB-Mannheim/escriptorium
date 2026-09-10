#!/bin/bash
#
# Builds a self-contained eScriptorium.app (macOS, Apple Silicon) plus a .dmg.
#
# Usage:
#   packaging/macos/build.sh          build the .app and .dmg
#   packaging/macos/build.sh --test   additionally run a smoke test
#
# Prerequisites: Apple Silicon macOS, Xcode command line tools, Node.js >= 20,
# curl, jq. No Homebrew needed: all Homebrew dependencies are fetched as
# bottles of the HOMEBREW_TIER tier, so the result runs on macOS >=
# MIN_MACOS regardless of the build machine's own macOS version.

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
MIN_MACOS="14.0"
HOMEBREW_TIER="arm64_sonoma"
VERSION_DATE="${VERSION_DATE:-UBMA-$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || date +%Y-%m-%d)}"
RUN_SMOKE_TEST=0
[ "${1:-}" = "--test" ] && RUN_SMOKE_TEST=1

fail() { echo "error: $*" >&2; exit 1; }

# --- prerequisites -----------------------------------------------------------
[ "$(uname -m)" = "arm64" ] || fail "this build must run on Apple Silicon"
for tool in curl jq npm node git hdiutil rsync swiftc; do
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

# --- Homebrew stage prefix -------------------------------------------------------
# Homebrew publishes bottles per OS tier. A bottle carries that tier's
# minimum OS and may reference libSystem symbols that only exist there (the
# macOS 26 SDK added glibc-compat symbols such as strchrnul, which PG, glib
# and krb5 now pick up). Installing the build machine's own tier would
# therefore restrict the bundle to that OS. Instead, stage the HOMEBREW_TIER
# bottles of the full dependency closure into a prefix mirroring
# /opt/homebrew, so the bundle keeps running on macOS >= MIN_MACOS no matter
# where the build runs.
echo "==> Staging $HOMEBREW_TIER Homebrew bottles"
HB_PREFIX="$BUILD/work/homebrew"
HB_OPT="$HB_PREFIX/opt"
HB_BOTTLES="$HERE/.cache/bottles"
mkdir -p "$HB_PREFIX/Cellar" "$HB_OPT" "$HB_BOTTLES"

hb_json() { curl -fsSL --retry 3 "https://formulae.brew.sh/api/formula/${1/@/%40}.json"; }

hb_collect_deps() {
    local f="$1" json d
    case " $HB_SEEN " in *" $f "*) return ;; esac
    HB_SEEN="$HB_SEEN $f"
    json="$(hb_json "$f")" || fail "formula API failed for $f"
    HB_FORMULAS="$HB_FORMULAS $f"
    for d in $(jq -r '((.dependencies // []) + (.recommended_dependencies // []))[]? | if type == "string" then . else .name end' <<<"$json"); do
        hb_collect_deps "$d"
    done
}

hb_install_bottle() {
    local f="$1" json url sha tarball token ver hb_repo
    json="$(hb_json "$f")" || fail "formula API failed for $f"
    url="$(jq -r ".bottle.stable.files.\"$HOMEBREW_TIER\".url // empty" <<<"$json")"
    sha="$(jq -r ".bottle.stable.files.\"$HOMEBREW_TIER\".sha256 // empty" <<<"$json")"
    if [ -z "$url" ] || [ -z "$sha" ]; then
        # Formulae without a bottle (headers or data only, e.g. uthash,
        # ca-certificates) produce no dylibs, so there is nothing to stage.
        echo "    (no $HOMEBREW_TIER bottle for $f; nothing to stage)"
        return 0
    fi
    tarball="$HB_BOTTLES/$f-$HOMEBREW_TIER.bottle.tar.gz"
    if [ -f "$tarball" ] && ! echo "$sha  $tarball" | shasum -a 256 -c - >/dev/null 2>&1; then
        rm -f "$tarball"
    fi
    if [ ! -f "$tarball" ]; then
        # The GHCR repository is the path between /v2/ and /blobs/ (for
        # versioned formulae it includes the version, e.g.
        # homebrew/core/postgresql/18); the anonymous pull token must scope
        # to exactly that name.
        hb_repo="${url#https://ghcr.io/v2/}"
        hb_repo="${hb_repo%%/blobs/*}"
        token="$(curl -fsSL "https://ghcr.io/token?scope=repository:$hb_repo:pull" | jq -r .token)" \
            || fail "could not fetch GHCR token for $hb_repo"
        curl -fSL --retry 3 --retry-delay 2 --retry-all-errors \
            -H "Authorization: Bearer $token" -o "$tarball" "$url"
        echo "$sha  $tarball" | shasum -a 256 -c - >/dev/null || fail "bottle checksum mismatch for $f"
    fi
    tar -xzf "$tarball" -C "$HB_PREFIX/Cellar"
    ver="$(ls "$HB_PREFIX/Cellar/$f" | sort -V | tail -1)"
    ln -sfn "../Cellar/$f/$ver" "$HB_OPT/$f"
}

HB_SEEN=""
HB_FORMULAS=""
for f in "icu4c@78" vips geos gettext; do
    hb_collect_deps "$f"
done
for f in $HB_FORMULAS; do
    hb_install_bottle "$f"
done

# Translate a Homebrew path (installed /opt/homebrew prefix, or the
# @@HOMEBREW_PREFIX@@ / @@HOMEBREW_CELLAR@@ placeholders that raw bottles
# still carry) to the equivalent location in the staged prefix.
hb_stage_path() {
    local ref="$1" f sub rest2
    case "$ref" in
        /opt/homebrew/opt/*)
            f="${ref#/opt/homebrew/opt/}"; f="${f%%/*}"; sub="${ref#/opt/homebrew/opt/$f/}" ;;
        '@@HOMEBREW_PREFIX@@'/opt/*)
            f="${ref#'@@HOMEBREW_PREFIX@@'/opt/}"; f="${f%%/*}"; sub="${ref#'@@HOMEBREW_PREFIX@@'/opt/$f/}" ;;
        /opt/homebrew/Cellar/*|'@@HOMEBREW_CELLAR@@'/*)
            case "$ref" in
                /opt/homebrew/Cellar/*) rest2="${ref#/opt/homebrew/Cellar/}" ;;
                *) rest2="${ref#'@@HOMEBREW_CELLAR@@'/}" ;;
            esac
            f="${rest2%%/*}"
            sub="${rest2#*/}"
            sub="${sub#*/}"
            ;;
        *) return 1 ;;
    esac
    printf '%s' "$HB_OPT/$f/$sub"
}

# --- PostgreSQL ----------------------------------------------------------------
# Build from the official source tarball instead of taking the Homebrew keg:
# the keg bakes /opt/homebrew/share/postgresql@18 into get_share_path(), so
# it cannot run on a machine without Homebrew. The stock build derives the
# share dir from the executable's own path (.../bin/postgres ->
# .../share/postgresql), which keeps the bundle relocatable.
echo "==> Building PostgreSQL ${PG_VERSION} from source"
PG_SRC_VERSION="${PG_SRC_VERSION:-18.6}"
curl -fSL --retry 3 --retry-delay 2 --retry-all-errors --progress-bar \
    -o "$BUILD/downloads/postgresql-${PG_SRC_VERSION}.tar.bz2" \
    "https://ftp.postgresql.org/pub/source/v${PG_SRC_VERSION}/postgresql-${PG_SRC_VERSION}.tar.bz2"
tar -xjf "$BUILD/downloads/postgresql-${PG_SRC_VERSION}.tar.bz2" -C "$BUILD/downloads"
brew install --quiet icu4c@78
ICU_PREFIX="$(brew --prefix icu4c@78)"
# Link against the build machine's ICU keg so the recorded references are
# /opt/homebrew paths; vendor_dylibs then substitutes the staged bottle.
( cd "$BUILD/downloads/postgresql-${PG_SRC_VERSION}" && \
    PKG_CONFIG_PATH="$ICU_PREFIX/lib/pkgconfig" \
    CFLAGS="-mmacosx-version-min=${MIN_MACOS}" \
    LDFLAGS="-mmacosx-version-min=${MIN_MACOS}" \
    ./configure \
        --prefix="$BUILD/work/postgres" \
        --without-readline --without-openssl --without-lz4 --without-zstd \
        > "$BUILD/pg-configure.log" 2>&1 ) \
    || { tail -30 "$BUILD/pg-configure.log"; fail "PostgreSQL configure failed"; }
make -C "$BUILD/downloads/postgresql-${PG_SRC_VERSION}" -j"$(sysctl -n hw.ncpu)" \
    > "$BUILD/pg-make.log" 2>&1 \
    || { tail -30 "$BUILD/pg-make.log"; fail "PostgreSQL build failed"; }
make -C "$BUILD/downloads/postgresql-${PG_SRC_VERSION}" install > /dev/null 2>&1 \
    || fail "PostgreSQL install failed"
rm -rf "$BUILD/work/postgres/include" "$BUILD/work/postgres/share/doc" "$BUILD/work/postgres/share/man"

# True for Mach-O dylibs and executables; rejects static archives (otool
# -l/-L "work" on them, per member) and non-Mach-O files.
macho_ok() {
    otool -l "$1" >/dev/null 2>&1 || return 1
    case "$(otool -f "$1" 2>/dev/null)" in
        *Archive*) return 1 ;;
    esac
    return 0
}

vendor_dylibs() {
    local dir="$1"
    local libdir="$dir/lib"
    local map="$dir/.dylibmap"
    mkdir -p "$libdir"
    # Map of copied dylib basename -> original location; callers may
    # pre-populate it with directly copied seeds.
    [ -e "$map" ] || : > "$map"
    local file ref base origin changed pass
    for pass in 1 2 3 4 5 6 7 8 9 10; do
        changed=0
        for file in "$dir"/bin/* $(find "$libdir" -type f 2>/dev/null); do
            [ -f "$file" ] || continue
            macho_ok "$file" || continue
            while IFS= read -r ref; do
                [ -n "$ref" ] || continue
                case "$ref" in
                    /opt/homebrew/*|'@@HOMEBREW_PREFIX@@'/*|'@@HOMEBREW_CELLAR@@'/*)
                        staged="$(hb_stage_path "$ref")"
                        [ -n "$staged" ] && [ -e "$staged" ] || fail "Homebrew reference outside staged prefix: $ref"
                        base="$(basename "$ref")"
                        if [ ! -e "$libdir/$base" ]; then
                            cp "$staged" "$libdir/$base"
                            # Store the real staged location: sibling
                            # resolution below needs a path that exists.
                            printf '%s\t%s\n' "$base" "$staged" >> "$map"
                            # warnings about invalidated code signatures are
                            # expected (re-signed ad-hoc below)
                            install_name_tool -id "@rpath/$base" "$libdir/$base" 2>/dev/null || true
                        fi
                        install_name_tool -change "$ref" "@rpath/$base" "$file" 2>/dev/null || true
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
                    @rpath/*)
                        # Intra-keg dependency: resolve it via this file's own
                        # LC_RPATH entries (absolute keg paths, or relative to
                        # the file's original keg location) and copy it in.
                        base="${ref#@rpath/}"
                        origin="$(awk -F'\t' -v b="$(basename "$file")" '$1 == b {print $2; exit}' "$map" 2>/dev/null)"
                        origin_dir=""; [ -n "$origin" ] && origin_dir="$(dirname "$origin")"
                        [ -n "$origin_dir" ] || origin_dir="$(dirname "$file")"
                        while IFS= read -r rp; do
                            case "$rp" in
                                /opt/homebrew/*|'@@HOMEBREW_PREFIX@@'/*|'@@HOMEBREW_CELLAR@@'/*)
                                    rpp="$(hb_stage_path "$rp")"
                                    cand="$rpp/$base" ;;
                                @loader_path/*|@executable_path/*) cand="$origin_dir/${rp#*@*/}/$base" ;;
                                *) continue ;;
                            esac
                            if [ -e "$cand" ] && [ ! -e "$libdir/$base" ]; then
                                cp "$cand" "$libdir/$base"
                                printf '%s\t%s\n' "$base" "$cand" >> "$map"
                                install_name_tool -id "@rpath/$base" "$libdir/$base" 2>/dev/null || true
                                changed=1
                            fi
                        done < <(otool -l "$file" 2>/dev/null | awk '/LC_RPATH/{f=1;next} f&&/path /{print $2;f=0}')
                        ;;
                    "$dir"/lib/*)
                        # A from-source build stamps absolute build-dir paths
                        # as install names: re-anchor the reference inside the
                        # tree's own lib dir via @rpath.
                        install_name_tool -change "$ref" "@rpath/${ref#"$dir"/lib/}" "$file" 2>/dev/null || true
                        changed=1
                        ;;
                esac
            done < <(otool -L "$file" 2>/dev/null | awk 'NR>1 {print $1}' | grep -E "^(/opt/homebrew/|@loader_path/|@rpath/|@@HOMEBREW_PREFIX@@/|@@HOMEBREW_CELLAR@@/|$dir/lib/)" || true)
        done
        [ "$changed" = 1 ] || break
    done
    rm -f "$map"
    for file in "$dir"/bin/*; do
        [ -f "$file" ] || continue
        otool -L "$file" >/dev/null 2>&1 || continue
        install_name_tool -add_rpath "@executable_path/../lib" "$file" 2>/dev/null || true
    done
    for file in $(find "$libdir" -type f 2>/dev/null); do
        [ -f "$file" ] || continue
        macho_ok "$file" || continue
        install_name_tool -add_rpath "@loader_path" "$file" 2>/dev/null || true
        # A from-source build stamps absolute build-dir paths as install
        # names; re-anchor them inside the bundle.
        id="$(otool -D "$file" 2>/dev/null | sed -n 's/^current dylib: //p' || true)"
        case "$id" in
            @rpath/*|/usr/lib/*|/System/*) ;;
            *) install_name_tool -id "@rpath/${file#"$libdir"/}" "$file" 2>/dev/null || true ;;
        esac
    done
    # install_name_tool invalidates the code signatures that Apple requires
    # on arm64; re-sign ad-hoc after modifying.
    for file in "$dir"/bin/* $(find "$libdir" -type f 2>/dev/null); do
        [ -f "$file" ] || continue
        macho_ok "$file" || continue
        codesign --force --sign - "$file" 2>/dev/null || true
    done
}
vendor_dylibs "$BUILD/work/postgres"
# A from-source build stamps absolute build-dir paths into the binaries;
# nothing in the bundle may reference the build tree.
for f in "$BUILD/work/postgres"/bin/* $(find "$BUILD/work/postgres/lib" -type f 2>/dev/null); do
    [ -f "$f" ] || continue
    macho_ok "$f" || continue
    if otool -L "$f" 2>/dev/null | awk 'NR>1 {print $1}' | grep -F "$BUILD/" >/dev/null; then
        fail "PostgreSQL binary still references the build dir: $f"
    fi
done

# --- Redis ---------------------------------------------------------------------
echo "==> Building Redis ${REDIS_VERSION}"
curl -fSL --retry 3 --retry-delay 2 --retry-all-errors --progress-bar -o "$BUILD/downloads/redis.tar.gz" \
    "https://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz"
tar -xzf "$BUILD/downloads/redis.tar.gz" -C "$BUILD/downloads"
# -Wno-implicit-const-int-float-conversion silences a benign warning in
# Redis' timeout.c when built with recent Clang (Xcode 16+). The
# -mmacosx-version-min pin keeps the binary loadable on macOS >= MIN_MACOS
# even when built on a newer system; it must reach the link step too, which
# only sees LDFLAGS in Redis' Makefile.
make -C "$BUILD/downloads/redis-${REDIS_VERSION}" -j"$(sysctl -n hw.ncpu)" MALLOC=libc \
    CFLAGS="-Wno-implicit-const-int-float-conversion -mmacosx-version-min=$MIN_MACOS" \
    LDFLAGS="-mmacosx-version-min=$MIN_MACOS" >/dev/null
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
swiftc -O -target arm64-apple-macosx"$MIN_MACOS" -o "$APP/Contents/MacOS/eScriptoriumAgent" "$HERE/agent/EScriptoriumAgent.swift"

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
# The autobahn wheel ships a flatc CLI (FlatBuffers code generation) built
# for a newer macOS; eScriptorium never invokes it, so drop it to keep the
# bundle loadable on macOS >= MIN_MACOS.
rm -f "$BUNDLE_RES/python/lib/python3.${PY_MINOR}/site-packages/autobahn/_flatc/bin/flatc"

# --- Homebrew-linked Python extensions (pyvips, shapely/GEOS, ...) ------------
# Some wheels are built against Homebrew libraries via absolute paths, so they
# cannot load on a machine without Homebrew. Collect the referenced libraries,
# vendor the full closure, and rewrite the extension references to @rpath,
# which is resolved via an rpath added to the python binary.
echo "==> Vendoring Homebrew-linked libraries"
brew install --quiet vips geos gettext
PY_SITE_W="$BUILD/work/python/lib/python3.${PY_MINOR}/site-packages"
[ -d "$PY_SITE_W" ] || fail "python site-packages not found: $PY_SITE_W"
HBREW_LIB="$BUILD/work/hbrew/lib"
mkdir -p "$HBREW_LIB"
for so in $(find "$PY_SITE_W" \( -name '*.so' -o -name '*.dylib' \) -type f); do
    for ref in $(otool -L "$so" 2>/dev/null | awk 'NR>1 {print $1}' | grep '^/opt/homebrew' || true); do
        staged="$(hb_stage_path "$ref")"
        [ -n "$staged" ] && [ -e "$staged" ] || fail "wheel references Homebrew lib missing from staged prefix: $ref"
        if [ ! -e "$HBREW_LIB/$(basename "$ref")" ]; then
            cp "$staged" "$HBREW_LIB/"
            printf '%s\t%s\n' "$(basename "$ref")" "$staged" >> "$BUILD/work/hbrew/.dylibmap"
        fi
    done
done
# Normalize the ids of the directly copied seeds (vendor_dylibs only re-ids
# files it copies itself).
for f in "$HBREW_LIB"/*; do
    [ -f "$f" ] || continue
    case "$(otool -D "$f" 2>/dev/null | tail -1)" in
        /opt/homebrew/*|'@@HOMEBREW_PREFIX@@'/*|'@@HOMEBREW_CELLAR@@'/*) install_name_tool -id "@rpath/$(basename "$f")" "$f" ;;
    esac
done
if [ -n "$(ls -A "$HBREW_LIB")" ]; then
    vendor_dylibs "$BUILD/work/hbrew"
    mkdir -p "$BUNDLE_RES/hbrew"
    cp -R "$HBREW_LIB" "$BUNDLE_RES/hbrew/lib"
    PY_SITE="$BUNDLE_RES/python/lib/python3.${PY_MINOR}/site-packages"
    for so in $(find "$PY_SITE" \( -name '*.so' -o -name '*.dylib' \) -type f); do
        changed=0
        for ref in $(otool -L "$so" 2>/dev/null | awk 'NR>1 {print $1}' | grep '^/opt/homebrew' || true); do
            install_name_tool -change "$ref" "@rpath/$(basename "$ref")" "$so"
            changed=1
        done
        [ "$changed" = 1 ] && codesign --force --sign - "$so"
    done
    install_name_tool -add_rpath "@executable_path/../../hbrew/lib" "$BUNDLE_RES/python/bin/python3.${PY_MINOR}"
    codesign --force --sign - "$BUNDLE_RES/python/bin/python3.${PY_MINOR}"
fi
leftover=$(find "$BUNDLE_RES/python" \( -name '*.so' -o -name '*.dylib' \) -type f \
    -exec otool -L {} + 2>/dev/null | awk '{print $1}' | grep -E '^(/opt/homebrew|@@HOMEBREW_PREFIX@@|@@HOMEBREW_CELLAR@@)' | sort -u || true)
[ -z "$leftover" ] || fail "extensions still reference Homebrew: $leftover"
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

# --- compatibility audit -----------------------------------------------------------
# The bundle must load on macOS >= MIN_MACOS: fail if any Mach-O carries a
# higher minimum OS or references libSystem symbols that only exist on newer
# releases. The macOS 26 SDK added strchrnul/strrchrnul (glibc-compat); the
# sonoma-tier bottles already reference asprintf/vasprintf, so those exist
# since macOS 14 and are not listed here. Extend the list if a newer SDK
# adds more symbols that end up in vendored binaries.
echo "==> Auditing bundle for macOS $MIN_MACOS compatibility"
AUDIT_BAD=""
while IFS= read -r -d '' f; do
    file -b "$f" 2>/dev/null | grep -q '^Mach-O' || continue
    m="$(vtool -show "$f" 2>/dev/null | awk '/minos/{print $2; exit}')"
    [ -n "$m" ] || continue
    if awk -v a="$m" -v b="$MIN_MACOS" 'BEGIN { exit !(a + 0 > b + 0) }'; then
        AUDIT_BAD="$AUDIT_BAD $f(minos=$m)"
    fi
    if nm -u "$f" 2>/dev/null | grep -qxE '_?(strchrnul|strrchrnul)'; then
        AUDIT_BAD="$AUDIT_BAD $f(new-libSystem-symbols)"
    fi
done < <(find "$APP" -type f -print0)
[ -z "$AUDIT_BAD" ] || fail "bundle not compatible with macOS $MIN_MACOS:$AUDIT_BAD"

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
