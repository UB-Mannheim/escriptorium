import re
from urllib.parse import unquote_plus

from django.conf import settings
from elasticsearch import Elasticsearch


def search_content(current_page, page_size, user_id, terms, projects=None, documents=None, transcriptions=None):
    es_client = Elasticsearch(hosts=[settings.ELASTICSEARCH_URL])

    exact_matches = re.findall('"[^"]*[^"]"', re.escape(terms))
    terms_exact = [m[1:-1] for m in exact_matches]
    if terms_exact:
        terms_fuzzy = re.split('|'.join(exact_matches), re.escape(terms))
    else:
        terms_fuzzy = [terms]

    body = {
        "from": (current_page - 1) * page_size,
        "size": page_size,
        "sort": ["_score"],
        "query": {
            "bool": {
                "must": [
                    {"term": {"have_access": user_id}},
                    # Prevent from loading results from archived documents
                    {"term": {"document_archived": False}},
                ] + [
                    {"multi_match": {
                        "query": unquote_plus(term),
                        "fuzziness": "AUTO",
                        "fields": ["raw_content^3", "context"]
                    }}
                    for term in terms_fuzzy if term.strip() != ""
                ] + [
                    {"multi_match": {
                        "query": unquote_plus(term),
                        "type": "phrase",
                        "fields": ["raw_content^3", "context"]
                    }}
                    for term in terms_exact if term.strip() != ""
                ]
            }
        },
        "highlight": {
            "require_field_match": False,
            "pre_tags": ['<strong class="text-success">'],
            "post_tags": ["</strong>"],
            "fields": {
                "raw_content": {},
                "context_before": {},
                "context_after": {}
            },
        }
    }

    if projects:
        body["query"]["bool"]["must"].append({"terms": {"project_id": projects}})

    if documents:
        body["query"]["bool"]["must"].append({"terms": {"document_id": documents}})

    if transcriptions:
        body["query"]["bool"]["must"].append({"terms": {"transcription_id": transcriptions}})

    return es_client.search(index=settings.ELASTICSEARCH_COMMON_INDEX, body=body)
