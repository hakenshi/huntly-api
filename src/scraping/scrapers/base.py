"""
Base scraper class for all lead scrapers
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import aiohttp
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from ..models import ScrapedLead, ScrapingConfig, ScrapingSource

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all lead scrapers"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.scraped_count = 0
        self.errors = []
        self.warnings = []
        
        # Rate limiting
        self.last_request_time = 0
        self.request_delay = config.delay_between_requests
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
    
    @property
    @abstractmethod
    def source_name(self) -> ScrapingSource:
        """Return the source name for this scraper"""
        pass
    
    @abstractmethod
    async def scrape_leads(self) -> AsyncGenerator[ScrapedLead, None]:
        """
        Main scraping method - must be implemented by each scraper
        Yields ScrapedLead objects as they are found
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()
    
    async def start_session(self):
        """Initialize HTTP session"""
        headers = {
            'User-Agent': self.config.user_agent or random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        
        logger.info(f"Started {self.source_name} scraper session")
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info(f"Closed {self.source_name} scraper session")
    
    async def make_request(self, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Make HTTP request with rate limiting and error handling"""
        
        # Rate limiting
        await self._rate_limit()
        
        try:
            logger.debug(f"Making request to: {url}")
            
            # Add random delay to appear more human-like
            if self.config.delay_between_requests > 0:
                jitter = random.uniform(0.1, 0.5)
                await asyncio.sleep(jitter)
            
            async with self.session.get(url, **kwargs) as response:
                if response.status == 200:
                    return response
                elif response.status == 429:  # Rate limited
                    logger.warning(f"Rate limited by {url}, waiting...")
                    await asyncio.sleep(random.uniform(5, 15))
                    return await self.make_request(url, **kwargs)  # Retry once
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {url}")
            self.errors.append(f"Timeout for {url}")
            return None
        except Exception as e:
            logger.error(f"Request error for {url}: {e}")
            self.errors.append(f"Request error for {url}: {str(e)}")
            return None
    
    async def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove common unwanted characters
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        return text.strip()
    
    def extract_email(self, text: str) -> Optional[str]:
        """Extract email from text using regex"""
        import re
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        
        if matches:
            # Return the first valid-looking email
            for email in matches:
                if not any(skip in email.lower() for skip in ['noreply', 'no-reply', 'example', 'test']):
                    return email.lower()
        
        return None
    
    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        import re
        
        # Brazilian phone patterns
        phone_patterns = [
            r'\(\d{2}\)\s*\d{4,5}-?\d{4}',  # (11) 99999-9999
            r'\d{2}\s*\d{4,5}-?\d{4}',      # 11 99999-9999
            r'\+55\s*\d{2}\s*\d{4,5}-?\d{4}', # +55 11 99999-9999
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None
    
    def calculate_confidence_score(self, lead_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on data completeness and quality"""
        score = 0.0
        
        # Required fields scoring
        if lead_data.get('company'):
            score += 0.3
        if lead_data.get('email'):
            score += 0.2
        if lead_data.get('phone'):
            score += 0.15
        if lead_data.get('website'):
            score += 0.1
        
        # Optional but valuable fields
        if lead_data.get('industry'):
            score += 0.1
        if lead_data.get('location'):
            score += 0.05
        if lead_data.get('description'):
            score += 0.05
        if lead_data.get('employees'):
            score += 0.05
        
        return min(score, 1.0)
    
    def create_scraped_lead(self, data: Dict[str, Any], source_url: str = None) -> ScrapedLead:
        """Create ScrapedLead object from scraped data"""
        
        # Calculate confidence score
        confidence = self.calculate_confidence_score(data)
        
        # Extract keywords from description and company name
        keywords = []
        if data.get('description'):
            # Simple keyword extraction - could be enhanced with NLP
            words = data['description'].lower().split()
            keywords.extend([w for w in words if len(w) > 3 and w.isalpha()])
        
        if data.get('company'):
            company_words = data['company'].lower().split()
            keywords.extend([w for w in company_words if len(w) > 2])
        
        # Remove duplicates and limit
        keywords = list(set(keywords))[:10]
        
        return ScrapedLead(
            company=data.get('company', ''),
            contact=data.get('contact'),
            email=data.get('email'),
            phone=data.get('phone'),
            website=data.get('website'),
            industry=data.get('industry'),
            location=data.get('location'),
            address=data.get('address'),
            description=data.get('description'),
            revenue=data.get('revenue'),
            employees=data.get('employees'),
            founded_year=data.get('founded_year'),
            linkedin_url=data.get('linkedin_url'),
            facebook_url=data.get('facebook_url'),
            twitter_url=data.get('twitter_url'),
            source=self.source_name,
            source_url=source_url,
            scraped_at=datetime.now(),
            confidence_score=confidence,
            raw_data=data,
            keywords=keywords,
            tags=data.get('tags', [])
        )
    
    def should_skip_lead(self, lead_data: Dict[str, Any]) -> bool:
        """Check if lead should be skipped based on config filters"""
        
        # Check required fields
        for field in self.config.required_fields:
            if not lead_data.get(field):
                return True
        
        # Check employee count filters
        if self.config.min_employees or self.config.max_employees:
            employees_str = lead_data.get('employees', '')
            if employees_str:
                try:
                    # Extract number from employee string (e.g., "50-100" -> 75)
                    import re
                    numbers = re.findall(r'\d+', employees_str)
                    if numbers:
                        emp_count = int(numbers[0])  # Use first number as estimate
                        
                        if self.config.min_employees and emp_count < self.config.min_employees:
                            return True
                        if self.config.max_employees and emp_count > self.config.max_employees:
                            return True
                except:
                    pass
        
        return False
    
    async def validate_lead_data(self, lead: ScrapedLead) -> bool:
        """Validate scraped lead data quality"""
        
        # Basic validation
        if not lead.company or len(lead.company.strip()) < 2:
            return False
        
        # Email validation
        if lead.email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, lead.email):
                lead.email = None  # Remove invalid email
        
        # Website validation
        if lead.website:
            try:
                parsed = urlparse(str(lead.website))
                if not parsed.scheme or not parsed.netloc:
                    lead.website = None
            except:
                lead.website = None
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        return {
            "scraped_count": self.scraped_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[-5:],  # Last 5 errors
            "warnings": self.warnings[-5:]  # Last 5 warnings
        }