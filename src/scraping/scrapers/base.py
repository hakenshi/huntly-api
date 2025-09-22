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
from ..robots_checker import robots_checker
from ..data_validator import lead_validator

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
        
        # Check robots.txt compliance if enabled
        if self.config.respect_robots_txt:
            can_fetch = await robots_checker.can_fetch(url, self.config.user_agent)
            if not can_fetch:
                logger.warning(f"Robots.txt disallows fetching {url}")
                self.warnings.append(f"Robots.txt disallows access to {url}")
                return None
            
            # Get recommended crawl delay from robots.txt
            robots_delay = await robots_checker.get_crawl_delay(url, self.config.user_agent)
            if robots_delay and robots_delay > self.request_delay:
                logger.info(f"Using robots.txt crawl delay of {robots_delay}s for {url}")
                self.request_delay = robots_delay
        
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
        
        # Enhance data before creating lead
        enhanced_data = self.enhance_lead_data(data)
        
        # Calculate confidence score
        confidence = self.calculate_confidence_score(enhanced_data)
        
        # Extract keywords from description and company name
        keywords = []
        if enhanced_data.get('description'):
            keywords.extend(self.extract_keywords_from_text(enhanced_data['description']))
        
        if enhanced_data.get('company'):
            company_words = enhanced_data['company'].lower().split()
            keywords.extend([w for w in company_words if len(w) > 2])
        
        # Remove duplicates and limit
        keywords = list(set(keywords))[:10]
        
        return ScrapedLead(
            company=enhanced_data.get('company', ''),
            contact=enhanced_data.get('contact'),
            email=enhanced_data.get('email'),
            phone=enhanced_data.get('phone'),
            website=enhanced_data.get('website'),
            industry=enhanced_data.get('industry'),
            location=enhanced_data.get('location'),
            address=enhanced_data.get('address'),
            description=enhanced_data.get('description'),
            revenue=enhanced_data.get('revenue'),
            employees=enhanced_data.get('employees'),
            founded_year=enhanced_data.get('founded_year'),
            linkedin_url=enhanced_data.get('linkedin_url'),
            facebook_url=enhanced_data.get('facebook_url'),
            twitter_url=enhanced_data.get('twitter_url'),
            source=self.source_name,
            source_url=source_url,
            scraped_at=datetime.now(),
            confidence_score=confidence,
            raw_data=enhanced_data,
            keywords=keywords,
            tags=enhanced_data.get('tags', [])
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
        """Validate scraped lead data quality using comprehensive validator"""
        
        # Use the comprehensive data validator
        validation_result = lead_validator.validate_lead(lead)
        
        # Log validation issues for debugging
        if validation_result.issues:
            logger.debug(f"Lead validation issues for {lead.company}: {validation_result.issues}")
        
        # Log suggestions for improvement
        if validation_result.suggestions:
            logger.debug(f"Lead improvement suggestions: {validation_result.suggestions}")
        
        # Update lead with enhanced data if available
        if validation_result.enhanced_data:
            for key, value in validation_result.enhanced_data.items():
                if not hasattr(lead, key):
                    # Add enhanced data to raw_data if not a direct field
                    lead.raw_data[key] = value
        
        # Update confidence score
        lead.confidence_score = validation_result.confidence_score
        
        return validation_result.is_valid
    
    def validate_email_format(self, email: str) -> bool:
        """Validate email format and check if it's a business email"""
        if not email:
            return False
        
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False
        
        # Check if it's likely a business email (not personal)
        personal_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'uol.com.br', 'terra.com.br', 'bol.com.br', 'ig.com.br'
        ]
        
        domain = email.split('@')[-1].lower()
        return domain not in personal_domains
    
    def clean_company_name(self, name: str) -> str:
        """Clean and normalize company name"""
        if not name:
            return ""
        
        # Remove common prefixes/suffixes
        name = name.strip()
        
        # Remove business type suffixes
        suffixes = ['ltda', 'ltd', 'inc', 'corp', 'sa', 'me', 'eireli', 'epp', 'llc']
        for suffix in suffixes:
            # Remove suffix with various formats
            import re
            pattern = rf'\b{re.escape(suffix)}\.?\b'
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        name = ' '.join(name.split())
        
        return name.strip()
    
    def enhance_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance lead data with additional processing"""
        enhanced = lead_data.copy()
        
        # Clean company name
        if enhanced.get('company'):
            enhanced['company'] = self.clean_company_name(enhanced['company'])
        
        # Validate and clean email
        if enhanced.get('email'):
            if not self.validate_email_format(enhanced['email']):
                enhanced['email'] = None
        
        # Normalize phone number
        if enhanced.get('phone'):
            enhanced['phone'] = self.normalize_phone_number(enhanced['phone'])
        
        # Validate website URL
        if enhanced.get('website'):
            if not self.is_valid_website_url(enhanced['website']):
                enhanced['website'] = None
        
        # Extract additional keywords from description
        if enhanced.get('description'):
            keywords = self.extract_keywords_from_text(enhanced['description'])
            enhanced['keywords'] = enhanced.get('keywords', []) + keywords
        
        return enhanced
    
    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number format"""
        if not phone:
            return None
        
        import re
        
        # Remove all non-digit characters except + at the beginning
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Brazilian phone number patterns
        if cleaned.startswith('+55'):
            # International format
            return cleaned
        elif len(cleaned) == 11 and cleaned.startswith(('11', '21', '31', '41', '51')):
            # Brazilian mobile with area code
            return f"+55{cleaned}"
        elif len(cleaned) == 10 and cleaned.startswith(('11', '21', '31', '41', '51')):
            # Brazilian landline with area code
            return f"+55{cleaned}"
        
        return phone  # Return original if can't normalize
    
    def is_valid_website_url(self, url: str) -> bool:
        """Check if website URL is valid and accessible"""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be http or https
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check domain validity
            domain = parsed.netloc.lower()
            
            # Skip common non-business domains
            skip_domains = [
                'google.com', 'facebook.com', 'linkedin.com', 'twitter.com',
                'instagram.com', 'youtube.com', 'wikipedia.org'
            ]
            
            for skip_domain in skip_domains:
                if skip_domain in domain:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def extract_keywords_from_text(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract relevant keywords from text"""
        if not text or len(text) < 10:
            return []
        
        import re
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use',
            'com', 'www', 'http', 'https', 'html', 'php', 'asp', 'jsp',
            'empresa', 'company', 'business', 'service', 'services', 'solutions'
        }
        
        # Filter out stop words and get unique keywords
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Count frequency and return most common
        from collections import Counter
        word_counts = Counter(keywords)
        
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    def detect_duplicate_leads(self, new_lead: Dict[str, Any], existing_leads: List[Dict[str, Any]]) -> bool:
        """Detect if a lead is a duplicate of existing leads"""
        
        for existing in existing_leads:
            # Check company name similarity
            if self.calculate_text_similarity(
                new_lead.get('company', ''), 
                existing.get('company', '')
            ) > 0.8:
                return True
            
            # Check exact email match
            if (new_lead.get('email') and existing.get('email') and 
                new_lead['email'].lower() == existing['email'].lower()):
                return True
            
            # Check exact phone match
            if (new_lead.get('phone') and existing.get('phone') and 
                new_lead['phone'] == existing['phone']):
                return True
            
            # Check website domain match
            if (new_lead.get('website') and existing.get('website')):
                new_domain = self.get_domain_from_url(new_lead['website'])
                existing_domain = self.get_domain_from_url(existing['website'])
                if new_domain and existing_domain and new_domain == existing_domain:
                    return True
        
        return False
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1 = self.clean_company_name(text1.lower())
        text2 = self.clean_company_name(text2.lower())
        
        # Simple word overlap calculation
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower().replace('www.', '')
        except:
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        return {
            "scraped_count": self.scraped_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[-5:],  # Last 5 errors
            "warnings": self.warnings[-5:]  # Last 5 warnings
        }