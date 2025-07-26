# Create this file: management/commands/manage_points.py
# Directory structure: your_app/management/commands/manage_points.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Count
import pytz
from datetime import timedelta
from results.models import DailyPointsPool, UserPointsBalance, PointsTransaction, DailyPointsAwarded

class Command(BaseCommand):
    help = 'Manage points system - check status, reset pools, etc.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['status', 'reset_today', 'cleanup_old', 'user_stats'],
            default='status',
            help='Action to perform'
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number for user-specific stats'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days for cleanup or stats'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'status':
            self.show_status()
        elif action == 'reset_today':
            self.reset_today_pool()
        elif action == 'cleanup_old':
            self.cleanup_old_data(options['days'])
        elif action == 'user_stats':
            self.show_user_stats(options.get('phone'), options['days'])

    def show_status(self):
        """Show current points system status"""
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        
        self.stdout.write(self.style.SUCCESS(f"=== Points System Status ({today_ist}) ==="))
        
        # Today's pool status
        try:
            today_pool = DailyPointsPool.objects.get(date=today_ist)
            self.stdout.write(f"📊 Today's Pool:")
            self.stdout.write(f"   Total Budget: {today_pool.total_budget:,}")
            self.stdout.write(f"   Distributed: {today_pool.distributed_points:,}")
            self.stdout.write(f"   Remaining: {today_pool.remaining_points:,}")
            self.stdout.write(f"   Usage: {(today_pool.distributed_points/today_pool.total_budget)*100:.1f}%")
        except DailyPointsPool.DoesNotExist:
            self.stdout.write(self.style.WARNING("⚠️ No pool created for today yet"))
        
        # Awards today
        today_awards = DailyPointsAwarded.objects.filter(award_date=today_ist)
        award_count = today_awards.count()
        total_awarded_today = today_awards.aggregate(Sum('points_awarded'))['points_awarded__sum'] or 0
        
        self.stdout.write(f"\n🎁 Today's Awards:")
        self.stdout.write(f"   Users Awarded: {award_count}")
        self.stdout.write(f"   Total Points: {total_awarded_today:,}")
        
        # Overall stats
        total_users = UserPointsBalance.objects.count()
        total_lifetime_points = UserPointsBalance.objects.aggregate(Sum('lifetime_earned'))['lifetime_earned__sum'] or 0
        total_current_balance = UserPointsBalance.objects.aggregate(Sum('total_points'))['total_points__sum'] or 0
        
        self.stdout.write(f"\n📈 Overall Stats:")
        self.stdout.write(f"   Total Users: {total_users:,}")
        self.stdout.write(f"   Lifetime Points Earned: {total_lifetime_points:,}")
        self.stdout.write(f"   Current Total Balance: {total_current_balance:,}")
        
        # Recent pools (last 7 days)
        week_ago = today_ist - timedelta(days=7)
        recent_pools = DailyPointsPool.objects.filter(date__gte=week_ago).order_by('-date')
        
        self.stdout.write(f"\n📅 Last 7 Days:")
        for pool in recent_pools:
            usage_pct = (pool.distributed_points/pool.total_budget)*100 if pool.total_budget > 0 else 0
            self.stdout.write(f"   {pool.date}: {pool.distributed_points:,}/{pool.total_budget:,} ({usage_pct:.1f}%)")

    def reset_today_pool(self):
        """Reset today's points pool to 10,000"""
        ist = pytz.timezone('Asia/Kolkata')
        today_ist = timezone.now().astimezone(ist).date()
        
        pool, created = DailyPointsPool.objects.get_or_create(
            date=today_ist,
            defaults={
                'total_budget': 10000,
                'distributed_points': 0,
                'remaining_points': 10000
            }
        )
        
        if not created:
            old_distributed = pool.distributed_points
            pool.total_budget = 10000
            pool.distributed_points = 0
            pool.remaining_points = 10000
            pool.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Reset today's pool. Was: {old_distributed:,} distributed, Now: 10,000 available"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("✅ Created today's pool with 10,000 points"))

    def cleanup_old_data(self, days):
        """Clean up old transaction data (keep pools and balances)"""
        cutoff_date = timezone.now().date() - timedelta(days=days)
        
        # Clean old transactions (but keep recent ones for audit)
        old_transactions = PointsTransaction.objects.filter(created_at__date__lt=cutoff_date)
        transaction_count = old_transactions.count()
        
        if transaction_count > 0:
            old_transactions.delete()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Deleted {transaction_count:,} transactions older than {days} days")
            )
        
        # Clean old daily awards (but keep recent ones)
        old_awards = DailyPointsAwarded.objects.filter(award_date__lt=cutoff_date)
        award_count = old_awards.count()
        
        if award_count > 0:
            old_awards.delete()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Deleted {award_count:,} daily awards older than {days} days")
            )
        
        # Optional: Clean very old pools (keep recent ones for analytics)
        very_old_date = cutoff_date - timedelta(days=90)  # Keep 90 days of pools
        old_pools = DailyPointsPool.objects.filter(date__lt=very_old_date)
        pool_count = old_pools.count()
        
        if pool_count > 0:
            old_pools.delete()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Deleted {pool_count:,} very old pools (older than {days+90} days)")
            )
        
        if transaction_count == 0 and award_count == 0 and pool_count == 0:
            self.stdout.write(self.style.WARNING("ℹ️ No old data found to clean up"))

    def show_user_stats(self, phone_number, days):
        """Show stats for a specific user or top users"""
        if phone_number:
            self.show_single_user_stats(phone_number, days)
        else:
            self.show_top_users_stats(days)

    def show_single_user_stats(self, phone_number, days):
        """Show detailed stats for one user"""
        try:
            user = UserPointsBalance.objects.get(phone_number=phone_number)
            
            self.stdout.write(self.style.SUCCESS(f"=== User Stats: {phone_number} ==="))
            self.stdout.write(f"📊 Current Balance: {user.total_points:,} points")
            self.stdout.write(f"🏆 Lifetime Earned: {user.lifetime_earned:,} points")
            self.stdout.write(f"📅 Member Since: {user.created_at.date()}")
            
            # Recent transactions
            recent_transactions = PointsTransaction.objects.filter(
                phone_number=phone_number
            ).order_by('-created_at')[:10]
            
            if recent_transactions:
                self.stdout.write(f"\n📋 Recent Transactions (Last 10):")
                for tx in recent_transactions:
                    self.stdout.write(
                        f"   {tx.created_at.date()}: {tx.points_amount:+,} pts "
                        f"({tx.get_transaction_type_display()}) - Balance: {tx.balance_after:,}"
                    )
            
            # Points earned in last N days
            cutoff_date = timezone.now().date() - timedelta(days=days)
            recent_awards = DailyPointsAwarded.objects.filter(
                phone_number=phone_number,
                award_date__gte=cutoff_date
            )
            
            recent_points = recent_awards.aggregate(Sum('points_awarded'))['points_awarded__sum'] or 0
            recent_days = recent_awards.count()
            
            self.stdout.write(f"\n📈 Last {days} Days:")
            self.stdout.write(f"   Points Earned: {recent_points:,}")
            self.stdout.write(f"   Days Active: {recent_days}")
            if recent_days > 0:
                avg_points = recent_points / recent_days
                self.stdout.write(f"   Average per Active Day: {avg_points:.1f}")
                
        except UserPointsBalance.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User {phone_number} not found"))

    def show_top_users_stats(self, days):
        """Show top users by various metrics"""
        self.stdout.write(self.style.SUCCESS(f"=== Top Users (Last {days} Days) ==="))
        
        # Top by lifetime points
        top_lifetime = UserPointsBalance.objects.order_by('-lifetime_earned')[:10]
        self.stdout.write(f"\n🏆 Top by Lifetime Points:")
        for i, user in enumerate(top_lifetime, 1):
            self.stdout.write(f"   {i}. {user.phone_number}: {user.lifetime_earned:,} pts")
        
        # Top by current balance
        top_balance = UserPointsBalance.objects.order_by('-total_points')[:10]
        self.stdout.write(f"\n💰 Top by Current Balance:")
        for i, user in enumerate(top_balance, 1):
            self.stdout.write(f"   {i}. {user.phone_number}: {user.total_points:,} pts")
        
        # Most active in recent days
        cutoff_date = timezone.now().date() - timedelta(days=days)
        most_active = DailyPointsAwarded.objects.filter(
            award_date__gte=cutoff_date
        ).values('phone_number').annotate(
            days_active=Count('award_date'),
            total_earned=Sum('points_awarded')
        ).order_by('-days_active')[:10]
        
        self.stdout.write(f"\n🔥 Most Active (Last {days} Days):")
        for i, user in enumerate(most_active, 1):
            self.stdout.write(
                f"   {i}. {user['phone_number']}: "
                f"{user['days_active']} days, {user['total_earned']:,} pts"
            )