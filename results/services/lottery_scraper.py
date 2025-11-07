"""
Kerala Lottery Web Scraper Service

This service extracts lottery result data from Kerala Lotteries website URLs
and structures the data for automatic database entry.

Author: Auto-generated for lottery project
Date: 2025-10-23
"""

import requests
from bs4 import BeautifulSoup
import re
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LotteryScraperError(Exception):
    """Custom exception for lottery scraping errors"""
    pass


class KeralaLotteryScraper:
    """
    Scraper for Kerala Lotteries website (keralalotteries.net)
    Extracts lottery results including prizes, amounts, and ticket numbers
    """

    # Mapping of website prize names to database prize types
    PRIZE_TYPE_MAPPING = {
        '1st prize': '1st',
        'first prize': '1st',
        '2nd prize': '2nd',
        'second prize': '2nd',
        '3rd prize': '3rd',
        'third prize': '3rd',
        '4th prize': '4th',
        'fourth prize': '4th',
        '5th prize': '5th',
        'fifth prize': '5th',
        '6th prize': '6th',
        'sixth prize': '6th',
        '7th prize': '7th',
        'seventh prize': '7th',
        '8th prize': '8th',
        'eighth prize': '8th',
        '9th prize': '9th',
        'ninth prize': '9th',
        '10th prize': '10th',
        'tenth prize': '10th',
        'consolation prize': 'consolation',
        'consolation': 'consolation',
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize scraper

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scrape_lottery_result(self, url: str) -> Dict:
        """
        Main method to scrape lottery results from URL

        Args:
            url: Kerala Lotteries result page URL

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
            LotteryScraperError: If scraping fails
        """
        try:
            # Fetch the page
            logger.info(f"Fetching lottery data from: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract lottery information
            lottery_name = self._extract_lottery_name(soup, url)
            draw_number = self._extract_draw_number(soup, url)
            date = self._extract_date(soup, url)
            prizes = self._extract_prizes(soup)

            result = {
                'lottery_name': lottery_name,
                'draw_number': draw_number,
                'date': date,
                'prizes': prizes
            }

            logger.info(f"Successfully scraped: {lottery_name} - {draw_number} ({len(prizes)} prizes)")
            return result

        except requests.RequestException as e:
            logger.error(f"Network error while fetching {url}: {e}")
            raise LotteryScraperError(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            logger.error(f"Error scraping lottery data: {e}", exc_info=True)
            raise LotteryScraperError(f"Failed to parse lottery data: {str(e)}")

    def _extract_lottery_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract lottery name from page"""
        try:
            # PRIORITIZE URL extraction (most reliable for multi-lottery pages)
            # URL pattern: .../karunya-plus-kerala-lottery-result-... or .../dhanalekshmi-kerala-lottery-result-...
            match = re.search(r'/([a-z-]+)-kerala-lottery-result', url, re.IGNORECASE)
            if match:
                name = match.group(1).replace('-', ' ').title()
                logger.info(f"Extracted lottery name from URL: {name}")
                return name

            # Try to find lottery name in title
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                # Pattern: "Date Lottery_Name DL-XX Lottery Result"
                # Example: "22-10-2025 Dhanalekshmi DL-23 Lottery Result"
                match = re.search(r'\d{1,2}-\d{1,2}-\d{4}\s+([A-Za-z\s]+?)(?:\s+[A-Z]{2}-\d+|\s+Lottery)', title_text, re.IGNORECASE)
                if match:
                    lottery_name = match.group(1).strip()
                    logger.info(f"Extracted lottery name from title: {lottery_name}")
                    return lottery_name

                # Fallback title pattern: "Lottery_Name Kerala Lottery Result..."
                match = re.search(r'^([A-Za-z\s]+?)\s+Kerala\s+Lottery', title_text, re.IGNORECASE)
                if match:
                    lottery_name = match.group(1).strip()
                    # Avoid generic names like "Kerala" or "Result"
                    if lottery_name.lower() not in ['kerala', 'result', 'results', 'lottery']:
                        logger.info(f"Extracted lottery name from title (fallback): {lottery_name}")
                        return lottery_name

            # Try h1 or h2 tags with "Today Dhanalekshmi Lottery"
            for tag in soup.find_all(['h1', 'h2', 'h3']):
                text = tag.get_text()
                if 'today' in text.lower() and 'lottery' in text.lower():
                    match = re.search(r'Today\s+([A-Za-z\s]+?)\s+Lottery', text, re.IGNORECASE)
                    if match:
                        lottery_name = match.group(1).strip()
                        logger.info(f"Extracted lottery name from heading: {lottery_name}")
                        return lottery_name

            raise LotteryScraperError("Could not extract lottery name from page")

        except LotteryScraperError:
            raise
        except Exception as e:
            logger.error(f"Error extracting lottery name: {e}")
            raise LotteryScraperError(f"Failed to extract lottery name: {str(e)}")

    def _extract_draw_number(self, soup: BeautifulSoup, url: str) -> str:
        """Extract draw number from page"""
        try:
            # PRIORITIZE URL extraction (e.g., dl-23-today or kn-594-today)
            match = re.search(r'-([a-z]{2})-(\d{1,4})-', url, re.IGNORECASE)
            if match:
                prefix = match.group(1).upper()
                number = match.group(2)
                draw_number = f"{prefix}-{number}"
                logger.info(f"Extracted draw number from URL: {draw_number}")
                return draw_number

            # Look for draw number patterns like "KN-594", "KN 594", "DL-23" in page content
            text_content = soup.get_text()

            # Pattern 1: XX-NNN or similar (prioritize exact lottery code from URL if known)
            match = re.search(r'([A-Z]{2,3})[\s-]*(\d{1,4})', text_content)
            if match:
                draw_number = f"{match.group(1)}-{match.group(2)}"
                logger.info(f"Extracted draw number from content: {draw_number}")
                return draw_number

            # Pattern 2: Draw No: 594 or Draw Number: 594
            match = re.search(r'Draw\s+(?:No|Number)[:\s]*(\d{3,4})', text_content, re.IGNORECASE)
            if match:
                return match.group(1)

            # Fallback: Extract from URL (loose pattern)
            match = re.search(r'[a-z]+-(\d{1,4})-', url, re.IGNORECASE)
            if match:
                return match.group(1)

            raise LotteryScraperError("Could not extract draw number from page")

        except Exception as e:
            logger.error(f"Error extracting draw number: {e}")
            raise LotteryScraperError(f"Failed to extract draw number: {str(e)}")

    def _extract_date(self, soup: BeautifulSoup, url: str) -> datetime.date:
        """Extract lottery date from page"""
        try:
            # PRIORITIZE URL extraction
            # Pattern 1: /2025/10/...-22-10-2025.html (day-month-year in filename)
            match = re.search(r'-(\d{1,2})-(\d{1,2})-(\d{4})\.html', url)
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                logger.info(f"Extracted date from URL filename: {year}-{month:02d}-{day:02d}")
                return datetime(year, month, day).date()

            # Pattern 2: /2025/10/... (year/month in path)
            match = re.search(r'/(\d{4})/(\d{1,2})/', url)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                # Try to get day from somewhere else in URL
                day_match = re.search(r'-(\d{1,2})\.html', url)
                day = int(day_match.group(1)) if day_match else 1
                logger.info(f"Extracted date from URL path: {year}-{month:02d}-{day:02d}")
                return datetime(year, month, day).date()

            # Pattern 2: Look for text patterns like "23-10-2025" or "23.10.2025"
            text_content = soup.get_text()
            match = re.search(r'(\d{1,2})[-./](\d{1,2})[-./](\d{4})', text_content)
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                return datetime(year, month, day).date()

            # Pattern 3: "Today" or extract from URL path
            match = re.search(r'/(\d{4})/(\d{1,2})/', url)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                # Try to get day from somewhere else in URL or default to 1
                day_match = re.search(r'-(\d{1,2})\.html', url)
                day = int(day_match.group(1)) if day_match else 1
                return datetime(year, month, day).date()

            raise LotteryScraperError("Could not extract date from page or URL")

        except ValueError as e:
            logger.error(f"Invalid date values: {e}")
            raise LotteryScraperError(f"Invalid date format: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting date: {e}")
            raise LotteryScraperError(f"Failed to extract date: {str(e)}")

    def _extract_prizes(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all prize entries from page using <strong> and <b> tags"""
        prizes = []

        try:
            # Try both <strong> and <b> tags as some sites use different tags
            strong_tags = soup.find_all(['strong', 'b'])

            logger.info(f"Found {len(strong_tags)} bold tags to process")

            current_prize_type = None
            current_amount = None
            skip_next = False
            found_1st = False
            found_3rd = False

            for i, strong_tag in enumerate(strong_tags):
                if skip_next:
                    skip_next = False
                    continue

                text = strong_tag.get_text().strip()

                # Skip empty or very short tags
                if len(text) < 3:
                    continue

                # Check if this strong tag contains a prize type header
                prize_type = self._identify_prize_type(text)

                if prize_type:
                    # This is a prize header (e.g., "1st Prize ₹1,00,00,000/-")
                    current_prize_type = prize_type
                    current_amount = self._extract_amount_from_text(text)

                    # Track if we've found specific prizes (for 2nd prize detection)
                    if prize_type == '1st':
                        found_1st = True
                    elif prize_type == '3rd':
                        found_3rd = True

                    logger.debug(f"Found prize header: {text[:50]}, Type: {prize_type}, Amount: {current_amount}")

                    # For 1st, 2nd, 3rd prizes, the next <strong> tag contains the ticket
                    if current_prize_type in ['1st', '2nd', '3rd', 'consolation']:
                        # Look for the next strong tag (skip a few if they're empty)
                        for j in range(i + 1, min(i + 5, len(strong_tags))):
                            next_strong = strong_tags[j]
                            next_text = next_strong.get_text().strip()

                            if len(next_text) < 3:
                                continue

                            # Skip tags that are just markers
                            if next_text in ['---', '(Common to all series)', '(Remaining all series)']:
                                continue

                            # Extract ticket number from next strong tag
                            ticket_numbers = self._extract_ticket_numbers(next_text)
                            if ticket_numbers:
                                # Extract place from parentheses like "(KOLLAM)"
                                place_match = re.search(r'\((.*?)\)', next_text)
                                place = place_match.group(1) if place_match else None

                                prizes.append({
                                    'prize_type': current_prize_type,
                                    'prize_amount': current_amount,
                                    'ticket_number': ticket_numbers[0],
                                    'place': place
                                })

                                logger.debug(f"Added prize: {current_prize_type} - {ticket_numbers[0]}")
                                skip_next = True
                                break

                # SPECIAL CASE: 2nd prize often has NO header
                # Look for pattern: "(Common to all series)" followed by ticket number BETWEEN 1st and 3rd prize
                elif found_1st and not found_3rd and '(Common to all series)' in text:
                    # Check next tag for 2nd prize ticket
                    if i + 1 < len(strong_tags):
                        next_strong = strong_tags[i + 1]
                        next_text = next_strong.get_text().strip()

                        # Make sure it's not agent info or another marker
                        if 'Agent' not in next_text and len(next_text) > 5:
                            ticket_numbers = self._extract_ticket_numbers(next_text)
                            if ticket_numbers:
                                place_match = re.search(r'\((.*?)\)', next_text)
                                place = place_match.group(1) if place_match else None

                                # Default 2nd prize amount (₹10,00,000 for Karunya Plus)
                                amount_2nd = Decimal('1000000')  # Default, will be updated if header found

                                prizes.append({
                                    'prize_type': '2nd',
                                    'prize_amount': amount_2nd,
                                    'ticket_number': ticket_numbers[0],
                                    'place': place
                                })

                                logger.debug(f"Found 2nd prize (no header): {ticket_numbers[0]}")
                                skip_next = True

            # For 4th-10th prizes, we need to extract from text nodes
            # These prizes have format like:
            # <strong>4th Prize ₹5,000/-</strong>
            # <em>(Last Four digits to be drawn 19 times)</em>
            # 0691  0721  0754  1065  1315  ...

            # Find all text content after each prize header
            for i, strong_tag in enumerate(strong_tags):
                text = strong_tag.get_text().strip()
                prize_type = self._identify_prize_type(text)

                if prize_type and prize_type not in ['1st', '2nd', '3rd', 'consolation']:
                    # This is a 4th-10th prize
                    amount = self._extract_amount_from_text(text)

                    if not amount:
                        continue

                    # Get all text that follows this strong tag
                    # Kerala lottery structure: b > span > div, and tickets are in div siblings
                    # Try grandparent first (most common), then parent, then tag itself
                    start_elem = strong_tag
                    if strong_tag.parent:
                        if strong_tag.parent.parent and strong_tag.parent.parent.name in ['div', 'p']:
                            start_elem = strong_tag.parent.parent  # Use grandparent
                        elif strong_tag.parent.name in ['span', 'div']:
                            start_elem = strong_tag.parent  # Use parent

                    next_text = ''
                    next_elem = start_elem.next_sibling

                    # Look through up to 50 siblings to get all ticket numbers
                    # Some pages have messy HTML with closing tags breaking sibling chains
                    sibling_count = 0
                    while next_elem and sibling_count < 50:
                        # Stop if we hit another prize header
                        if hasattr(next_elem, 'name'):
                            elem_text = next_elem.get_text() if hasattr(next_elem, 'get_text') else ''
                            if self._identify_prize_type(elem_text):
                                logger.debug(f"Stopping at next prize header: {elem_text[:30]}")
                                break

                        # Collect text
                        if isinstance(next_elem, str):
                            next_text += next_elem
                        elif hasattr(next_elem, 'get_text'):
                            next_text += ' ' + next_elem.get_text()

                        next_elem = next_elem.next_sibling
                        sibling_count += 1

                    logger.debug(f"Collected text for {prize_type} from {sibling_count} siblings: {next_text[:100]}...")

                    # Extract all ticket numbers from this text
                    ticket_numbers = self._extract_ticket_numbers(next_text)

                    # If no tickets found in siblings, try finding next div with numbers in parent's siblings
                    # But be careful not to grab numbers from the NEXT prize
                    if not ticket_numbers and start_elem.parent:
                        parent_sibling = start_elem.parent.next_sibling
                        search_count = 0
                        collected_parent_text = ''

                        while parent_sibling and search_count < 20:
                            if hasattr(parent_sibling, 'get_text'):
                                sibling_text = parent_sibling.get_text()
                                # STOP if we hit another prize header (different prize type)
                                detected_type = self._identify_prize_type(sibling_text)
                                if detected_type and detected_type != prize_type:
                                    logger.debug(f"Stopping parent search at {detected_type} prize header")
                                    break
                                # Collect text
                                collected_parent_text += ' ' + sibling_text
                            parent_sibling = parent_sibling.next_sibling
                            search_count += 1

                        # Extract all numbers from collected text
                        temp_numbers = self._extract_ticket_numbers(collected_parent_text)
                        if temp_numbers:
                            ticket_numbers = temp_numbers
                            logger.debug(f"Found {len(ticket_numbers)} numbers in parent siblings for {prize_type}")

                    logger.info(f"Found {len(ticket_numbers)} tickets for {prize_type} prize")

                    for ticket_num in ticket_numbers:
                        prizes.append({
                            'prize_type': prize_type,
                            'prize_amount': amount,
                            'ticket_number': ticket_num,
                            'place': None
                        })

            if not prizes:
                logger.warning("No prizes extracted, trying fallback method")
                # Try a different approach - maybe the page uses a different structure
                prizes = self._extract_prizes_fallback(soup)

            if not prizes:
                raise LotteryScraperError("No prizes could be extracted from page. The page may not contain result data yet.")

            logger.info(f"Extracted {len(prizes)} prize entries")
            return prizes

        except LotteryScraperError:
            raise
        except Exception as e:
            logger.error(f"Error extracting prizes: {e}", exc_info=True)
            raise LotteryScraperError(f"Failed to extract prizes: {str(e)}")

    def _extract_prizes_fallback(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback method to extract prizes from plain text"""
        prizes = []

        try:
            # Get all text and try to find patterns
            text_content = soup.get_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]

            current_prize_type = None
            current_amount = None

            for i, line in enumerate(lines):
                # Check for prize type
                prize_type = self._identify_prize_type(line)

                if prize_type:
                    current_prize_type = prize_type
                    current_amount = self._extract_amount_from_text(line)
                    continue

                # Look for ticket numbers
                if current_prize_type and current_amount:
                    tickets = self._extract_ticket_numbers(line)

                    for ticket in tickets:
                        place = None
                        if current_prize_type in ['1st', '2nd', '3rd']:
                            # Try to find place in next couple of lines
                            for j in range(i, min(i + 3, len(lines))):
                                if re.search(r'\([A-Z\s]+\)', lines[j]):
                                    place_match = re.search(r'\(([^)]+)\)', lines[j])
                                    if place_match:
                                        place = place_match.group(1)
                                        break

                        prizes.append({
                            'prize_type': current_prize_type,
                            'prize_amount': current_amount,
                            'ticket_number': ticket,
                            'place': place
                        })

            return prizes

        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return []

    def _identify_prize_type(self, text: str) -> Optional[str]:
        """Identify if text contains a prize type"""
        text_lower = text.lower().strip()

        for key, value in self.PRIZE_TYPE_MAPPING.items():
            if key in text_lower:
                return value

        return None

    def _extract_amount_from_text(self, text: str) -> Optional[Decimal]:
        """Extract monetary amount from text"""
        try:
            # Remove currency symbols and markers, but keep spaces initially
            # Patterns: ₹1,00,00,000 or Rs. 1,00,00,000 or 10000000
            text_clean = text.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace('/-', '')
            text_clean = text_clean.replace('[', ' ').replace(']', ' ')  # Remove brackets

            # Find number patterns WITH commas (look for amounts with at least 3 digits or commas)
            # This avoids matching prize numbers like "1st", "2nd", "3rd"
            match = re.search(r'([\d,]{3,}(?:\.\d{2})?)', text_clean)
            if match:
                amount_str = match.group(1)
                # Remove commas after extracting
                amount_str = amount_str.replace(',', '')
                # Convert to Decimal
                amount = Decimal(amount_str)
                logger.debug(f"Extracted amount {amount} from '{text[:50]}'")
                return amount

            return None

        except Exception as e:
            logger.debug(f"Failed to extract amount from '{text}': {e}")
            return None

    def _extract_ticket_numbers(self, text: str) -> List[str]:
        """Extract ticket numbers from text line"""
        ticket_numbers = []

        # Pattern 1: Series with 6-digit number (PU 539160, PS539160, PU539160)
        pattern1 = re.findall(r'\b([A-Z]{2}\s*\d{6})\b', text)
        for match in pattern1:
            # Normalize: Format as XXNNNNNN (e.g., PU539160)
            ticket_num = re.sub(r'([A-Z]+)\s+(\d+)', r'\1\2', match)
            ticket_numbers.append(ticket_num)

        # Pattern 2: Just 6-digit numbers without series (539160)
        if not ticket_numbers:
            pattern2 = re.findall(r'\b(\d{6})\b', text)
            # Filter out numbers that might be amounts (like 100000, 500000)
            for num in pattern2:
                # Skip if it looks like a common prize amount
                if num not in ['100000', '500000', '300000', '200000', '150000']:
                    ticket_numbers.append(num)

        # Pattern 3: Last 4 digits for lower prizes (0691, 1315, 2033, 2081, etc.)
        # These are typically for 4th-10th prizes
        if not ticket_numbers:
            pattern3 = re.findall(r'\b(\d{4})\b', text)
            # Filter out ONLY actual years (2020-2030 range), not ticket numbers like 2033
            for num in pattern3:
                num_int = int(num)
                # Skip only if it's a likely year (2020-2030)
                if not (2020 <= num_int <= 2030):
                    ticket_numbers.append(num)
                # Also include numbers starting with 20 if they're not in year range
                elif num_int > 2030:
                    ticket_numbers.append(num)

        return ticket_numbers

    def _extract_place_from_context(self, lines: List[str], current_index: int) -> Optional[str]:
        """Extract place/location from context (for 1st, 2nd, 3rd prizes)"""
        # Look in next 2-3 lines for place names
        for i in range(current_index, min(current_index + 4, len(lines))):
            line = lines[i]
            # If line contains location indicators like city names, districts, etc.
            if re.search(r'\b(Agent|District|Kollam|Kochi|Thiruvananthapuram|Kozhikode|Palakkad)\b', line, re.IGNORECASE):
                # Remove extra whitespace and return
                return line.strip()[:100]  # Limit to 100 chars

        return None

    def _extract_prizes_from_html_structure(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Alternative method: Extract prizes using HTML structure
        (tables, divs, lists, etc.)
        """
        prizes = []

        # Try to find prize information in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # First cell might be prize type, second might be amount, third ticket number
                    for cell in cells:
                        text = cell.get_text().strip()
                        prize_type = self._identify_prize_type(text)
                        if prize_type:
                            # Found a prize type, extract details from this row
                            amount = None
                            ticket_num = None

                            for c in cells:
                                c_text = c.get_text().strip()
                                if not amount:
                                    amount = self._extract_amount_from_text(c_text)
                                tickets = self._extract_ticket_numbers(c_text)
                                if tickets:
                                    ticket_num = tickets[0]

                            if prize_type and amount and ticket_num:
                                prizes.append({
                                    'prize_type': prize_type,
                                    'prize_amount': amount,
                                    'ticket_number': ticket_num,
                                    'place': None
                                })

        return prizes

    def match_lottery_name(self, scraped_name: str, existing_lotteries: List[Tuple[int, str]]) -> Optional[int]:
        """
        Match scraped lottery name to existing lottery in database

        Args:
            scraped_name: Lottery name extracted from website
            existing_lotteries: List of (id, name) tuples from database

        Returns:
            Lottery ID if match found, None otherwise
        """
        scraped_name_clean = scraped_name.lower().strip()

        # Exact match
        for lottery_id, lottery_name in existing_lotteries:
            if lottery_name.lower().strip() == scraped_name_clean:
                return lottery_id

        # Partial match (contains)
        for lottery_id, lottery_name in existing_lotteries:
            if scraped_name_clean in lottery_name.lower() or lottery_name.lower() in scraped_name_clean:
                return lottery_id

        # Fuzzy match (remove common words and compare)
        common_words = ['kerala', 'lottery', 'bumper', 'special']
        scraped_tokens = [w for w in scraped_name_clean.split() if w not in common_words]

        for lottery_id, lottery_name in existing_lotteries:
            lottery_tokens = [w for w in lottery_name.lower().split() if w not in common_words]
            # If any significant token matches
            if any(token in lottery_tokens for token in scraped_tokens):
                return lottery_id

        return None


# Convenience function for easy import
def scrape_kerala_lottery(url: str) -> Dict:
    """
    Convenience function to scrape Kerala lottery results

    Args:
        url: Kerala Lotteries result page URL

    Returns:
        Dictionary with lottery data

    Raises:
        LotteryScraperError: If scraping fails
    """
    scraper = KeralaLotteryScraper()
    return scraper.scrape_lottery_result(url)
