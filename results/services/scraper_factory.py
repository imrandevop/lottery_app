"""
Scraper Factory

Factory pattern to create appropriate scraper based on URL domain.
Supports multiple lottery result websites with a unified interface.

Author: Auto-generated for lottery project
Date: 2025-10-27
"""

from typing import Dict
import logging

from .lottery_scraper import (
    KeralaLotteryScraper,
    LotteryScraperError
)
from .ponkudam_scraper import (
    PonkudamLotteryScraper,
    PonkudamScraperError
)

logger = logging.getLogger(__name__)


class ScraperFactoryError(Exception):
    """Custom exception for scraper factory errors"""
    pass


class ScraperFactory:
    """
    Factory to create appropriate scraper based on URL
    """

    # Supported domains and their scraper classes
    SCRAPER_MAPPING = {
        'keralalotteries.net': KeralaLotteryScraper,
        'ponkudam.com': PonkudamLotteryScraper,
    }

    @classmethod
    def get_scraper(cls, url: str):
        """
        Returns appropriate scraper instance based on URL domain

        Args:
            url: Lottery result URL

        Returns:
            Scraper instance (KeralaLotteryScraper or PonkudamLotteryScraper)

        Raises:
            ScraperFactoryError: If domain is not supported
        """
        if not url:
            raise ScraperFactoryError("URL cannot be empty")

        url_lower = url.lower()

        # Check each supported domain
        for domain, scraper_class in cls.SCRAPER_MAPPING.items():
            if domain in url_lower:
                logger.info(f"Selected {scraper_class.__name__} for domain: {domain}")
                return scraper_class()

        # No matching scraper found
        supported_domains = ', '.join(cls.SCRAPER_MAPPING.keys())
        raise ScraperFactoryError(
            f"Unsupported domain in URL: {url}. "
            f"Supported domains: {supported_domains}"
        )

    @classmethod
    def scrape_lottery_result(cls, url: str) -> Dict:
        """
        Convenience method to scrape any supported lottery URL

        Args:
            url: Lottery result URL (keralalotteries.net or ponkudam.com)

        Returns:
            Dictionary containing:
            {
                'lottery_name': str,
                'draw_number': str,
                'date': datetime.date,
                'prizes': List[{
                    'prize_type': str,
                    'prize_amount': Decimal,
                    'ticket_number': str,
                    'place': Optional[str]
                }]
            }

        Raises:
            ScraperFactoryError: If domain is not supported
            LotteryScraperError: If Kerala Lotteries scraping fails
            PonkudamScraperError: If Ponkudam scraping fails
        """
        try:
            scraper = cls.get_scraper(url)
            return scraper.scrape_lottery_result(url)
        except (LotteryScraperError, PonkudamScraperError) as e:
            # Re-raise scraper-specific errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in scraper factory: {e}", exc_info=True)
            raise ScraperFactoryError(f"Scraping failed: {str(e)}")

    @classmethod
    def get_supported_domains(cls) -> list:
        """
        Get list of supported domains

        Returns:
            List of supported domain names
        """
        return list(cls.SCRAPER_MAPPING.keys())

    @classmethod
    def is_supported_url(cls, url: str) -> bool:
        """
        Check if URL is from a supported domain

        Args:
            url: URL to check

        Returns:
            True if supported, False otherwise
        """
        if not url:
            return False

        url_lower = url.lower()
        return any(domain in url_lower for domain in cls.SCRAPER_MAPPING.keys())
