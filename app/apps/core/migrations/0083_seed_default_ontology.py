from django.db import migrations

# Replaces the old block/line type templates (seeded in 0039) with a new
# default ontology. These are public+default global (document=NULL) rows:
# new documents copy them at creation time (see Document.save()); existing
# documents are unaffected. Safe to delete the old ones outright - the
# 0080 data migration already retargeted all existing content to
# document-owned rows, so nothing still points at these global rows.

OLD_BLOCK_TYPES = ['Title', 'Main', 'Commentary', 'Illustration']
OLD_LINE_TYPES = ['Main', 'Numbering', 'Correction', 'Signature']

NEW_BLOCK_TYPES = [
    'DamageZone', 'DigitizationArtefactZone', 'DropCapitalZone', 'GraphicZone',
    'MainZone', 'MarginTextZone', 'MusicZone', 'NumberingZone', 'QuireMarksZone',
    'RunningTitleZone', 'SealZone', 'StampZone', 'TableZone', 'TitlePageZone',
]
NEW_LINE_TYPES = [
    'DefaultLine', 'DropCapitalLine', 'HeadingLine', 'InterlinearLine', 'MusicLine',
]


def seed_default_ontology(apps, schema_editor):
    BlockType = apps.get_model('core', 'BlockType')
    LineType = apps.get_model('core', 'LineType')

    BlockType.objects.filter(document__isnull=True, public=True, name__in=OLD_BLOCK_TYPES).delete()
    LineType.objects.filter(document__isnull=True, public=True, name__in=OLD_LINE_TYPES).delete()

    for name in NEW_BLOCK_TYPES:
        BlockType.objects.update_or_create(document=None, name=name, defaults={'public': True, 'default': True})
    for name in NEW_LINE_TYPES:
        LineType.objects.update_or_create(document=None, name=name, defaults={'public': True, 'default': True})


def unseed_default_ontology(apps, schema_editor):
    BlockType = apps.get_model('core', 'BlockType')
    LineType = apps.get_model('core', 'LineType')

    BlockType.objects.filter(document__isnull=True, name__in=NEW_BLOCK_TYPES).delete()
    LineType.objects.filter(document__isnull=True, name__in=NEW_LINE_TYPES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0082_type_unique_constraints'),
    ]

    operations = [
        migrations.RunPython(seed_default_ontology, unseed_default_ontology),
    ]
