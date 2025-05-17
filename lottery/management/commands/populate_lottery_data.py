from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from lottery.models import LotteryType, LotteryDraw, PrizeCategory, WinningTicket

class Command(BaseCommand):
    help = 'Populates the database with sample lottery data'

    def handle(self, *args, **kwargs):
        # Create lottery types
        self.stdout.write('Creating lottery types...')
        akshaya, created = LotteryType.objects.get_or_create(
            name='Akshaya',
            code='AK',
            defaults={
                'price': 80,
                'first_prize_amount': 7000000,
                'description': 'Akshaya lottery is a popular Kerala state lottery.'
            }
        )
        
        win_win, created = LotteryType.objects.get_or_create(
            name='Win Win',
            code='WW',
            defaults={
                'price': 40,
                'first_prize_amount': 5000000,
                'description': 'Win Win lottery is conducted every Monday.'
            }
        )
        
        # Create prize categories
        self.stdout.write('Creating prize categories...')
        first_prize, created = PrizeCategory.objects.get_or_create(
            name='First Prize',
            defaults={
                'display_name': '1st Prize Rs 7000000/- [70 Lakhs]',
                'amount': 7000000,
                'display_amount': 'Rs 7000000/- [70 Lakhs]'
            }
        )
        
        consolation_prize, created = PrizeCategory.objects.get_or_create(
            name='Consolation Prize',
            defaults={
                'display_name': 'Consolation Prize 8000/-',
                'amount': 8000,
                'display_amount': '8000/-'
            }
        )
        
        # Create today's lottery draw
        self.stdout.write('Creating lottery draws...')
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Today's draw
        today_draw, created = LotteryDraw.objects.get_or_create(
            lottery_type=akshaya,
            draw_number=620,
            defaults={
                'draw_date': today,
                'result_declared': True,
                'is_new': True
            }
        )
        
        # Yesterday's draw
        yesterday_draw, created = LotteryDraw.objects.get_or_create(
            lottery_type=win_win,
            draw_number=520,
            defaults={
                'draw_date': yesterday,
                'result_declared': True,
                'is_new': False
            }
        )
        
        # Create some older draws
        for i in range(2, 10):
            older_date = today - timedelta(days=i)
            draw_number = 620 - i
            
            older_draw, created = LotteryDraw.objects.get_or_create(
                lottery_type=akshaya if i % 2 == 0 else win_win,
                draw_number=draw_number,
                defaults={
                    'draw_date': older_date,
                    'result_declared': True,
                    'is_new': False
                }
            )
        
        # Create winning tickets for today's draw
        self.stdout.write('Creating winning tickets...')
        
        # First prize winner
        first_winner, created = WinningTicket.objects.get_or_create(
            draw=today_draw,
            series='AY',
            number='197092',
            prize_category=first_prize,
            defaults={'location': 'Thrissur'}
        )
        
        # Consolation winners
        consolation_tickets = [
            {'series': 'NB', 'number': '57040'},
            {'series': 'NC', 'number': '570212'},
            {'series': 'NE', 'number': '89456'},
            {'series': 'NB', 'number': '57040'}, # Duplicated as shown in screenshot
            {'series': 'NC', 'number': '570212'}, # Duplicated as shown in screenshot
            {'series': 'NE', 'number': '89456'}, # Duplicated as shown in screenshot
        ]
        
        for ticket_data in consolation_tickets:
            WinningTicket.objects.get_or_create(
                draw=today_draw,
                series=ticket_data['series'],
                number=ticket_data['number'],
                prize_category=consolation_prize
            )
        
        # Also create winners for yesterday's and older draws
        self.stdout.write('Creating winners for other draws...')
        
        # Yesterday's draw winner
        yesterday_winner, created = WinningTicket.objects.get_or_create(
            draw=yesterday_draw,
            series='WA',
            number='123456',
            prize_category=first_prize,
            defaults={'location': 'Kochi'}
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated lottery data!'))