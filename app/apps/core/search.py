from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk as es_bulk

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q

from users.models import User

ES_HOST = settings.ELASTICSEARCH_HOST + ":" + settings.ELASTICSEARCH_PORT


class Indexer:
    es_client = Elasticsearch(hosts=[ES_HOST])

    def __init__(self, project):
        self.project = project

    def configure(self):
        indices = IndicesClient(self.es_client)
        if not indices.exists(settings.ELASTICSEARCH_COMMON_INDEX):
            indices.create(settings.ELASTICSEARCH_COMMON_INDEX)
            print(f"Created a new index named {settings.ELASTICSEARCH_COMMON_INDEX}")

    def process(self):
        to_insert = []
        for document in self.project.documents.all():
            to_insert += self.process_document(document)

        to_insert = [entry for entry in to_insert if entry["transcription"]]

        nb_inserted, _ = es_bulk(self.es_client, to_insert, stats_only=True)
        print(f"Inserted {nb_inserted} new entries in index {settings.ELASTICSEARCH_COMMON_INDEX}")

    def process_document(self, document):
        shared_with_groups = Group.objects.filter(Q(shared_documents=document) | Q(shared_projects=self.project))
        shared_with_users = list(User.objects.filter(
            Q(groups__in=shared_with_groups) |
            Q(shared_documents=document) |
            Q(shared_projects=self.project)
        ).values_list("id", flat=True))

        if document.owner:
            shared_with_users.append(document.owner.id)

        return [
            {
                "_index": settings.ELASTICSEARCH_COMMON_INDEX,
                "_type": "document",
                "_id": part.id,
                "document_id": document.id,
                "project_id": self.project.id,
                "transcription": " ".join([transcription.content for line in part.lines.all() for transcription in line.transcriptions.all()]),
                "have_access": list(set(shared_with_users)),
            }
            for part in document.parts.all()
        ]
