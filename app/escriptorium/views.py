"""
Health endpoints for container orchestration and monitoring.

`health` is a dependency-free liveness probe: it answers as soon as Django can
serve a request, and is what the docker-compose healthchecks poll.

`health_ready` is a readiness probe that actually exercises the backing
services. It is restricted to internal callers in nginx.conf, since it reports
on the state of our dependencies.
"""
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

# keep a failing check from bloating the response with a whole traceback
ERROR_MAX_LENGTH = 200


@require_safe
@never_cache
def health(request):
    """Liveness: no database, no cache, no broker. Just 'the app is serving'."""
    return JsonResponse({'status': 'ok'})


def check_database():
    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT 1')


def check_cache():
    try:
        from django_redis import get_redis_connection
        connection = get_redis_connection('default')
    except (ImportError, NotImplementedError, AttributeError):
        # not a redis backend (locmem or dummy, as in the test settings):
        # fall back to exercising whatever backend is configured
        cache.set('healthcheck', 'ok', 5)
        cache.get('healthcheck')
    else:
        connection.ping()


def check_celery_broker():
    # reachability of the broker only; deliberately not app.control.ping(),
    # which polls the workers and is both slow and flaky
    from escriptorium.celery import app
    with app.connection() as connection:
        connection.ensure_connection(max_retries=0, timeout=2)


@require_safe
@never_cache
def health_ready(request):
    """Readiness: report on each backing service, 503 if any of them is down."""
    checks = {
        'database': check_database,
        'cache': check_cache,
        'celery_broker': check_celery_broker,
    }

    results = {}
    for name, check in checks.items():
        try:
            check()
        except Exception as e:
            results[name] = str(e)[:ERROR_MAX_LENGTH] or repr(e)[:ERROR_MAX_LENGTH]
        else:
            results[name] = 'ok'

    healthy = all(result == 'ok' for result in results.values())
    return JsonResponse({
        'status': 'ok' if healthy else 'error',
        'checks': results,
    }, status=200 if healthy else 503)
