from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.helpers import bulk as es_bulk

from django.conf import settings

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
        return [
            {
                "_index": settings.ELASTICSEARCH_COMMON_INDEX,
                "_type": "document",
                "_id": str(part.id),
                "document_id": str(document.id),
                "project_id": str(self.project.id),
                "transcription": " ".join([transcription.content for line in part.lines.all() for transcription in line.transcriptions.all()])
            }
            for part in document.parts.all()
        ]
