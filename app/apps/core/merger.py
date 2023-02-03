import itertools
import sys
from math import sqrt
from typing import Any, Dict, List, Tuple

from django.db.models import prefetch_related_objects
from shapely.geometry import LineString, Polygon

from api.serializers import DetailedLineSerializer
from core.models import Block, Line

__all__ = ['merge_lines', 'MAX_MERGE_SIZE']
MAX_MERGE_SIZE = 8  # Maximum numbers of segments we can merge


def distance(a: Line, b: Line) -> float:
    pt1 = a.baseline[-1]
    pt2 = b.baseline[0]
    dist = sqrt((pt2[1] - pt1[1])**2 + (pt2[0] - pt1[0])**2)

    return dist


def build_dist_matrix(lines: List[Line]) -> List[List[float]]:
    # The distance matrix contains the distance between every two lines
    # mat[i][j] is the distance from the end of lines[i] to the beginning of lines[j]

    dist_matrix: List[List[float]] = []
    for i in range(len(lines)):
        line_dist = [distance(lines[i], lines[j]) if i != j else sys.maxsize for j in range(len(lines))]
        dist_matrix.append(line_dist)
    return dist_matrix


def find_order(lines: List[Line]) -> Tuple[int, ...]:
    # Brute force our way through all the permutations. MAX_MERGE_SIZE makes sure this will not explode.
    if len(lines) > MAX_MERGE_SIZE:  # Test again, in case someone calls this function from the outside
        raise ValueError(f"Can't find order of more than {MAX_MERGE_SIZE} lines")

    def perm_score(perm):
        score = 0.0
        for i in range(len(perm) - 1):
            score += mat[perm[i]][perm[i + 1]]
        return score

    mat = build_dist_matrix(lines)

    best_score = sys.maxsize
    best_perm: Tuple[int, ...] = (0, )

    for perm in itertools.permutations(list(range(len(lines)))):
        score = perm_score(perm)
        if score < best_score:
            best_score, best_perm = score, perm

    return best_perm


def merge_baseline(ordered_lines: List[Line]) -> List[Tuple[int, int]]:
    baseline = []
    for line in ordered_lines:
        baseline += line.baseline
    return baseline


def find_typology(lines):
    types = (line.typology for line in lines if line.typology is not None)
    return next(types, None)


def merge_transcriptions(ordered_lines: List[Line]) -> List[Dict[str, Any]]:
    def get_line_transcription(line, transcription):
        # Filter in Python, not SQL, as to not generate another SQL request.
        # The number of transcriptions per line is relatively low, this will not need to be optimized.
        lt = [lt for lt in line.transcriptions.all() if lt.transcription == transcription]
        if len(lt) == 0:
            return None
        if len(lt) == 1:
            return lt[0]
        raise ValueError(f"Found more than one transcription {transcription} for line {line.pk}")  # This should never happen

    doc = ordered_lines[0].document_part.document
    rtl = doc.main_script and doc.main_script.text_direction in ['horizontal-rl', 'vertical-rl']
    if rtl:
        ordered_lines = list(reversed(ordered_lines))

    transcriptions = doc.transcriptions.all()
    prefetch_related_objects(ordered_lines, 'transcriptions')

    # Combine all transcriptions. This isn't done in an efficient manner, but shouldn't post a problem
    # since merging is done on a small number of lines, and there are only so much transcriptions.
    # If this proves to cause a performance issue, we'll use more efficient SQL queries.

    result = []
    for transcription in transcriptions:
        line_transcriptions = [get_line_transcription(line, transcription) for line in ordered_lines]  # type:ignore PyLance doesn't find the transcriptions related property
        actual = [t.content for t in line_transcriptions if t is not None]
        joined_content = doc.main_script and doc.main_script.blank_char.join(actual) or ' '

        json = dict(transcription=transcription.pk, content=joined_content, )
        result.append(json)

    return result


def find_block(baseline: str, regions: List[Block]):
    center = LineString(baseline).interpolate(0.5, normalized=True)
    region = next(
        (r for r in regions if Polygon(r.box).contains(center)), None
    )

    return region.pk if region is not None else None


def merge_lines(lines: List[Line]):
    if len(lines) > MAX_MERGE_SIZE:
        raise ValueError(f"Can't merge {len(lines)} lines, can only merge up to {MAX_MERGE_SIZE} lines")

    order = find_order(lines)

    # We don't really create the line, just the JSON that will allow the serializers to create the line.
    # This guarantees that all the error checks, validations and dependent async processes (calculating the mask, for example)
    # run as usual.

    serializer = DetailedLineSerializer(lines[0], many=False)
    merged_json = serializer.data

    # Clear fields we don't need
    unnecessary = ('pk', 'external_id', 'region',)
    for key in unnecessary:
        del merged_json[key]

    ordered_lines = [lines[order[i]] for i in range(len(lines))]
    merged_json['baseline'] = merge_baseline(ordered_lines)
    typology = find_typology(ordered_lines)
    merged_json['typology'] = typology.pk if typology else None
    merged_json['transcriptions'] = merge_transcriptions(ordered_lines)

    blocks = ordered_lines[0].document_part.blocks.all()
    merged_json['region'] = find_block(merged_json['baseline'], blocks)

    return merged_json
