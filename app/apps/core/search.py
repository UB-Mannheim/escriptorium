import re
from urllib.parse import unquote_plus

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery
if settings.USE_OPENSEARCH:
    from opensearchpy import OpenSearch as Elasticsearch
else:
    from elasticsearch import Elasticsearch

from core.models import LineTranscription

EXTRACT_EXACT_TERMS_REGEXP = '"[^"]+"'


def search_content_es(current_page, page_size, user_id, terms, projects=None, documents=None, transcriptions=None):
    es_client = Elasticsearch(hosts=[settings.ELASTICSEARCH_URL])

    cleaned_terms = re.escape(terms)
    exact_matches = re.findall(EXTRACT_EXACT_TERMS_REGEXP, cleaned_terms)
    # Removing the quotation marks around exact terms
    terms_exact = [m[1:-1] for m in exact_matches]
    if terms_exact:
        terms_fuzzy = re.split(EXTRACT_EXACT_TERMS_REGEXP, cleaned_terms)
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


def search_content_psql(terms, right_filters, project_id=None, document_id=None, transcription_id=None, part_id=None):
    cleaned_terms = re.escape(terms)

    filters = {}
    if project_id:
        filters["line__document_part__document__project_id"] = project_id

    if document_id:
        filters["line__document_part__document_id"] = document_id

    if transcription_id:
        filters["transcription_id"] = transcription_id

    if part_id:
        filters["line__document_part_id"] = part_id

    search_query = SearchQuery(cleaned_terms)
    return (
        LineTranscription.objects.select_related(
            "transcription",
            "line",
            "line__document_part",
            "line__document_part__document",
        )
        .filter(content__search=search_query, **right_filters, **filters)
        .annotate(
            highlighted_content=SearchHeadline(
                "content",
                search_query,
                start_sel='<strong class="text-success">',
                stop_sel="</strong>",
            )
        )
    )
