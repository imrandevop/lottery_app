"""
Django Management Command: Live Lottery Scraper Background Worker

This command runs continuously in the background and polls active scraping sessions
every 60 seconds. It scrapes the Kerala Lottery website and merges new prizes.

Usage:
    python manage.py run_live_scraper

To run in background (Windows):
    start /B python manage.py run_live_scraper

To run in background (Linux/Mac):
    nohup python manage.py run_live_scraper &

Author: Auto-generated for lottery project
Date: 2025-10-25
"""

import time
import logging
from django.core.management.base import BaseCommand
from results.services.live_lottery_scraper import LiveScraperService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Background worker to poll active live lottery scraping sessions every 60 seconds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Polling interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit (useful for testing)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']

        self.stdout.write(self.style.SUCCESS('🚀 Live Lottery Scraper Worker Started'))
        self.stdout.write(f'⏱️  Polling interval: {interval} seconds')

        if run_once:
            self.stdout.write(self.style.WARNING('⚠️  Running in ONE-TIME mode'))

        try:
            while True:
                try:
                    self.stdout.write(f'\n{"="*60}')
                    self.stdout.write(f'🔄 Polling active sessions... ({time.strftime("%Y-%m-%d %H:%M:%S")})')
                    self.stdout.write(f'{"="*60}')

                    # Poll all active sessions
                    LiveScraperService.poll_active_sessions()

                    self.stdout.write(self.style.SUCCESS('✅ Poll cycle completed'))

                    if run_once:
                        self.stdout.write(self.style.SUCCESS('✅ One-time run completed. Exiting.'))
                        break

                    # Wait for next poll
                    self.stdout.write(f'⏳ Waiting {interval} seconds for next poll...\n')
                    time.sleep(interval)

                except KeyboardInterrupt:
                    self.stdout.write(self.style.WARNING('\n⚠️  Keyboard interrupt detected'))
                    break
                except Exception as e:
                    logger.error(f'❌ Error in poll cycle: {e}', exc_info=True)
                    self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))

                    if run_once:
                        break

                    # Continue running even if there's an error
                    self.stdout.write(f'⏳ Waiting {interval} seconds before retry...')
                    time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⏸️  Worker stopped by user'))
        finally:
            self.stdout.write(self.style.SUCCESS('\n👋 Live Lottery Scraper Worker Stopped'))
