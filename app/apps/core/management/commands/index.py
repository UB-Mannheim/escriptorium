from django.core.management.base import BaseCommand
from core.search import Indexer
from core.models import Project


class Command(BaseCommand):
    help = 'Index all projects by creating a DocumentPart wide transcription for each Document in each Project.'
        
    def handle(self, *args, **options):
        for project in Project.objects.all():
            indexer = Indexer(project)
            indexer.configure()
            indexer.process()
