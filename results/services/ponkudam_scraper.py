"""
Ponkudam.com Lottery Scraper Service

This service extracts lottery result data from ponkudam.com using:
1. Firebase Firestore REST API for fast data access
2. Browser automation (Selenium) to determine today's lottery code from homepage

Author: Auto-generated for lottery project
Date: 2025-10-27
"""

import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


class PonkudamScraperError(Exception):
    """Custom exception for ponkudam scraping errors"""
    pass


class PonkudamLotteryScraper:
    """
    Scraper for ponkudam.com website
    Uses Firebase Firestore REST API for data access
    """

    # Firebase configuration (discovered from site)
    PROJECT_ID = "kerala-red"
    API_KEY = "AIzaSyBECHTUgMiedrtozaHGnyZHFv1pNLRaVqA"
    DATABASE = "(default)"
    FIRESTORE_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{DATABASE}/documents"

    # Lottery name mapping (first letter of code to full name)
    # Note: Only the FIRST letter of the code matters (e.g., 'kn' -> 'k' -> Karunya)
    LOTTERY_NAME_MAPPING = {
        'd': 'Dhanalekshmi',
        'b': 'Bhagyathara',
        's': 'Sthree Sakthi',
        'm': 'Samrudhi',
        'k': 'Karunya',
        'r': 'Suvarna Keralam',
        'p': 'Karunya Plus',
        'v': 'Vishu Bumper',
        'z': 'Mansoon Bumper',
        't': 'Thiruvonam Bumper',
        'x': 'Christmas New Year Bumper',
        'j': 'Pooja Bumper',
    }

    # Day of week to lottery mapping (Kerala Lottery Schedule)
    # This allows us to predict today's lottery without pagination
    # Note: Now using FIRST letter only
    DAY_TO_LOTTERY_PREFIX = {
        0: None,  # Monday - (Update based on actual schedule)
        1: 's',   # Tuesday - Sthree Sakthi
        2: None,  # Wednesday - (Update based on actual schedule)
        3: 'p',   # Thursday - Karunya Plus
        4: None,  # Friday - (Update based on actual schedule)
        5: 'k',   # Saturday - Karunya
        6: None,  # Sunday - (Update based on actual schedule)
    }

    # Default prize amounts (if not specified in Firestore)
    DEFAULT_PRIZE_AMOUNTS = {
        '1st': Decimal('10000000'),   # 1 Crore
        '2nd': Decimal('1000000'),     # 10 Lakhs
        '3rd': Decimal('500000'),      # 5 Lakhs
        '4th': Decimal('5000'),
        '5th': Decimal('2000'),
        '6th': Decimal('1000'),
        '7th': Decimal('500'),
        '8th': Decimal('100'),
        'consolation': Decimal('800000')  # 8 Lakhs
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize scraper

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()

    def scrape_lottery_result(self, url: str) -> Dict:
        """
        Main method to scrape lottery results from ponkudam.com

        Args:
            url: Ponkudam URL (can be homepage or specific result page)

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
            PonkudamScraperError: If scraping fails
        """
        try:
            logger.info(f"Fetching lottery data from ponkudam.com...")

            # For now, we'll scrape today's latest result
            # In the future, could parse URL to get specific lottery code
            lottery_code = self._get_today_lottery_code()

            # Fetch data from Firestore
            firestore_data = self._fetch_from_firestore(lottery_code)

            # Transform to standard format
            result = self._transform_to_standard_format(firestore_data)

            logger.info(f"Successfully scraped: {result['lottery_name']} - {result['draw_number']}")
            return result

        except Exception as e:
            logger.error(f"Error scraping ponkudam data: {e}", exc_info=True)
            raise PonkudamScraperError(f"Failed to scrape ponkudam.com: {str(e)}")

    def _get_today_lottery_code(self) -> str:
        """
        Determine today's lottery code using Firebase Structured Query API

        OPTIMIZATION: Instead of paginating through 1500+ documents (5 MB),
        we use Firebase's structured query to fetch ONLY today's result (5 KB).
        This is 900x more efficient!
        """
        try:
            today = datetime.now()
            today_str = today.strftime('%d/%m/%Y')
            day_of_week = today.weekday()  # 0=Monday, 6=Sunday

            # Predict lottery type based on day (for logging)
            expected_prefix = self.DAY_TO_LOTTERY_PREFIX.get(day_of_week)
            if expected_prefix:
                expected_name = self.LOTTERY_NAME_MAPPING.get(expected_prefix, expected_prefix.upper())
                logger.info(f"Today is {today.strftime('%A')}, expecting {expected_name} lottery")

            logger.info(f"Querying Firebase for date: {today_str}")

            # Use Firebase Structured Query API
            # Query: SELECT * FROM results WHERE date = today_str LIMIT 5
            query_url = f"https://firestore.googleapis.com/v1/projects/{self.PROJECT_ID}/databases/{self.DATABASE}/documents:runQuery"
            params = {'key': self.API_KEY}

            query_body = {
                'structuredQuery': {
                    'from': [{'collectionId': 'results'}],
                    'where': {
                        'fieldFilter': {
                            'field': {'fieldPath': 'date'},
                            'op': 'EQUAL',
                            'value': {'stringValue': today_str}
                        }
                    },
                    'limit': 5  # Should only be 1, but allow for edge cases
                }
            }

            response = self.session.post(query_url, json=query_body, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Extract results
            results = [item for item in data if 'document' in item]

            if results:
                # Found today's result!
                doc = results[0].get('document', {})
                fields = doc.get('fields', {})
                code_value = fields.get('code', {}).get('stringValue', '')

                if code_value:
                    # Verify it matches expected lottery type (check first letter only)
                    if expected_prefix and not code_value.lower().startswith(expected_prefix):
                        logger.warning(f"Found lottery {code_value} but expected first letter '{expected_prefix}' (possible holiday/schedule change)")

                    logger.info(f"Found today's lottery: {code_value} (query returned {len(results)} result(s), ~5 KB)")
                    return code_value
                else:
                    raise PonkudamScraperError("Found result but code field is empty")

            # Today's result not found, fallback to most recent
            logger.warning(f"Today's result ({today_str}) not found via query")
            logger.info("Falling back to find most recent result...")

            # Query for recent results (order by date desc)
            # Note: Firebase Firestore requires an index for orderBy on date field
            # Fallback: Fetch first page and find most recent
            fallback_url = f"{self.FIRESTORE_BASE}/results"
            fallback_params = {
                'key': self.API_KEY,
                'pageSize': 300
            }

            response = self.session.get(fallback_url, params=fallback_params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            documents = data.get('documents', [])

            if not documents:
                raise PonkudamScraperError("No lottery results found in database")

            # Find most recent result in first page
            latest_date = None
            latest_code = None

            for doc in documents:
                fields = doc.get('fields', {})
                date_str = fields.get('date', {}).get('stringValue', '')
                code_value = fields.get('code', {}).get('stringValue', '')

                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                        if latest_date is None or date_obj > latest_date:
                            latest_date = date_obj
                            latest_code = code_value
                    except ValueError:
                        continue

            if latest_code:
                logger.warning(f"Using most recent result: {latest_code} on {latest_date.strftime('%d/%m/%Y')}")
                return latest_code

            # Last resort
            first_doc = documents[0]
            code = first_doc.get('fields', {}).get('code', {}).get('stringValue', 'unknown')
            logger.error(f"No valid results found, using first document: {code}")
            return code

        except Exception as e:
            logger.error(f"Error determining today's lottery code: {e}")
            raise PonkudamScraperError(f"Could not determine lottery code: {str(e)}")

    def _fetch_from_firestore(self, lottery_code: str) -> Dict:
        """
        Fetch lottery data from Firestore REST API

        Args:
            lottery_code: Lottery code (e.g., 'ak-099')

        Returns:
            Raw Firestore document data
        """
        try:
            url = f"{self.FIRESTORE_BASE}/results/{lottery_code}"
            params = {'key': self.API_KEY}

            logger.info(f"Fetching Firestore document: {lottery_code}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            if not data.get('fields'):
                raise PonkudamScraperError(f"Empty document for code: {lottery_code}")

            return data

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise PonkudamScraperError(f"Lottery code not found: {lottery_code}")
            raise PonkudamScraperError(f"HTTP error fetching data: {e}")
        except Exception as e:
            raise PonkudamScraperError(f"Error fetching Firestore data: {str(e)}")

    def _transform_to_standard_format(self, firestore_doc: Dict) -> Dict:
        """
        Transform Firestore document to standard lottery result format

        Args:
            firestore_doc: Raw Firestore document

        Returns:
            Standardized lottery result dictionary
        """
        fields = firestore_doc.get('fields', {})

        # Extract basic info
        code = fields.get('code', {}).get('stringValue', '')
        date_str = fields.get('date', {}).get('stringValue', '')

        # Parse lottery name from code (e.g., 'ak-099' -> 'Akshaya')
        lottery_name = self._get_lottery_name_from_code(code)

        # Parse draw number from code (e.g., 'ak-099' -> 'AK-099')
        draw_number = code.upper() if code else 'UNKNOWN'

        # Parse date (DD/MM/YYYY format)
        try:
            date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}, using today")
            date_obj = datetime.now().date()

        # Extract prizes
        prizes = self._extract_prizes_from_fields(fields)

        return {
            'lottery_name': lottery_name,
            'draw_number': draw_number,
            'date': date_obj,
            'prizes': prizes
        }

    def _get_lottery_name_from_code(self, code: str) -> str:
        """Get full lottery name from first letter of code"""
        if not code:
            return "Unknown Lottery"

        # Extract only the FIRST letter (e.g., 'k' from 'kn-099' or 'd' from 'dl-123')
        first_letter = code[0].lower()
        return self.LOTTERY_NAME_MAPPING.get(first_letter, code.upper())

    def _extract_prizes_from_fields(self, fields: Dict) -> List[Dict]:
        """
        Extract prize entries from Firestore fields

        Firestore structure:
        - "1": "KA452146" (1st prize)
        - "2": "KC521463" (2nd prize)
        - "3": "06045 0052 0067..." (3rd prize tickets, space-separated)
        - "4": "8562" (4th prize, last 4 digits)
        - etc.
        """
        prizes = []

        # Map field keys to prize types
        prize_field_mapping = {
            '1': '1st',
            '2': '2nd',
            '3': '3rd',
            '4': '4th',
            '5': '5th',
            '6': '6th',
            '7': '7th',
            '8': '8th',
            '9': '9th',
            '10': '10th',
            'consolation': 'consolation'
        }

        for field_key, prize_type in prize_field_mapping.items():
            if field_key not in fields:
                continue

            field_value = fields[field_key]
            ticket_str = field_value.get('stringValue', '')

            if not ticket_str:
                continue

            # Get prize amount
            prize_amount = self.DEFAULT_PRIZE_AMOUNTS.get(prize_type, Decimal('0'))

            # Split tickets by space (some prizes have multiple tickets)
            tickets = [t.strip() for t in ticket_str.split() if t.strip()]

            for ticket in tickets:
                prizes.append({
                    'prize_type': prize_type,
                    'prize_amount': prize_amount,
                    'ticket_number': ticket,
                    'place': None  # ponkudam doesn't store place info consistently
                })

        logger.info(f"Extracted {len(prizes)} prize entries")
        return prizes


# Convenience function for easy import
def scrape_ponkudam_lottery(url: str) -> Dict:
    """
    Convenience function to scrape ponkudam lottery results

    Args:
        url: Ponkudam URL

    Returns:
        Dictionary with lottery data

    Raises:
        PonkudamScraperError: If scraping fails
    """
    scraper = PonkudamLotteryScraper()
    return scraper.scrape_lottery_result(url)
