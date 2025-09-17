"""
LinkedIn scraper for lead generation
Note: This is a simplified implementation. LinkedIn has strict anti-scraping measures.
In production, consider using LinkedIn's official API or Sales Navigator.
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from urllib.parse import quote_plus

from .base import BaseScraper
from ..models import ScrapedLead, ScrapingSource

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn company and people data"""
    
    @property
    def source_name(self) -> ScrapingSource:
        return ScrapingSource.LINKEDIN
    
    def build_search_url(self, query: str, location: str = None, page: int = 0) -> str:
        """Build LinkedIn search URL"""
        
        # LinkedIn company search URL
        base_url = "https://www.linkedin.com/search/results/companies/"
        
        # Build query parameters
        params = []
        params.append(f"keywords={quote_plus(query)}")
        
        if location:
            params.append(f"geoUrn={quote_plus(location)}")
        
        if page > 0:
            params.append(f"page={page + 1}")
        
        url = f"{base_url}?{'&'.join(params)}"
        
        return url
    
    async def scrape_leads(self) -> AsyncGenerator[ScrapedLead, None]:
        """Scrape leads from LinkedIn"""
        
        logger.info(f"Starting LinkedIn scraping for: {self.config.search_query}")
        
        # Note: LinkedIn has strong anti-scraping measures
        # This is a simplified implementation for demonstration
        # In production, you should:
        # 1. Use LinkedIn's official API
        # 2. Use LinkedIn Sales Navigator API
        # 3. Use a professional scraping service
        # 4. Implement proper session management and CAPTCHA handling
        
        try:
            search_url = self.build_search_url(
                self.config.search_query,
                self.config.location
            )
            
            logger.info(f"Searching LinkedIn: {search_url}")
            
            # Make request with special headers for LinkedIn
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = await self.make_request(search_url, headers=headers)
            
            if not response:
                logger.warning("Failed to get LinkedIn search results - likely blocked")
                self.warnings.append("LinkedIn access blocked - consider using official API")
                return
            
            html_content = await response.text()
            
            # Check if we're blocked or redirected to login
            if 'sign-in' in html_content.lower() or 'login' in html_content.lower():
                logger.warning("LinkedIn requires authentication")
                self.warnings.append("LinkedIn requires authentication - consider using official API")
                return
            
            soup = self.parse_html(html_content)
            
            # Extract company listings
            companies = await self.extract_companies_from_html(soup, search_url)
            
            for company in companies:
                if self.scraped_count >= self.config.max_results:
                    break
                
                if not self.should_skip_lead(company):
                    lead = self.create_scraped_lead(company, search_url)
                    
                    if await self.validate_lead_data(lead):
                        self.scraped_count += 1
                        yield lead
                        
                        logger.debug(f"Scraped LinkedIn lead: {lead.company}")
                        
                        # Add delay between leads
                        await asyncio.sleep(2.0)  # Longer delay for LinkedIn
            
            logger.info(f"LinkedIn scraping completed. Found {self.scraped_count} leads")
            
        except Exception as e:
            logger.error(f"Error in LinkedIn scraping: {e}")
            self.errors.append(f"LinkedIn scraping error: {str(e)}")
    
    async def extract_companies_from_html(self, soup, source_url: str) -> list:
        """Extract company information from LinkedIn HTML"""
        
        companies = []
        
        try:
            # LinkedIn uses dynamic loading, so static HTML parsing is limited
            # Look for company result containers
            company_selectors = [
                '.search-result__wrapper',
                '.entity-result',
                '.search-entity-result',
                '[data-entity-urn*="company"]'
            ]
            
            company_elements = []
            for selector in company_selectors:
                elements = soup.select(selector)
                if elements:
                    company_elements = elements
                    break
            
            logger.info(f"Found {len(company_elements)} potential company elements")
            
            for element in company_elements[:self.config.max_results]:
                company_data = await self.extract_company_data(element)
                
                if company_data and company_data.get('company'):
                    companies.append(company_data)
                    
                    if len(companies) >= self.config.max_results:
                        break
            
        except Exception as e:
            logger.error(f"Error extracting companies from LinkedIn HTML: {e}")
            self.errors.append(f"LinkedIn HTML extraction error: {str(e)}")
        
        return companies
    
    async def extract_company_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract company data from a LinkedIn company element"""
        
        try:
            company_data = {}
            
            # Extract company name
            name_selectors = [
                '.entity-result__title-text a',
                '.search-result__result-link',
                'h3 a',
                '.entity-result__title-line a'
            ]
            
            company_name = None
            company_url = None
            
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    company_name = self.clean_text(name_elem.get_text())
                    company_url = name_elem.get('href')
                    break
            
            if not company_name:
                return None
            
            company_data['company'] = company_name
            company_data['linkedin_url'] = company_url
            
            # Extract company description/tagline
            desc_selectors = [
                '.entity-result__primary-subtitle',
                '.search-result__snippets',
                '.entity-result__summary'
            ]
            
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem:
                    description = self.clean_text(desc_elem.get_text())
                    if len(description) > 10:
                        company_data['description'] = description
                        break
            
            # Extract location
            location_selectors = [
                '.entity-result__secondary-subtitle',
                '.search-result__info .text-body-small'
            ]
            
            for selector in location_selectors:
                loc_elem = element.select_one(selector)
                if loc_elem:
                    location_text = self.clean_text(loc_elem.get_text())
                    # Filter out non-location text
                    if any(indicator in location_text.lower() for indicator in ['city', 'state', 'country', ',']):
                        company_data['location'] = location_text
                        break
            
            # Extract industry (if available)
            industry_elem = element.select_one('.entity-result__content .text-body-small')
            if industry_elem:
                industry_text = self.clean_text(industry_elem.get_text())
                if len(industry_text) < 100:  # Reasonable industry length
                    company_data['industry'] = industry_text
            
            # Extract employee count (if available)
            employee_indicators = ['employees', 'people', 'staff']
            full_text = element.get_text().lower()
            
            for indicator in employee_indicators:
                if indicator in full_text:
                    # Try to extract employee count
                    import re
                    pattern = rf'(\d+[\d,]*)\s*{indicator}'
                    match = re.search(pattern, full_text)
                    if match:
                        emp_count = match.group(1).replace(',', '')
                        company_data['employees'] = f"{emp_count}+"
                        break
            
            # Set default industry based on search query if not found
            if not company_data.get('industry') and self.config.industry:
                company_data['industry'] = self.config.industry
            
            # Add metadata
            company_data['source_type'] = 'linkedin'
            company_data['search_query'] = self.config.search_query
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error extracting LinkedIn company data: {e}")
            return None
    
    async def scrape_company_details(self, company_url: str) -> Dict[str, Any]:
        """Scrape additional details from LinkedIn company page"""
        
        try:
            # Note: This would require authentication in most cases
            response = await self.make_request(company_url)
            if not response:
                return {}
            
            html_content = await response.text()
            soup = self.parse_html(html_content)
            
            details = {}
            
            # Extract company size
            size_elem = soup.select_one('[data-test-id="about-us-company-size"]')
            if size_elem:
                details['employees'] = self.clean_text(size_elem.get_text())
            
            # Extract industry
            industry_elem = soup.select_one('[data-test-id="about-us-industry"]')
            if industry_elem:
                details['industry'] = self.clean_text(industry_elem.get_text())
            
            # Extract website
            website_elem = soup.select_one('a[data-test-id="about-us-website"]')
            if website_elem:
                details['website'] = website_elem.get('href')
            
            # Extract headquarters
            hq_elem = soup.select_one('[data-test-id="about-us-headquarters"]')
            if hq_elem:
                details['location'] = self.clean_text(hq_elem.get_text())
            
            # Extract company description
            desc_elem = soup.select_one('[data-test-id="about-us-description"]')
            if desc_elem:
                details['description'] = self.clean_text(desc_elem.get_text())
            
            return details
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn company details from {company_url}: {e}")
            return {}