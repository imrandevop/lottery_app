# Replace your current migration with this safer version
# results/migrations/0020_remove_points_system.py

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0019_dailypointspool_is_archived_and_more'),
    ]

    operations = [
        # Use raw SQL with IF EXISTS to avoid errors if tables don't exist
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS results_dailypoints CASCADE;",
            reverse_sql="-- No reverse operation - tables removed"
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS results_dailypointspool CASCADE;", 
            reverse_sql="-- No reverse operation - tables removed"
        ),
    ]