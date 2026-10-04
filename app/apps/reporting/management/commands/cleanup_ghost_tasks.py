import json
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from escriptorium.celery import app
from reporting.models import TaskReport

logger = logging.getLogger(__name__)


def worker_task_ids(timeout=5.0):
    """Task ids currently active or reserved on any worker.

    Returns a set of task ids, or None if the workers cannot be asked.
    """
    try:
        inspector = app.control.inspect(timeout=timeout)
        ids = set()
        for method in ('active', 'reserved'):
            for tasks in (getattr(inspector, method)() or {}).values():
                ids.update(task['id'] for task in tasks if task.get('id'))
        return ids
    except Exception:
        logger.warning('Could not ask workers for active/reserved tasks.', exc_info=True)
        return None


def queued_task_ids():
    """Task ids whose message is still in one of the Celery queues.

    Only a Redis broker is supported; returns None otherwise.
    """
    if not settings.CELERY_BROKER_URL.lower().startswith('redis'):
        return None
    try:
        with app.broker_connection() as connection:
            channel = connection.channel()
            try:
                client = channel.client
                ids = set()
                for queue in settings.CELERY_TASK_QUEUES:
                    for payload in client.lrange(queue.name, 0, -1):
                        if isinstance(payload, (bytes, bytearray)):
                            payload = payload.decode('utf-8', 'replace')
                        ids.add(json.loads(payload)['headers']['id'])
                return ids
            finally:
                channel.close()
    except Exception:
        logger.warning('Could not inspect the broker queues.', exc_info=True)
        return None


class Command(BaseCommand):
    help = ("Mark TaskReports as crashed when their Celery task is gone. "
            "A 'Running' report is reaped when its task is no longer active or "
            "reserved on any worker; a 'Queued' report is reaped when its task is "
            "neither in a queue nor in a worker anymore (e.g. the message was "
            "consumed and lost). Reports younger than --min-age are left alone, "
            "and nothing is reaped if the workers or the broker cannot be asked.")

    verbosity_map = [
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-age',
            type=int,
            default=60,
            help='only clean up reports that are at least this many seconds old, '
                 'measured from when the task started (Running) or was queued '
                 '(Queued) (default: 60)'
        )

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        logger.setLevel(self.verbosity_map[verbosity])
        min_age = options['min_age']
        # Only talk to the workers when there is actually something to check.
        active = None
        if TaskReport.objects.filter(
                workflow_state__in=(TaskReport.WORKFLOW_STATE_STARTED,
                                    TaskReport.WORKFLOW_STATE_QUEUED)).exists():
            active = worker_task_ids()
        count = self.cleanup_running(active, min_age=min_age)
        count += self.cleanup_queued(active, min_age=min_age)
        logger.info(f'Cleaned up {count} ghost tasks.')

    @staticmethod
    def _reference_time(report):
        # When the task started for Running reports, when it was queued otherwise.
        return report.started_at or report.queued_at

    def cleanup_running(self, active, min_age=60):
        count = 0
        reports = TaskReport.objects.filter(workflow_state=TaskReport.WORKFLOW_STATE_STARTED)
        if not reports:
            return count
        if active is None:
            # We cannot tell which tasks are still alive; reaping would risk
            # marking a live task as crashed.
            logger.warning('Cannot determine which tasks are still alive; '
                           'not cleaning up Running reports.')
            return count
        now = timezone.now()
        for report in reports:
            if (now - self._reference_time(report)).total_seconds() < min_age:
                continue
            if report.task_id and report.task_id in active:
                continue
            logger.debug('Cleaning up task %d : %s.' % (report.id, report.task_id))
            report.error(
                f'Celery task {report.task_id or "<unknown>"} is no longer active on any worker; '
                f'marked as crashed by cleanup_ghost_tasks.'
            )
            count += 1
        return count

    def cleanup_queued(self, active, min_age=60):
        count = 0
        reports = TaskReport.objects.filter(workflow_state=TaskReport.WORKFLOW_STATE_QUEUED)
        if not reports:
            return count
        if active is None:
            logger.warning('Cannot determine which tasks are still alive; '
                           'not cleaning up Queued reports.')
            return count
        queued = queued_task_ids()
        if queued is None:
            logger.warning('Cannot determine which tasks are still queued; '
                           'not cleaning up Queued reports.')
            return count
        live = active | queued
        now = timezone.now()
        for report in reports:
            if (now - self._reference_time(report)).total_seconds() < min_age:
                continue
            if report.task_id and report.task_id in live:
                continue
            logger.debug('Cleaning up task %d : %s.' % (report.id, report.task_id))
            report.error(
                f'Celery task {report.task_id or "<unknown>"} is no longer in a queue or a worker; '
                f'marked as crashed by cleanup_ghost_tasks.'
            )
            count += 1
        return count
