import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from escriptorium.utils import send_email
from users.models import MEGABYTES_TO_BYTES, QuotaEvent, User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send quotas alerts to users by email.'

    def handle(self, *args, **options):
        if settings.DISABLE_QUOTAS:
            logger.info('Quotas are disabled on this instance, no need to run this command')
            return

        for user in User.objects.all():
            has_disk_storage = user.has_free_disk_storage()
            has_cpu_minutes = user.has_free_cpu_minutes()
            has_gpu_minutes = user.has_free_gpu_minutes()

            if has_disk_storage and has_cpu_minutes and has_gpu_minutes:
                continue

            disk_storage_usage = user.calc_disk_usage()
            cpu_minutes_usage = user.calc_cpu_usage()
            gpu_minutes_usage = user.calc_gpu_usage()
            events = QuotaEvent.objects.filter(
                user=user,
                reached_disk_storage=None if has_disk_storage else disk_storage_usage / MEGABYTES_TO_BYTES,
                reached_cpu=None if has_cpu_minutes else cpu_minutes_usage,
                reached_gpu=None if has_gpu_minutes else gpu_minutes_usage,
                sent=True,
                created__gte=date.today() - timedelta(days=settings.QUOTA_NOTIFICATIONS_TIMEOUT)
            )

            reached = [
                None if has_disk_storage else _('Disk storage'),
                None if has_cpu_minutes else _('CPU minutes'),
                None if has_gpu_minutes else _('GPU minutes'),
            ]
            reached = [x for x in reached if x]

            if events:
                reached = ', '.join(reached)
                logger.info(f'The user {user.pk} reached his following quotas: {reached}. An email was already send less than {settings.QUOTA_NOTIFICATIONS_TIMEOUT} days ago.')
                continue

            event = QuotaEvent.objects.create(
                user=user,
                reached_disk_storage=None if has_disk_storage else disk_storage_usage / MEGABYTES_TO_BYTES,
                reached_cpu=None if has_cpu_minutes else cpu_minutes_usage,
                reached_gpu=None if has_gpu_minutes else gpu_minutes_usage
            )

            send_email(
                'users/email/quotas_reached_subject.txt',
                'users/email/quotas_reached_message.txt',
                'users/email/quotas_reached_html.html',
                (user.email,),
                context={'user': user, 'reached': reached},
                result_interface=('users', 'QuotaEvent', event.id)
            )
