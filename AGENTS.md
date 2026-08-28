# Agents

This document provides AI coding assistants with project-specific conventions and context for the eScriptorium codebase.

## Project overview

- **Django 4.2 LTS** monolith with **Django REST Framework 3.15**
- **Celery 5.3** with Redis broker for async tasks
- **Vue.js 2** + Vuex 3 frontend, built with Webpack 5 (legacy `front/src` and newer `front/vue` share one webpack build, entries in `front/webpack.common.js`)
- **PostgreSQL 15**, Redis cache and broker
- OCR engine: **Kraken** (Python library)
- Full-text search via **opensearch-py** (works with Elasticsearch and OpenSearch backends)

## Architecture

Custom apps live in `app/apps/`, added to `sys.path` so imports are `core.models`, not `apps.core.models`:

- `core/` — Main business logic: models, tasks, views
- `api/` — DRF endpoints, serializers, viewsets
- `reporting/` — Celery task tracking via TaskReport model
- `users/` — Custom User model
- `imports/` — Document import/export (ALTO, PageXML, METS)
- `versioning/` — JSONB-based model versioning

## Branch-specific: local_settings.py is tracked

On this branch `app/escriptorium/local_settings.py` is a **committed file**
containing the UB Mannheim production configuration (it is normally
git-ignored upstream). Do not assume it is absent or regenerate it.

## Running tests

Use Django's test runner (no pytest):

```bash
cd app
../venv3.12/bin/python manage.py test -v 2 <test_target> --keepdb
```

Test settings are in `app/escriptorium/test_settings.py` (loaded automatically in tests). Key settings:
- `CELERY_TASK_ALWAYS_EAGER = True` — tasks run synchronously
- `CACHES` uses `LocMemCache` — cache works in-process but is not shared across processes
- Migrations are disabled via `DisableMigrations`
- Media root is `test_media/`

### Gotchas

- Always import `reporting.tasks` (start_task_reporting, end_task_reporting) in any module that defines Celery tasks, otherwise TaskReport objects won't be created
- The `DisableMigrations` class in test_settings means the test DB is created from `syncdb`, not migrations — schema must match the models exactly
- `on_commit` callbacks work in tests (`TransactionTestCase`), but `self.pk` is set to `None` by `Collector.delete()` before the callback fires — always capture `pk` in a local variable

## Celery task patterns

Tasks use `@shared_task(autoretry_for=(MemoryError,), default_retry_delay=...)` and typically accept `instance_pk=None, user_pk=None, **kwargs`.

Task routing via `CELERY_TASK_ROUTES` to named queues: `default`, `live`, `low-priority`, `gpu`, `jvm`, `intensive-inference`.

## Code conventions

- **Models**: PascalCase (e.g. `DocumentPart`), fields are snake_case
- **Tests**: `CoreFactoryTestCase(TransactionTestCase)` with `self.factory` helper; test methods are `test_*` snake_case
- **Imports**: isort with `profile=black`; known first-party: `api,core,imports,reporting,users,versioning,escriptorium`
- **Linting**: flake8 (max-line-length=120), codespell, pre-commit hooks
- **Strings**: `gettext_lazy` for user-facing strings; no hardcoded English in model metadata
- **DRF serializers**: ModelSerializer with explicit fields; use `create()`/`update()` overrides for related object creation
- No explanatory comments in code unless the logic is non-obvious

## Internationalization

English is the source language; catalogs exist only for `de`, `es`, `fr` (there is deliberately no `en` catalog).

```bash
cd app
../venv3.12/bin/python manage.py makemessages -l de -l es -l fr --add-location file
```

Do **not** use `--all`: it also writes a catalog for the source language
`en`. After running, review the diff: resolve fuzzy entries (msgmerge
sometimes matches new strings against unrelated previous ones via `#|`
comments) and delete `#~` obsolete entries before committing.

## Frontend

- Frontend dependencies live in `front/package.json` + `front/package-lock.json`; install with `npm ci --prefix front` (or `npm upgrade` to refresh within semver ranges, then commit the new lock file)
- Builds: `npm run build --prefix front` (dev), `npm run production --prefix front` (deploy)
- Jest: `npm test --prefix front` — two suites (`store/lines.spec.js`, `components/ImportImagesForm.spec.js`) fail to load under jsdom because `document.currentScript` is null at module load in `front/src/scriptname.js`; this is a known, pre-existing limitation

### Non-root / subpath installation

eScriptorium supports deployment under a URL prefix (e.g. `/escriptorium/`).

- Django: `FORCE_SCRIPT_NAME` prefixes all URLs. On this branch the derived
  settings (`STATIC_URL`, `MEDIA_URL`, login/logout redirect) live in the
  tracked `local_settings.py`, not in `settings.py`.
- Frontend: the legacy app sets `axios.defaults.baseURL = SCRIPT_NAME + '/api'`
  (`SCRIPT_NAME` is derived from the static file URL in
  `front/src/scriptname.js`). New Vue components/pages must follow the same
  pattern — **never use root-absolute paths** (`/api/...`, `href="/..."`,
  `action="/..."`); prefix them with `SCRIPT_NAME` (import from
  `../../../src/scriptname.js`) or use the `url()` helper in
  `GlobalNavigation.vue`.
- Webpack: `publicPath` is `process.env.STATIC_URL || "/static/"`. For a
  subpath deployment, build with `STATIC_URL=/escriptorium/static/ npm run production --prefix front` so asset URLs inside the bundles (e.g. fonts) carry the prefix.
- Static serving: Django serves static files only while `DEBUG=True`
  (`static()` patterns in `urls.py`). With `DEBUG=False` the web server must
  serve them, e.g.:
  ```nginx
  location /escriptorium/static/ {
      alias /opt/escriptorium/app/static/;
  }
  location /escriptorium/media/ {
      alias /opt/escriptorium/app/media/;
  }
  location /escriptorium/ {
      proxy_pass http://127.0.0.1:8000;
  }
  ```

### Search settings naming

`ES` in setting names means **eScriptorium** (not Elasticsearch):
`DISABLE_ES_SEARCH`, `ES_SEARCH_URL`, `ES_SEARCH_COMMON_INDEX`. Keep the
variable name and the environment variable key identical when renaming.

## Preparing a production release

Workflow for integrating a new upstream release into this branch:

1. **Rebase on upstream**: fetch `scripta`, then `git rebase scripta/develop`
   (or on a local branch that stacks pending changes on top of it, e.g.
   `opensearch`). Recurring conflict points: `app/requirements.txt` (keep
   the local pins: `pyvips~=2.1`, unpinned `celery` for passim,
   `opensearch-py` instead of `elasticsearch`), templates, and
   `local_settings.py`.
2. **Audit new frontend code for subpath compatibility**: upstream adds Vue
   components regularly — check them for root-absolute paths (`href="/"`,
   `action="/"`, `"/api/...`) and prefix them with `SCRIPT_NAME` (see
   "Non-root / subpath installation" above).
3. **Update translations**: `makemessages -l de -l es -l fr --add-location file`
   (see "Internationalization"), resolve fuzzy entries, translate new
   strings, drop `#~` obsolete entries, commit the catalogs.
4. **Update frontend dependencies**: `npm upgrade --prefix front`, commit
   the new `front/package-lock.json` (fold repeated lockfile-only commits
   into one), and verify `npm run production --prefix front` builds.
5. **Run the test suite**: `./run_tests.sh` (repo root; sets `JAVA_HOME`
   and Spark loopback args for passim/seriatim), i.e.
   `manage.py test -v 2 users api versioning imports core escriptorium --keepdb`.
6. **Bump `VERSION_DATE`**: set `VERSION_DATE = 'UBMA-<YYYY-MM-DD>'` in
   `app/escriptorium/local_settings.py` as a fresh commit on top; do not
   amend or stack older `Update VERSION_DATE` commits.

## Git conventions

Conventional commits: `type(scope): description` where type is `feat`, `fix`, `chore`, `refactor`, `test`, `docs`.

Pushing (especially force-pushing) is only done when explicitly asked.

Commit messages must include:
```
Assisted-by: OpenCode / <model name> (<vendor>)
Signed-off-by: Stefan Weil <sw@weilnetz.de>
```
