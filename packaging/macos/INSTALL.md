# Installing and running eScriptorium on macOS (DMG)

User guide for the self-contained `eScriptorium.app` (Apple Silicon, macOS 13+).
The bundle includes everything it needs — a CPython 3.12 runtime with all
Python dependencies, PostgreSQL, Redis, and a JRE — so no prerequisites,
virtual environments, or Homebrew installation are required on the target
machine.

The app is currently **unsigned** (ad-hoc signed only: no Developer ID
certificate, no notarization). macOS Gatekeeper therefore blocks a downloaded
copy on its first launch. That is expected, not a broken build; see
[Running the unsigned app](#running-the-unsigned-app).

## Size

The DMG is about **1.3 GB**, and the installed app takes about **2.5 GB**.
Allow a few minutes for the download and for the copy into *Applications*.
The size also means that even a *successful* start takes some time: the
launcher first starts PostgreSQL, Redis, a Celery worker and the web server,
and only opens your browser once the web server actually answers. The
**first** start is the longest, because it additionally initializes the local
database, runs the migrations, and imports the bundled recognition model and
transcription fonts.

There is no window and no progress bar while this happens (the app runs in
the background), so just wait — and do not double-click the app a second time
while the first start is still running. A book icon appears in the macOS menu
bar as soon as eScriptorium is up; see [The system menu](#the-system-menu).

## Install the DMG

1. Download `eScriptorium-<VERSION_DATE>.dmg` from the release (for example
   from the *Build macOS installer* GitHub workflow, which attaches the DMG
   to a release).
2. Double-click the DMG. The *eScriptorium* volume opens and shows the
   eScriptorium app icon and an *Applications* folder icon.
3. Drag **eScriptorium** onto the **Applications** icon. This copies 2.5 GB
   and takes a while.
4. Eject the *eScriptorium* volume (or just close the Finder window).

## Running the unsigned app

macOS tags everything that arrived over the network with a *quarantine*
attribute, and Gatekeeper refuses the first launch of an unsigned app.
Unblock the app once, either of these ways:

1. **System Settings**: double-click *eScriptorium* in *Applications* —
   macOS refuses with an alert. Then open *System Settings → Privacy &
   Security*, scroll to the bottom, and in the *Security* section click
   **Open Anyway** next to "eScriptorium was blocked …". Double-click
   *eScriptorium* again; it now asks for confirmation one last time.
2. **Terminal**: remove the quarantine attribute:

   ```bash
   xattr -dr com.apple.quarantine /Applications/eScriptorium.app
   ```

After that, running the app is simply **double-clicking it in
/Applications** (or `open -a eScriptorium` in a terminal). The launcher:

1. creates `~/Library/Application Support/eScriptorium/` (all user data),
2. on first start only: initializes the PostgreSQL data directory, runs the
   migrations (the first migration creates the initial `admin` account:
   username `admin`, password `admin` — change it in the user settings once
   logged in), and imports the bundled recognition model *german_print* and
   the bundled transcription fonts,
3. starts Redis, PostgreSQL, a Celery worker and the web server,
4. opens `http://127.0.0.1:8000/` in the default browser once the web server
   answers (port 8000, falling back to 8001–8010 if busy), and
5. adds a book icon to the macOS menu bar (see below).

Because of the app's size, the browser window does not appear immediately —
wait until the launcher has finished (a few seconds for a warm start,
considerably longer for the very first start).

## The system menu

Once eScriptorium has started, a **book icon** appears in the macOS system
menu bar (top right, next to the clock). Clicking it opens a menu with:

- the current state — *eScriptorium is running* or *eScriptorium is
  stopped*,
- *Open eScriptorium* (only shown while running) — opens the web interface
  in the default browser,
- *Stop eScriptorium* / *Start eScriptorium* — stops or starts all local
  services,
- *Show logs* — opens the log folder in Finder
  (`~/Library/Application Support/eScriptorium/logs/`),
- *Quit eScriptorium* — removes the menu bar item. The services keep
  running; launch the app again (or use the terminal commands below) to get
  the menu item back.

The menu bar item survives *Stop eScriptorium* (so it can start the services
again) and removes itself when the data directory is deleted (e.g. by the
`reset` command).

## Terminal commands

The launcher is scriptable; most users will use the menu bar item instead.
The executable lives at `/Applications/eScriptorium.app/Contents/MacOS/eScriptorium`:

```bash
open -a eScriptorium                     # start (if needed) + open browser
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium start
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium stop
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium status
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium logs
/Applications/eScriptorium.app/Contents/MacOS/eScriptorium reset
```

`reset` deletes the entire data directory (database, uploads, models) and
asks for confirmation.
