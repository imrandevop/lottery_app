#models.py

from django.db import migrations, models
import uuid


def generate_unique_ids(apps, schema_editor):
    """Generate unique UUIDs for existing LotteryResult records"""
    LotteryResult = apps.get_model('results', 'LotteryResult')
    for lottery_result in LotteryResult.objects.all():
        lottery_result.unique_id = uuid.uuid4()
        lottery_result.save()


def reverse_generate_unique_ids(apps, schema_editor):
    """Reverse migration - set all UUIDs to None"""
    pass  # We can't really reverse this meaningfully


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0002_lotteryresult_prizeentry'),  # Update this to match your last migration
    ]

    operations = [
        # Step 1: Add UUID field without unique constraint
        migrations.AddField(
            model_name='lotteryresult',
            name='unique_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        
        # Step 2: Populate unique UUIDs for existing records
        migrations.RunPython(
            generate_unique_ids,
            reverse_generate_unique_ids,
        ),
        
        # Step 3: Make the field non-nullable and unique
        migrations.AlterField(
            model_name='lotteryresult',
            name='unique_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]