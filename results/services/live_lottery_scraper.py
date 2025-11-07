"""
Live Lottery Result Scraper Service

This service handles real-time scraping of lottery results during the draw period (3:00 PM - 4:15 PM).
It polls the Kerala Lottery website every 60 seconds and merges new prizes with existing data.

Author: Auto-generated for lottery project
Date: 2025-10-25
"""

import logging
from typing import Dict, List, Optional
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from results.models import LotteryResult, PrizeEntry, LiveScrapingSession, Lottery
from results.services.scraper_factory import ScraperFactory
from results.services.lottery_scraper import KeralaLotteryScraper

logger = logging.getLogger(__name__)


class LiveScraperService:
    """
    Service to handle live lottery result scraping
    Polls website every 60 seconds and intelligently merges prizes
    """

    @classmethod
    def start_scraping(cls, url: str) -> Dict:
        """
        Start a live scraping session for a Kerala Lottery URL

        Args:
            url: Kerala Lotteries result page URL

        Returns:
            Dictionary with:
            {
                'success': bool,
                'session_id': int,
                'lottery_result_id': int,
                'message': str
            }
        """
        try:
            # Check if there's already an active session
            if LiveScrapingSession.has_active_session():
                active_session = LiveScrapingSession.get_active_session()
                return {
                    'success': False,
                    'message': f'Another scraping session is already active for {active_session.lottery_result}. Please stop it first.',
                    'session_id': None,
                    'lottery_result_id': None
                }

            logger.info(f"🚀 Starting live scraping session for URL: {url}")

            # Initial scrape to get lottery info
            scraped_data = ScraperFactory.scrape_lottery_result(url)

            # Match lottery name to existing lottery
            scraper = KeralaLotteryScraper()
            existing_lotteries = list(Lottery.objects.values_list('id', 'name'))
            matched_lottery_id = scraper.match_lottery_name(
                scraped_data['lottery_name'],
                existing_lotteries
            )

            if not matched_lottery_id:
                return {
                    'success': False,
                    'message': f"Could not match lottery name '{scraped_data['lottery_name']}' to existing lottery. Please create the lottery first.",
                    'session_id': None,
                    'lottery_result_id': None
                }

            # Create or get LotteryResult
            lottery_result, created = LotteryResult.objects.get_or_create(
                lottery_id=matched_lottery_id,
                draw_number=scraped_data['draw_number'],
                date=scraped_data['date'],
                defaults={
                    'is_published': False,
                    'is_bumper': False,
                    'results_ready_notification': False
                }
            )

            # Check if a live session already exists for this result
            if hasattr(lottery_result, 'live_session') and lottery_result.live_session.is_active:
                return {
                    'success': False,
                    'message': f'Live scraping session already exists for this lottery result.',
                    'session_id': lottery_result.live_session.id,
                    'lottery_result_id': lottery_result.id
                }

            # Create initial prize entries from first scrape
            prizes_added = 0
            for prize_data in scraped_data['prizes']:
                _, prize_created = PrizeEntry.objects.get_or_create(
                    lottery_result=lottery_result,
                    prize_type=prize_data['prize_type'],
                    ticket_number=prize_data['ticket_number'],
                    defaults={
                        'prize_amount': prize_data['prize_amount'],
                        'place': prize_data.get('place', '')
                    }
                )
                if prize_created:
                    prizes_added += 1

            # Create live scraping session
            session = LiveScrapingSession.objects.create(
                lottery_result=lottery_result,
                scraping_url=url,
                status='scraping',
                is_active=True,
                prizes_found_count=prizes_added,
                poll_count=1,
                last_polled_at=timezone.now()
            )

            logger.info(f"✅ Live scraping session created: {session.id} for {lottery_result} ({prizes_added} prizes found)")

            return {
                'success': True,
                'message': f'Live scraping started for {scraped_data["lottery_name"]} - {scraped_data["draw_number"]} ({prizes_added} prizes found)',
                'session_id': session.id,
                'lottery_result_id': lottery_result.id
            }

        except Exception as e:
            logger.error(f"❌ Error starting live scraping: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Failed to start live scraping: {str(e)}',
                'session_id': None,
                'lottery_result_id': None
            }

    @classmethod
    def stop_scraping(cls, session_id: int) -> Dict:
        """
        Stop an active scraping session

        Args:
            session_id: ID of the LiveScrapingSession to stop

        Returns:
            Dictionary with success status and message
        """
        try:
            session = LiveScrapingSession.objects.get(id=session_id)

            if not session.is_active:
                return {
                    'success': False,
                    'message': 'Scraping session is already stopped'
                }

            session.mark_stopped()
            logger.info(f"⏸️ Live scraping session {session_id} stopped manually")

            return {
                'success': True,
                'message': f'Scraping stopped. Total prizes found: {session.prizes_found_count}'
            }

        except LiveScrapingSession.DoesNotExist:
            return {
                'success': False,
                'message': 'Scraping session not found'
            }
        except Exception as e:
            logger.error(f"❌ Error stopping scraping session: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error stopping session: {str(e)}'
            }

    @classmethod
    def scrape_and_merge(cls, session: LiveScrapingSession) -> Dict:
        """
        Scrape website and merge new prizes with existing data

        Args:
            session: Active LiveScrapingSession

        Returns:
            Dictionary with scraping results
        """
        try:
            logger.info(f"🔄 Polling {session.scraping_url}...")

            # Scrape the website
            scraped_data = ScraperFactory.scrape_lottery_result(session.scraping_url)
            scraped_prizes = scraped_data['prizes']

            # Get existing prizes from database
            existing_prizes = list(PrizeEntry.objects.filter(
                lottery_result=session.lottery_result
            ).values('prize_type', 'ticket_number', 'prize_amount', 'place'))

            # Convert existing prizes to a set of tuples for fast lookup
            existing_set = {
                (p['prize_type'], p['ticket_number'])
                for p in existing_prizes
            }

            # Merge: Add only new prizes
            added_count = 0
            skipped_count = 0

            with transaction.atomic():
                for prize_data in scraped_prizes:
                    prize_key = (prize_data['prize_type'], prize_data['ticket_number'])

                    if prize_key in existing_set:
                        # Prize already exists, skip
                        skipped_count += 1
                        logger.debug(f"⏩ Skipped duplicate: {prize_data['prize_type']} - {prize_data['ticket_number']}")
                    else:
                        # New prize, add to database
                        PrizeEntry.objects.create(
                            lottery_result=session.lottery_result,
                            prize_type=prize_data['prize_type'],
                            prize_amount=prize_data['prize_amount'],
                            ticket_number=prize_data['ticket_number'],
                            place=prize_data.get('place', '')
                        )
                        added_count += 1
                        logger.info(f"➕ Added new prize: {prize_data['prize_type']} - {prize_data['ticket_number']}")

                # Update session stats
                total_prizes = len(existing_prizes) + added_count
                session.update_stats(total_prizes)

            result = {
                'success': True,
                'added': added_count,
                'skipped': skipped_count,
                'total': total_prizes,
                'message': f'Added {added_count} new prizes, skipped {skipped_count} duplicates. Total: {total_prizes} prizes.'
            }

            logger.info(f"✅ Poll complete: {result['message']}")
            return result

        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}", exc_info=True)

            # Mark session as error
            session.mark_error(str(e))

            return {
                'success': False,
                'added': 0,
                'skipped': 0,
                'total': 0,
                'message': f'Error during scraping: {str(e)}'
            }

    @classmethod
    def poll_active_sessions(cls):
        """
        Poll all active scraping sessions (called by background worker)
        """
        active_sessions = LiveScrapingSession.objects.filter(
            is_active=True,
            status='scraping'
        )

        logger.info(f"🔍 Found {active_sessions.count()} active scraping sessions")

        for session in active_sessions:
            # Check for timeout (auto-stop after 2 hours)
            if session.started_at:
                elapsed = timezone.now() - session.started_at
                if elapsed.total_seconds() > 7200:  # 2 hours
                    logger.warning(f"⏰ Session {session.id} timed out after 2 hours")
                    session.mark_completed()
                    continue

            # Scrape and merge
            result = cls.scrape_and_merge(session)

            if not result['success']:
                logger.error(f"❌ Session {session.id} encountered error: {result['message']}")

    @classmethod
    def get_session_status(cls, lottery_result_id: int) -> Dict:
        """
        Get status of live scraping session for a lottery result

        Args:
            lottery_result_id: ID of the LotteryResult

        Returns:
            Dictionary with session status
        """
        try:
            lottery_result = LotteryResult.objects.get(id=lottery_result_id)

            if not hasattr(lottery_result, 'live_session'):
                return {
                    'has_session': False,
                    'status': 'idle',
                    'prizes_found': 0,
                    'poll_count': 0,
                    'message': 'No active scraping session'
                }

            session = lottery_result.live_session

            return {
                'has_session': True,
                'session_id': session.id,
                'status': session.status,
                'is_active': session.is_active,
                'prizes_found': session.prizes_found_count,
                'poll_count': session.poll_count,
                'last_polled_at': session.last_polled_at.isoformat() if session.last_polled_at else None,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'error_message': session.error_message,
                'message': f'{session.get_status_display()} - {session.prizes_found_count} prizes found'
            }

        except LotteryResult.DoesNotExist:
            return {
                'has_session': False,
                'status': 'error',
                'message': 'Lottery result not found'
            }
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return {
                'has_session': False,
                'status': 'error',
                'message': str(e)
            }
