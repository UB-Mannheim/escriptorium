from urllib.parse import unquote_plus

from django.conf import settings
from elasticsearch import Elasticsearch


def search_in_projects(current_page, page_size, user_id, projects, terms):
    es_client = Elasticsearch(hosts=[settings.ELASTICSEARCH_URL])

    body = {
        "from": (current_page - 1) * page_size,
        "size": page_size,
        "sort": ["_score"],
        "query": {
            "bool": {
                "must": [
                    {"term": {"have_access": user_id}},
                    {"terms": {"project_id": projects}},
                    {
                        "match": {
                            "content": {
                                "query": unquote_plus(terms),
                                "fuzziness": "AUTO",
                            }
                        }
                    },
                ]
            }
        },
        "highlight": {
            "pre_tags": ['<strong class="text-success">'],
            "post_tags": ["</strong>"],
            "fields": {"content": {}},
        },
    }

    return es_client.search(index=settings.ELASTICSEARCH_COMMON_INDEX, body=body)
