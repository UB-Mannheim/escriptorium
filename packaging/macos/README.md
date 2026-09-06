# macOS bundle (Apple Silicon)

Self-contained `eScriptorium.app` that runs the full stack locally without
any prerequisites: bundled CPython 3.12 with all Python dependencies,
PostgreSQL 18, Redis, and a Temurin JRE (for passim text alignment).

## Build

Prerequisites on the build machine: Apple Silicon macOS 13+, Xcode command
line tools, Homebrew, Node.js >= 20, `curl`, `jq`.

```bash
packaging/macos/build.sh            # build .app and .dmg
packaging/macos/build.sh --test     # additionally smoke-test the result
```

Outputs (in `packaging/macos/build/`):

- `eScriptorium.app`
- `eScriptorium-<VERSION_DATE>.dmg`

`VERSION_DATE` defaults to `UBMA-` plus the base upstream release
(`git describe --tags --abbrev=0`, e.g. `UBMA-v26.07`) and is shown on the
start page; override it via the environment:

```bash
VERSION_DATE=UBMA-v26.07 packaging/macos/build.sh
```

The build downloads the Python runtime, the JRE and the Redis source,
installs PostgreSQL 18 via Homebrew, and runs `npm ci`/`npm run production`
in `front/`. Budget a few GB of disk and a few minutes.

### Building on GitHub

The "Build macOS installer" workflow (`.github/workflows/build-macos.yml`)
can be triggered manually from the *Actions* tab. It runs the same build
on an Apple Silicon runner and attaches the resulting `.dmg` to a release
(named `macos-<sha>-<run>`), from which it can be downloaded directly.
(GitHub *artifacts* are always delivered as a zip, so a release asset is
used instead.) The optional *version* input overrides `VERSION_DATE`.

## Install (users)

Get the `eScriptorium-<VERSION_DATE>.dmg` from the release, open it and drag
*eScriptorium* onto the *Applications* folder icon. The DMG is about 1.3 GB;
the installed app takes about 2.5 GB.

The app is currently **unsigned** and **not notarized**, so macOS
Gatekeeper blocks it on first launch. After dragging it to
`/Applications`, unblock it one of these ways:

1. Double-click it once (Gatekeeper refuses), then open
   *System Settings → Privacy & Security*, scroll to the bottom and click
   *"eScriptorium was blocked … Open Anyway"*, then double-click again.
2. Or in a terminal:

   ```bash
   xattr -dr com.apple.quarantine /Applications/eScriptorium.app
   ```

Then double-click *eScriptorium*. On first start the launcher:

1. creates `~/Library/Application Support/eScriptorium/` (all user data),
2. initializes the local PostgreSQL data directory,
3. runs migrations (the first migration creates the initial `admin`
   account: username `admin`, password `admin` — change it in the user
   settings once logged in),
4. imports the bundled recognition model *german_print* (public, owned by
   `admin`) if no recognition model exists yet,
5. starts Redis, PostgreSQL, a Celery worker and the web server,
6. opens `http://127.0.0.1:8000/` in the default browser,
7. adds a menu bar (status bar) item for stopping the services.

Out of the box you can run OCR: line segmentation uses the default model
bundled with Kraken, and recognition uses *german_print*
([Zenodo 10519596](https://zenodo.org/records/10519596)), a generic model
for German and Latin prints (15th–20th century). More models can be
downloaded from the [HTR-MoPo catalog](https://htrmopo.inria.fr/catalog)
and uploaded via the *Models* page.

## Menu bar

While running, eScriptorium shows a book icon in the macOS menu bar. Its
menu offers:

- the current state (*running* / *stopped*),
- *Open eScriptorium* — opens the web interface in the browser,
- *Stop eScriptorium* / *Start eScriptorium*,
- *Show logs* — opens the log folder in Finder,
- *Quit eScriptorium* — removes the menu bar item.

The menu bar item survives *Stop* (so it can start the services again) and
removes itself when the data directory is deleted (e.g. by *reset*).

## Commands

The launcher is scriptable from the terminal; most users will use the menu
bar item instead:

```bash
open -a eScriptorium                    # start (if needed) + open browser
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium start
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium stop
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium status
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium logs
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium reset
```

`reset` deletes the entire data directory (database, uploads, models).

## Ports

| Service | Port |
| --- | --- |
| Web (Django, HTTP + WebSocket) | 8000 (falls back to 8001–8010 if busy) |
| PostgreSQL | 5433 |
| Redis | 6380 |

The web server binds to `127.0.0.1` only. Fatal startup problems (a
port already in use, a failing migration, …) are shown as a macOS alert
when the app was double-clicked, and always logged to
`~/Library/Application Support/eScriptorium/logs/launcher.log`.

## Updating

All user data (database, media uploads, trained models) lives in
`~/Library/Application Support/eScriptorium/`, outside the app bundle.
To update, replace `eScriptorium.app` in `/Applications` with the new
version; the next start reuses the existing data directory and runs any
pending migrations.

## Design notes

- The bundle serves the app with `manage.py runserver` (ASGI, since
  `ASGI_APPLICATION` is set) with `DEBUG=True`; there is no uwsgi/nginx in
  the bundle.
- User data is kept out of the `.app` via the `MEDIA_ROOT`, `STATIC_ROOT`
  and `LOG_FILE` environment overrides in `settings.py`.
- PostgreSQL is vendored from the Homebrew keg; `build.sh` rewrites its
  dylib install names (`@rpath`) so no Homebrew installation is needed on
  the target machine.
- Text alignment (`TEXT_ALIGNMENT=True`) is enabled and a JRE is bundled;
  remove the JRE step and set the env var in the launcher to disable it.
- Kraken OCR training and inference run on the Apple GPU (PyTorch MPS) by
  default; set `ESCR_KRAKEN_DEVICE=cpu` (before starting) to force CPU.
- The app icon is generated at build time from
  `app/escriptorium/static/images/escriptorium_hd.png` via `sips`/`iconutil`.
- The *german_print* recognition model (Zenodo 10519596) is downloaded at
  build time (cached in `.cache/models/`), bundled in `Resources/models/`,
  and imported on first start if no recognition model exists yet.
- The bundle runs with trust authentication on a localhost-only PostgreSQL
  instance — acceptable for a single-user local tool, not for network use.
