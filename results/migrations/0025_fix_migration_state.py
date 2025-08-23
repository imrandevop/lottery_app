# Generated manually to fix migration state
# This migration removes the DailyPoints model from Django's migration state
# without attempting to delete the table (which was already dropped in migration 0020)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("results", "0024_delete_dailypoints"),
    ]

    operations = [
        # State-only operation to remove DailyPoints from migration state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="DailyPoints",
                ),
            ],
            database_operations=[
                # No database operations needed - table already dropped
                migrations.RunSQL(
                    sql="SELECT 1; -- State-only fix: DailyPoints already removed from database",
                    reverse_sql="SELECT 1; -- No reverse operation"
                ),
            ]
        ),
    ]