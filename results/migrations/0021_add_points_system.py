# Create this file manually: results/migrations/0021_add_points_system.py
# (Adjust the number based on your latest migration)

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0020_remove_points_system'),  # Replace with your actual latest migration
    ]

    operations = [
        migrations.CreateModel(
            name='DailyPointsPool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True, unique=True)),
                ('total_budget', models.IntegerField(default=10000)),
                ('distributed_points', models.IntegerField(default=0)),
                ('remaining_points', models.IntegerField(default=10000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Daily Points Pool',
                'verbose_name_plural': 'Daily Points Pools',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='UserPointsBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(db_index=True, max_length=15, unique=True)),
                ('total_points', models.IntegerField(default=0)),
                ('lifetime_earned', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'User Points Balance',
                'verbose_name_plural': 'User Points Balances',
            },
        ),
        migrations.CreateModel(
            name='PointsTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(db_index=True, max_length=15)),
                ('transaction_type', models.CharField(choices=[('lottery_check', 'Lottery Check Reward'), ('bonus', 'Bonus Points'), ('redemption', 'Points Redemption'), ('adjustment', 'Manual Adjustment')], max_length=20)),
                ('points_amount', models.IntegerField()),
                ('balance_before', models.IntegerField()),
                ('balance_after', models.IntegerField()),
                ('ticket_number', models.CharField(blank=True, max_length=50)),
                ('lottery_name', models.CharField(blank=True, max_length=200)),
                ('check_date', models.DateField(blank=True, null=True)),
                ('daily_pool_date', models.DateField(blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Points Transaction',
                'verbose_name_plural': 'Points Transactions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DailyPointsAwarded',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(db_index=True, max_length=15)),
                ('award_date', models.DateField(db_index=True)),
                ('points_awarded', models.IntegerField()),
                ('ticket_number', models.CharField(max_length=50)),
                ('lottery_name', models.CharField(max_length=200)),
                ('awarded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Daily Points Awarded',
                'verbose_name_plural': 'Daily Points Awarded',
                'ordering': ['-award_date', '-awarded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pointstransaction',
            index=models.Index(fields=['phone_number', '-created_at'], name='results_poi_phone_n_4c4c4a_idx'),
        ),
        migrations.AddIndex(
            model_name='pointstransaction',
            index=models.Index(fields=['daily_pool_date'], name='results_poi_daily_p_7e7e7e_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='dailypointsawarded',
            unique_together={('phone_number', 'award_date')},
        ),
    ]