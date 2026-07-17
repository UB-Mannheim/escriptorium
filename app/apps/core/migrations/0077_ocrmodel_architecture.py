from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0076_alter_ocrmodel_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='ocrmodel',
            name='architecture',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
