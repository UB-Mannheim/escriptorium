import re
from urllib.parse import unquote_plus

from django.conf import settings
from django.contrib.postgres.search import SearchHeadline, SearchQuery
from django.db.models import CharField, F, Func, Value
from elasticsearch import Elasticsearch

EXTRACT_EXACT_TERMS_REGEXP = '"[^"]+"'
WORD_BY_WORD_SEARCH_MODE = "word-by-word"
REGEX_SEARCH_MODE = "regex"


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


def get_filtered_queryset(user, project_id, document_id, transcription_id, part_id):
    from core.models import Document, LineTranscription, Project

    right_filters = {
        "line__document_part__document__project_id__in": Project.objects.for_user_read(user),
        "line__document_part__document_id__in": Document.objects.for_user(user),
    }

    filters = {}
    if project_id:
        filters["line__document_part__document__project_id"] = project_id

    if document_id:
        filters["line__document_part__document_id"] = document_id

    if transcription_id:
        filters["transcription_id"] = transcription_id

    if part_id:
        filters["line__document_part_id"] = part_id

    return LineTranscription.objects.select_related(
        "transcription",
        "line",
        "line__document_part",
        "line__document_part__document",
    ).filter(**right_filters, **filters)


def search_content_psql_word(terms, user, highlight_class, project_id=None, document_id=None, transcription_id=None, part_id=None):
    search_query = SearchQuery(terms)
    return (
        get_filtered_queryset(user, project_id, document_id, transcription_id, part_id)
        .filter(content__search=search_query)
        .annotate(
            highlighted_content=SearchHeadline(
                "content",
                search_query,
                start_sel=f'<strong class="{highlight_class}">',
                stop_sel="</strong>",
            )
        )
    )


def search_content_psql_regex(terms, user, highlight_class, project_id=None, document_id=None, transcription_id=None, part_id=None):
    return (
        get_filtered_queryset(user, project_id, document_id, transcription_id, part_id)
        .filter(content__regex=terms)
        .annotate(
            highlighted_content=Func(
                F("content"),
                Value(r"(%s)" % terms),
                Value(r'<strong class="%s">\1</strong>' % highlight_class),
                Value("g"),
                function="REGEXP_REPLACE",
                output_field=CharField(),
            )
        )
    )


def build_highlighted_replacement_psql(mode, find_terms, replace_term, highlighted_content):
    if not replace_term:
        return None

    extra = {}
    if mode == WORD_BY_WORD_SEARCH_MODE:
        replace_term = replace_term.replace('\\', r'\\')
        extra = {"flags": re.IGNORECASE}

    return re.sub(r'<strong class="text-danger">%s</strong>' % find_terms, r'<strong class="text-success">%s</strong>' % replace_term, highlighted_content, **extra)
