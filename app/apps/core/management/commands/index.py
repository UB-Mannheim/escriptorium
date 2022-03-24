import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db.models import Q
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk as es_bulk

from core.models import Project
from users.models import User

logger = logging.getLogger("es_indexing")
logger.setLevel(logging.ERROR)


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
        if options["verbosity"] > 1:
            logger.setLevel(logging.INFO)

        if settings.DISABLE_ELASTICSEARCH:
            logger.error(
                "Please set the DISABLE_ELASTICSEARCH Django setting to 'False' to use this command."
            )
            return

        self.es_client = Elasticsearch(hosts=[settings.ELASTICSEARCH_URL])
        if not self.es_client.ping():
            logger.error(
                f"Unable to connect to Elasticsearch host defined as {settings.ELASTICSEARCH_URL}."
            )
            return

        # Creating the common index if it doesn't exist
        indices = IndicesClient(self.es_client)
        if not indices.exists(index=settings.ELASTICSEARCH_COMMON_INDEX):
            indices.create(index=settings.ELASTICSEARCH_COMMON_INDEX)
            logger.info(
                f"Created a new index named {settings.ELASTICSEARCH_COMMON_INDEX}"
            )

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
            try:
                self.index_project(project, **extras)
            except Exception as e:
                logger.error(f"Failed to index project {project.pk} because: {e}")

    def index_project(self, project, filter_documents=None, filter_parts=None):
        logger.info(f"Indexing project {project.name} (PK={project.pk})...")

        documents = (
            project.documents.filter(pk__in=filter_documents)
            if filter_documents
            else project.documents.all()
        )
        for document in documents:
            logger.info(
                f" - Processing the document {document.name} (PK={document.pk})..."
            )

            # Retrieve users that have a read access on this document
            allowed_users = self.retrieve_allowed_users(project, document)

            total_inserted = 0
            parts = (
                document.parts.filter(pk__in=filter_parts)
                if filter_parts
                else document.parts.all()
            )
            for part in parts:
                try:
                    total_inserted += self.ingest_document_part(
                        project, document, part, allowed_users
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to index part {part.pk} on project {project.pk} because: {e}"
                    )

            logger.info(
                f"   Inserted {total_inserted} new entries in index {settings.ELASTICSEARCH_COMMON_INDEX}\n"
            )

        logger.info(
            f"Project {project.name} (PK={project.pk}) was successfully indexed"
        )
        logger.info("\n" + "-" * 50 + "\n")

    def ingest_document_part(self, project, document, part, allowed_users):
        to_insert = []
        previous_contents = {}
        previous_index = {}
        for line in part.lines.all().order_by("order"):
            for line_transcription in line.transcriptions.all():
                tr_id = line_transcription.transcription.id

                if previous_index.get(tr_id) is not None:
                    # Enhance the previous ES document for this Transcription with the content of its next neighbor
                    to_insert[previous_index[tr_id]][
                        "content"
                    ] += f" {line_transcription.content}"

                to_insert.append(
                    {
                        "_index": settings.ELASTICSEARCH_COMMON_INDEX,
                        "_id": f"{line_transcription.id}",
                        "project_id": project.id,
                        "document_id": document.id,
                        "document_part_id": part.id,
                        "image_url": part.image.url,
                        "image_width": part.image.width,
                        "image_height": part.image.height,
                        "transcription_id": tr_id,
                        # Build the enhanced LineTranscription content by adding the last LineTranscription content for this Transcription
                        "content": f"{previous_contents[tr_id]} {line_transcription.content}"
                        if previous_contents.get(tr_id) is not None
                        else line_transcription.content,
                        "bounding_box": line.get_box(),
                        "have_access": list(set(allowed_users)),
                    }
                )

                previous_contents[tr_id] = line_transcription.content
                previous_index[tr_id] = len(to_insert) - 1

        to_insert = [entry for entry in to_insert if entry["content"]]

        nb_inserted, _ = es_bulk(self.es_client, to_insert, stats_only=True)
        return nb_inserted

    def retrieve_allowed_users(self, project, document):
        shared_with_groups = Group.objects.filter(
            Q(shared_documents=document) | Q(shared_projects=project)
        )
        shared_with_users = list(
            User.objects.filter(
                Q(groups__in=shared_with_groups)
                | Q(shared_documents=document)
                | Q(shared_projects=project)
            ).values_list("id", flat=True)
        )

        if document.owner:
            shared_with_users.append(document.owner.id)

        return shared_with_users
