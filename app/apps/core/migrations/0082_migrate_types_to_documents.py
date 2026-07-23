from django.db import migrations

# Forward-only data migration: turns global BlockType/LineType/DocumentPartType
# rows into per-document rows (one row per (document, name) that is actually
# linked or used), retargets content to the new owned rows, empties the
# soon-to-be-dropped valid_* M2M tables, drops now-unreferenced non-public
# globals, and dedups whatever public templates remain. Also dedups
# AnnotationType by name, retargeting AnnotationTaxonomy.

BLOCK_SQL = """
INSERT INTO core_blocktype (name, public, "default", document_id, color)
SELECT DISTINCT bt.name, false, false, u.doc_id, NULL FROM (
    SELECT m.document_id AS doc_id, m.blocktype_id AS type_id
      FROM core_document_valid_block_types m
    UNION
    SELECT dp.document_id, b.typology_id
      FROM core_block b JOIN core_documentpart dp ON dp.id = b.document_part_id
     WHERE b.typology_id IS NOT NULL
) u JOIN core_blocktype bt ON bt.id = u.type_id
WHERE bt.document_id IS NULL;

UPDATE core_block b
   SET typology_id = nt.id
  FROM core_documentpart dp, core_blocktype ot, core_blocktype nt
 WHERE dp.id = b.document_part_id AND ot.id = b.typology_id
   AND ot.document_id IS NULL
   AND nt.document_id = dp.document_id AND nt.name = ot.name;

DELETE FROM core_document_valid_block_types;

DELETE FROM core_blocktype bt
 WHERE bt.document_id IS NULL AND bt.public = false
   AND NOT EXISTS (SELECT 1 FROM core_block b WHERE b.typology_id = bt.id);

DELETE FROM core_blocktype a USING core_blocktype b
 WHERE a.document_id IS NULL AND b.document_id IS NULL
   AND a.name = b.name AND a.id > b.id;
"""

LINE_SQL = """
INSERT INTO core_linetype (name, public, "default", document_id, color)
SELECT DISTINCT lt.name, false, false, u.doc_id, NULL FROM (
    SELECT m.document_id AS doc_id, m.linetype_id AS type_id
      FROM core_document_valid_line_types m
    UNION
    SELECT dp.document_id, l.typology_id
      FROM core_line l JOIN core_documentpart dp ON dp.id = l.document_part_id
     WHERE l.typology_id IS NOT NULL
) u JOIN core_linetype lt ON lt.id = u.type_id
WHERE lt.document_id IS NULL;

UPDATE core_line l
   SET typology_id = nt.id
  FROM core_documentpart dp, core_linetype ot, core_linetype nt
 WHERE dp.id = l.document_part_id AND ot.id = l.typology_id
   AND ot.document_id IS NULL
   AND nt.document_id = dp.document_id AND nt.name = ot.name;

DELETE FROM core_document_valid_line_types;

DELETE FROM core_linetype lt
 WHERE lt.document_id IS NULL AND lt.public = false
   AND NOT EXISTS (SELECT 1 FROM core_line l WHERE l.typology_id = lt.id);

DELETE FROM core_linetype a USING core_linetype b
 WHERE a.document_id IS NULL AND b.document_id IS NULL
   AND a.name = b.name AND a.id > b.id;
"""

PART_SQL = """
INSERT INTO core_documentparttype (name, public, "default", document_id)
SELECT DISTINCT pt.name, false, false, u.doc_id FROM (
    SELECT m.document_id AS doc_id, m.documentparttype_id AS type_id
      FROM core_document_valid_part_types m
    UNION
    SELECT dp.document_id, dp.typology_id
      FROM core_documentpart dp
     WHERE dp.typology_id IS NOT NULL
) u JOIN core_documentparttype pt ON pt.id = u.type_id
WHERE pt.document_id IS NULL;

UPDATE core_documentpart dp
   SET typology_id = nt.id
  FROM core_documentparttype ot, core_documentparttype nt
 WHERE ot.id = dp.typology_id
   AND ot.document_id IS NULL
   AND nt.document_id = dp.document_id AND nt.name = ot.name;

DELETE FROM core_document_valid_part_types;

DELETE FROM core_documentparttype pt
 WHERE pt.document_id IS NULL AND pt.public = false
   AND NOT EXISTS (SELECT 1 FROM core_documentpart dp WHERE dp.typology_id = pt.id);

DELETE FROM core_documentparttype a USING core_documentparttype b
 WHERE a.document_id IS NULL AND b.document_id IS NULL
   AND a.name = b.name AND a.id > b.id;
"""

ANNOTATIONTYPE_SQL = """
UPDATE core_annotationtaxonomy t SET typology_id = k.keep_id
  FROM (SELECT name, MIN(id) AS keep_id FROM core_annotationtype GROUP BY name) k,
       core_annotationtype a
 WHERE a.id = t.typology_id AND a.name = k.name AND a.id <> k.keep_id;

DELETE FROM core_annotationtype a
 USING (SELECT name, MIN(id) AS keep_id FROM core_annotationtype GROUP BY name) k
 WHERE a.name = k.name AND a.id <> k.keep_id;
"""


def migrate_types_to_documents(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(BLOCK_SQL)
        cursor.execute(LINE_SQL)
        cursor.execute(PART_SQL)
        cursor.execute(ANNOTATIONTYPE_SQL)


def unsupported_reverse(apps, schema_editor):
    raise NotImplementedError("0082_migrate_types_to_documents cannot be reversed")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0081_document_scoped_types'),
    ]

    operations = [
        migrations.RunPython(migrate_types_to_documents, unsupported_reverse),
    ]
