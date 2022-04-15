import re
from urllib.parse import unquote_plus

from django.conf import settings
from elasticsearch import Elasticsearch


def search_content(current_page, page_size, user_id, terms, projects=None, documents=None):
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
                ] + [
                    {"match": {
                        "content": {
                            "query": unquote_plus(term),
                            "fuzziness": "AUTO",
                        }
                    }}
                    for term in terms_fuzzy if term.strip() != ""
                ] + [
                    {"match_phrase": {
                        "content": {
                            "query": unquote_plus(term)
                        }
                    }}
                    for term in terms_exact if term.strip() != ""
                ]
            }
        },
        "highlight": {
            "pre_tags": ['<strong class="text-success">'],
            "post_tags": ["</strong>"],
            "fields": {"content": {}},
        },
    }

    if projects:
        body["query"]["bool"]["must"].append({"terms": {"project_id": projects}})

    if documents:
        body["query"]["bool"]["must"].append({"terms": {"document_id": documents}})

    return es_client.search(index=settings.ELASTICSEARCH_COMMON_INDEX, body=body)
