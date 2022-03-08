import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk as es_bulk

from core.models import Project

logger = logging.getLogger('es_indexing')


class Command(BaseCommand):
    help = "Index projects by creating one ElasticSearch document for each LineTranscription."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-pks",
            nargs="+",
            type=int,
            help="Specify a few project PKs to index. If unset, all projects will be indexed by default.",
        )
        parser.add_argument(
            "--document-pks",
            nargs="+",
            type=int,
            help="Specify a few document PKs to index. If unset, all documents will be indexed by default.",
        )
        parser.add_argument(
            "--part-pks",
            nargs="+",
            type=int,
            help="Specify a few part PKs to index. If unset, all parts will be indexed by default.",
        )

    def handle(self, *args, **options):
        if settings.DISABLE_ELASTICSEARCH:
            logger.error("Please set the DISABLE_ELASTICSEARCH Django setting to 'False' to use this command.")
            return

        self.es_client = Elasticsearch(hosts=[settings.ELASTICSEARCH_URL])
        if not self.es_client.ping():
            logger.error(
                f"Unable to connect to Elasticsearch host defined as {settings.ELASTICSEARCH_URL}."
            )
            return

        # Creating the common index if it doesn't exist
        indices = IndicesClient(self.es_client)
        if not indices.exists(settings.ELASTICSEARCH_COMMON_INDEX):
            indices.create(settings.ELASTICSEARCH_COMMON_INDEX)
            logger.info(f"Created a new index named {settings.ELASTICSEARCH_COMMON_INDEX}")

        extras = {}
        # Index all projects by default
        projects = Project.objects.all()

        # Only index selected projects if the project-pks flag is given
        if options.get("project_pks") is not None:
            projects = projects.filter(pk__in=options["project_pks"])

        # Only index selected documents if the document-pks flag is given
        if options.get("document_pks") is not None:
            extras["filter_documents"] = options["document_pks"]
            projects = projects.filter(documents__in=options["document_pks"])

        # Only index selected parts if the part-pks flag is given
        if options.get("part_pks") is not None:
            extras["filter_parts"] = options["part_pks"]
            projects = projects.filter(documents__parts__in=options["part_pks"])

        logger.info("\n" + "-" * 50 + "\n")
        for project in projects.distinct():
            self.index_project(project, **extras)

    def index_project(self, project, filter_documents=None, filter_parts=None):
        logger.info(f"Indexing project {project.name} (PK={project.pk})...")

        documents = project.documents.filter(pk__in=filter_documents) if filter_documents else project.documents.all()
        for document in documents:
            logger.info(f" - Processing the document {document.name} (PK={document.pk})...")

            total_inserted = 0
            parts = document.parts.filter(pk__in=filter_parts) if filter_parts else document.parts.all()
            for part in parts:
                total_inserted += self.ingest_document_part(project, document, part)

            logger.info(f"   Inserted {total_inserted} new entries in index {settings.ELASTICSEARCH_COMMON_INDEX}\n")

        logger.info(f"Project {project.name} (PK={project.pk}) was successfully indexed")
        logger.info("\n" + "-" * 50 + "\n")

    def ingest_document_part(self, project, document, part):
        to_insert = [
            {
                "_index": settings.ELASTICSEARCH_COMMON_INDEX,
                "_id": f"{line_transcription.id}",
                "project_id": project.id,
                "document_id": document.id,
                "document_part_id": part.id,
                "transcription_id": line_transcription.transcription.id,
                "content": line_transcription.content,
            }
            for line in part.lines.all()
            for line_transcription in line.transcriptions.all()
        ]
        to_insert = [entry for entry in to_insert if entry["content"]]

        nb_inserted, _ = es_bulk(self.es_client, to_insert, stats_only=True)
        return nb_inserted
