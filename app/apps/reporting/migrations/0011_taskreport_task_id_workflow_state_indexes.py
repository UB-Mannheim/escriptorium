from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for concurrent index creation

    dependencies = [
        ("reporting", "0010_taskgroup_collection_taskreport_collection_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="taskreport",
                    name="task_id",
                    field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
                ),
                migrations.AlterField(
                    model_name="taskreport",
                    name="workflow_state",
                    field=models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Queued"),
                            (1, "Running"),
                            (2, "Crashed"),
                            (3, "Finished"),
                            (4, "Canceled"),
                        ],
                        db_index=True,
                        default=0,
                    ),
                ),
            ],
            database_operations=[
                AddIndexConcurrently(
                    model_name="taskreport",
                    index=models.Index(fields=["task_id"], name="reporting_task_id_idx"),
                ),
                AddIndexConcurrently(
                    model_name="taskreport",
                    index=models.Index(fields=["workflow_state"], name="reporting_workflow_state_idx"),
                ),
            ],
        ),
    ]
