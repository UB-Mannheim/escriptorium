#!/bin/sh
# Rebuild the frontend bundle and force-refresh everything that can cache it.
#
# Why this is needed: webpack.common.js emits fixed filenames (main.js, vendor.js, ...)
# with no content hash, and the frontend is baked into the app image at build time
# (root Dockerfile, frontend stage) rather than volume-mounted. So after editing
# anything under front/, three layers of cache can serve the old code: the docker
# image, the static/ volume collectstatic writes into, and the browser cache (since
# the JS/CSS URLs never change). This script clears all three.
set -e

cd "$(dirname "$0")/.."

echo "==> Rebuilding app image (recompiles front/ via webpack)"
docker compose build web

echo "==> Recreating app containers with the new image"
docker compose up -d --force-recreate web channelserver celery-main celery-live celery-low-priority

echo "==> Restarting nginx (it caches the web/channelserver upstream IPs at startup,"
echo "    which change when those containers are recreated -- otherwise you get a 502)"
docker compose restart nginx

echo "==> Re-collecting static files with --clear to drop stale assets from the static/ volume"
docker compose exec web python manage.py collectstatic --no-input --clear

echo "==> Checking that all expected services are running"
services="web channelserver db redis nginx celery-main celery-live celery-low-priority celery-gpu flower mail"
down=""
for svc in $services; do
  state=$(docker compose ps --format '{{.State}}' "$svc" 2>/dev/null)
  if [ "$state" != "running" ]; then
    down="$down $svc"
  fi
done
if [ -n "$down" ]; then
  echo "==> WARNING: these services are not running:$down"
  docker compose ps
else
  echo "==> All services running."
fi

echo "==> Done. Hard-refresh your browser (or open in a private window) -- filenames are not"
echo "    content-hashed, so the browser cache will otherwise keep serving the old JS/CSS."
