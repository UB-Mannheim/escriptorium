from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.tests.factory import CoreFactory
from reporting.models import TaskReport


class DownloadsPageTestCase(TestCase):
    def setUp(self):
        self.factory = CoreFactory()
        self.user = self.factory.make_user()

    def test_downloads_page_renders(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('downloads'))
        self.assertEqual(resp.status_code, 200)


class CleanupGhostTasksTestCase(TestCase):
    def setUp(self):
        self.factory = CoreFactory()
        self.user = self.factory.make_user()

    def make_report(self, task_id, workflow_state, age_seconds=0):
        report = TaskReport.objects.create(
            user=self.user,
            label='Test report',
            task_id=task_id,
            method='core.tasks.test_task',
            workflow_state=workflow_state,
        )
        if age_seconds:
            TaskReport.objects.filter(pk=report.pk).update(
                queued_at=timezone.now() - timedelta(seconds=age_seconds)
            )
        return report

    def run_command(self):
        call_command('cleanup_ghost_tasks', verbosity=0)

    def test_running_report_cleaned_when_process_gone(self):
        report = self.make_report('task-running', TaskReport.WORKFLOW_STATE_STARTED)
        with patch.object(TaskReport, 'check_process_running', return_value=False):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_ERROR)

    def test_running_report_kept_when_process_running(self):
        report = self.make_report('task-running', TaskReport.WORKFLOW_STATE_STARTED)
        with patch.object(TaskReport, 'check_process_running', return_value=True):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_STARTED)

    def test_queued_report_cleaned_when_task_lost(self):
        report = self.make_report('task-lost', TaskReport.WORKFLOW_STATE_QUEUED, age_seconds=120)
        with patch('reporting.management.commands.cleanup_ghost_tasks.worker_task_ids', return_value=set()), \
                patch('reporting.management.commands.cleanup_ghost_tasks.queued_task_ids', return_value=set()):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_ERROR)
        self.assertIsNotNone(report.done_at)
        self.assertIn('cleanup_ghost_tasks', report.messages)

    def test_queued_report_kept_when_task_is_in_queue(self):
        report = self.make_report('task-in-queue', TaskReport.WORKFLOW_STATE_QUEUED, age_seconds=120)
        with patch('reporting.management.commands.cleanup_ghost_tasks.worker_task_ids', return_value=set()), \
                patch('reporting.management.commands.cleanup_ghost_tasks.queued_task_ids', return_value={'task-in-queue'}):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_QUEUED)

    def test_queued_report_kept_when_task_is_in_worker(self):
        report = self.make_report('task-in-worker', TaskReport.WORKFLOW_STATE_QUEUED, age_seconds=120)
        with patch('reporting.management.commands.cleanup_ghost_tasks.worker_task_ids', return_value={'task-in-worker'}), \
                patch('reporting.management.commands.cleanup_ghost_tasks.queued_task_ids', return_value=set()):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_QUEUED)

    def test_queued_report_kept_when_liveness_unknown(self):
        report = self.make_report('task-unknown', TaskReport.WORKFLOW_STATE_QUEUED, age_seconds=120)
        with patch('reporting.management.commands.cleanup_ghost_tasks.worker_task_ids', return_value=None), \
                patch('reporting.management.commands.cleanup_ghost_tasks.queued_task_ids', return_value=set()):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_QUEUED)

    def test_queued_report_kept_when_younger_than_min_age(self):
        report = self.make_report('task-fresh', TaskReport.WORKFLOW_STATE_QUEUED)
        with patch('reporting.management.commands.cleanup_ghost_tasks.worker_task_ids', return_value=set()), \
                patch('reporting.management.commands.cleanup_ghost_tasks.queued_task_ids', return_value=set()):
            self.run_command()
        report.refresh_from_db()
        self.assertEqual(report.workflow_state, TaskReport.WORKFLOW_STATE_QUEUED)
