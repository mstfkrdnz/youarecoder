"""
TCMB (Central Bank of Turkey) Exchange Rate Scraper

Fetches daily exchange rates from TCMB XML API for dynamic currency conversion.
Supports USD/TRY and EUR/TRY rates with automatic database updates.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal
import requests

from flask import current_app
from app import db
from app.models import ExchangeRate

logger = logging.getLogger(__name__)


class TCMBScraper:
    """TCMB exchange rate scraper and database updater."""

    # TCMB XML API endpoints
    TCMB_TODAY_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
    TCMB_DATE_URL = "https://www.tcmb.gov.tr/kurlar/{year}{month}/{day}{month}{year}.xml"

    def __init__(self):
        self.timeout = 10  # seconds
        self.retry_count = 3

    def fetch_daily_rates(self, target_date=None):
        """
        Fetch exchange rates from TCMB for a specific date.

        TCMB XML structure:
        <Tarih_Date Tarih="01.11.2025" Date="11/01/2025" Bulten_No="2025/212">
            <Currency CurrencyCode="USD" Kod="USD" CurrencyName="US DOLLAR">
                <Unit>1</Unit>
                <ForexBuying>34.2567</ForexBuying>
                <ForexSelling>34.3891</ForexSelling>
                ...
            </Currency>
        </Tarih_Date>

        Args:
            target_date: datetime.date object (default: today)

        Returns:
            dict: {
                'USD': Decimal('34.2567'),
                'EUR': Decimal('37.8912'),
                'date': date(2025, 11, 1)
            }

        Raises:
            requests.RequestException: If API call fails
            ValueError: If XML parsing fails
        """
        if target_date is None:
            target_date = date.today()
            url = self.TCMB_TODAY_URL
        else:
            url = self.TCMB_DATE_URL.format(
                year=target_date.strftime('%Y'),
                month=target_date.strftime('%m'),
                day=target_date.strftime('%d')
            )

        for attempt in range(self.retry_count):
            try:
                logger.info(f"Fetching TCMB rates for {target_date} from {url} (attempt {attempt + 1})")
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()

                # Parse XML
                root = ET.fromstring(response.content)
                rates = {}

                # Extract effective date from XML
                effective_date_str = root.get('Date')  # Format: "11/01/2025"
                if effective_date_str:
                    # Parse date from MM/DD/YYYY format
                    effective_date = datetime.strptime(effective_date_str, '%m/%d/%Y').date()
                else:
                    effective_date = target_date

                # Extract USD and EUR ForexBuying rates
                for currency in root.findall('Currency'):
                    code = currency.get('CurrencyCode')
                    if code in ['USD', 'EUR']:
                        # Use ForexBuying (Döviz Alış) rate
                        buying_rate = currency.find('ForexBuying')
                        if buying_rate is not None and buying_rate.text:
                            rates[code] = Decimal(buying_rate.text)

                if not rates:
                    raise ValueError("No USD/EUR rates found in TCMB XML")

                rates['date'] = effective_date

                logger.info(f"Fetched rates for {effective_date}: USD={rates.get('USD')}, EUR={rates.get('EUR')}")
                return rates

            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed to fetch TCMB rates: {str(e)}")
                if attempt == self.retry_count - 1:
                    logger.error(f"All {self.retry_count} attempts failed to fetch TCMB rates")
                    raise
            except ET.ParseError as e:
                logger.error(f"Failed to parse TCMB XML: {str(e)}")
                raise ValueError(f"XML parsing error: {str(e)}")

    def update_database(self, target_date=None):
        """
        Fetch latest rates and update database.

        This method:
        1. Fetches rates from TCMB XML API
        2. Updates or creates exchange rate records
        3. Commits changes to database

        Args:
            target_date: datetime.date object (default: today)

        Returns:
            dict: {
                'success': bool,
                'updated': ['USD', 'EUR'],
                'effective_date': date(2025, 11, 1),
                'errors': []
            }
        """
        if target_date is None:
            target_date = date.today()

        result = {
            'success': False,
            'updated': [],
            'effective_date': None,
            'errors': []
        }

        try:
            rates = self.fetch_daily_rates(target_date)
            effective_date = rates.pop('date')
            result['effective_date'] = effective_date

            for currency, rate in rates.items():
                try:
                    # Check if rate already exists
                    existing = ExchangeRate.query.filter_by(
                        source_currency=currency,
                        target_currency='TRY',
                        effective_date=effective_date
                    ).first()

                    if existing:
                        # Update existing rate
                        existing.rate = rate
                        existing.created_at = datetime.utcnow()
                        logger.info(f"Updated {currency}/TRY rate: {rate} for {effective_date}")
                    else:
                        # Create new rate
                        new_rate = ExchangeRate(
                            source_currency=currency,
                            target_currency='TRY',
                            rate=rate,
                            effective_date=effective_date,
                            source='TCMB'
                        )
                        db.session.add(new_rate)
                        logger.info(f"Created {currency}/TRY rate: {rate} for {effective_date}")

                    result['updated'].append(currency)

                except Exception as e:
                    error_msg = f"Failed to save {currency} rate: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

            db.session.commit()
            result['success'] = True
            logger.info(f"Exchange rates update complete for {effective_date}: {result}")

        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to update exchange rates: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result['errors'].append(error_msg)

        return result

    def get_rate_summary(self):
        """
        Get summary of current exchange rates in database.

        Returns:
            dict: {
                'usd': {'rate': 34.2567, 'date': '2025-11-01'},
                'eur': {'rate': 37.8912, 'date': '2025-11-01'},
                'total_records': 120
            }
        """
        summary = {
            'usd': None,
            'eur': None,
            'total_records': ExchangeRate.query.count()
        }

        usd_rate = ExchangeRate.get_latest_rate('USD', 'TRY')
        if usd_rate:
            summary['usd'] = {
                'rate': float(usd_rate.rate),
                'date': usd_rate.effective_date.isoformat()
            }

        eur_rate = ExchangeRate.get_latest_rate('EUR', 'TRY')
        if eur_rate:
            summary['eur'] = {
                'rate': float(eur_rate.rate),
                'date': eur_rate.effective_date.isoformat()
            }

        return summary
