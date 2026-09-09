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
                channel.release()
    except Exception:
        logger.warning('Could not inspect the broker queues.', exc_info=True)
        return None


class Command(BaseCommand):
    help = ("Mark TaskReports as crashed when their Celery task is gone: "
            "'Running' reports whose task is no longer running, and 'Queued' "
            "reports whose task is neither in a queue nor in a worker "
            "anymore (e.g. the message was consumed and lost).")

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
            help='only clean up Queued reports that are at least this many '
                 'seconds old (default: 60)'
        )

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        logger.setLevel(self.verbosity_map[verbosity])
        count = self.cleanup_running()
        count += self.cleanup_queued(min_age=options['min_age'])
        logger.info(f'Cleaned up {count} ghost tasks.')

    def cleanup_running(self):
        count = 0
        for report in TaskReport.objects.filter(workflow_state=TaskReport.WORKFLOW_STATE_STARTED):
            if not report.check_process_running():
                logger.debug('Cleaning up task %d : %s.' % (report.id, report.task_id))
                report.workflow_state = TaskReport.WORKFLOW_STATE_ERROR
                report.save()
                count += 1
        return count

    def cleanup_queued(self, min_age=60):
        count = 0
        reports = TaskReport.objects.filter(workflow_state=TaskReport.WORKFLOW_STATE_QUEUED)
        if not reports:
            return count
        active = worker_task_ids()
        queued = queued_task_ids()
        if active is None or queued is None:
            # We cannot tell which tasks are still alive, and cleaning up
            # would risk marking live tasks as crashed.
            logger.warning('Cannot determine which tasks are still alive; '
                           'not cleaning up Queued reports.')
            return count
        live = active | queued
        now = timezone.now()
        for report in reports:
            if (now - report.queued_at).total_seconds() < min_age:
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
