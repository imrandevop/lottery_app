
# Edit the migration file:
from django.db import migrations

def assign_lottery_types(apps, schema_editor):
    WinningTicket = apps.get_model('lottery', 'WinningTicket')
    PrizeCategory = apps.get_model('lottery', 'PrizeCategory')
    
    # For each prize category, try to infer its lottery type from its winning tickets
    for prize in PrizeCategory.objects.filter(lottery_type__isnull=True):
        # Get a winning ticket for this prize
        ticket = WinningTicket.objects.filter(prize_category=prize).first()
        if ticket:
            # Set the lottery type of the prize to match the lottery type of the draw
            prize.lottery_type = ticket.draw.lottery_type
            prize.save()

def reverse_func(apps, schema_editor):
    # No need to reverse this operation
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('lottery', '0002_alter_prizecategory_options_and_more'),  # Replace with actual dependency
    ]

    operations = [
        migrations.RunPython(assign_lottery_types, reverse_func),
    ]