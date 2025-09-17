"""
Google Maps scraper for lead generation
Scrapes business listings from Google Maps search results
"""

import asyncio
import logging
import json
import re
from typing import AsyncGenerator, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin

from .base import BaseScraper
from ..models import ScrapedLead, ScrapingSource

logger = logging.getLogger(__name__)

class GoogleMapsScraper(BaseScraper):
    """Scraper for Google Maps business listings"""
    
    @property
    def source_name(self) -> ScrapingSource:
        return ScrapingSource.GOOGLE_MAPS
    
    def build_search_url(self, query: str, location: str = None, page: int = 0) -> str:
        """Build Google Maps search URL"""
        
        # Combine query with location if provided
        search_term = query
        if location:
            search_term = f"{query} {location}"
        
        # Encode search term
        encoded_query = quote_plus(search_term)
        
        # Google Maps search URL
        base_url = "https://www.google.com/maps/search/"
        url = f"{base_url}{encoded_query}"
        
        # Add pagination if needed (Google Maps uses different pagination)
        if page > 0:
            url += f"/@-23.5505199,-46.6333094,11z/data=!3m1!4b1!4m2!2m1!6e1?start={page * 20}"
        
        return url
    
    async def scrape_leads(self) -> AsyncGenerator[ScrapedLead, None]:
        """Scrape leads from Google Maps"""
        
        logger.info(f"Starting Google Maps scraping for: {self.config.search_query}")
        
        try:
            # Build search URL
            search_url = self.build_search_url(
                self.config.search_query,
                self.config.location
            )
            
            logger.info(f"Searching Google Maps: {search_url}")
            
            # Make initial request
            response = await self.make_request(search_url)
            if not response:
                logger.error("Failed to get Google Maps search results")
                return
            
            html_content = await response.text()
            soup = self.parse_html(html_content)
            
            # Extract business listings from the page
            # Note: Google Maps uses dynamic loading, so this is a simplified approach
            # In production, you might want to use Selenium or similar for full JS rendering
            
            businesses = await self.extract_businesses_from_html(soup, search_url)
            
            for business in businesses:
                if self.scraped_count >= self.config.max_results:
                    break
                
                if not self.should_skip_lead(business):
                    lead = self.create_scraped_lead(business, search_url)
                    
                    if await self.validate_lead_data(lead):
                        self.scraped_count += 1
                        yield lead
                        
                        logger.debug(f"Scraped lead: {lead.company}")
                        
                        # Add delay between leads
                        await asyncio.sleep(0.5)
            
            logger.info(f"Google Maps scraping completed. Found {self.scraped_count} leads")
            
        except Exception as e:
            logger.error(f"Error in Google Maps scraping: {e}")
            self.errors.append(f"Google Maps scraping error: {str(e)}")
    
    async def extract_businesses_from_html(self, soup, source_url: str) -> list:
        """Extract business information from Google Maps HTML"""
        
        businesses = []
        
        try:
            # Look for business listings in various possible containers
            # Google Maps HTML structure can vary, so we try multiple selectors
            
            business_selectors = [
                '[data-result-index]',  # Common business listing container
                '.section-result',      # Alternative container
                '[jsaction*="pane"]',   # Another possible container
                '.section-result-content'
            ]
            
            business_elements = []
            for selector in business_selectors:
                elements = soup.select(selector)
                if elements:
                    business_elements = elements
                    break
            
            if not business_elements:
                # Fallback: look for any elements that might contain business info
                business_elements = soup.find_all(['div', 'article'], 
                                                class_=re.compile(r'result|listing|business'))
            
            logger.info(f"Found {len(business_elements)} potential business elements")
            
            for element in business_elements[:self.config.max_results]:
                business_data = await self.extract_business_data(element)
                
                if business_data and business_data.get('company'):
                    businesses.append(business_data)
                    
                    if len(businesses) >= self.config.max_results:
                        break
            
        except Exception as e:
            logger.error(f"Error extracting businesses from HTML: {e}")
            self.errors.append(f"HTML extraction error: {str(e)}")
        
        return businesses
    
    async def extract_business_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract business data from a single business element"""
        
        try:
            business_data = {}
            
            # Extract company name
            name_selectors = [
                '[data-value="Name"]',
                '.section-result-title',
                'h3',
                '.fontHeadlineSmall',
                '[role="heading"]'
            ]
            
            company_name = None
            for selector in name_selectors:
                name_elem = element.select_one(selector)
                if name_elem:
                    company_name = self.clean_text(name_elem.get_text())
                    break
            
            if not company_name:
                return None
            
            business_data['company'] = company_name
            
            # Extract address/location
            address_selectors = [
                '[data-value="Address"]',
                '.section-result-location',
                '[data-item-id="address"]'
            ]
            
            for selector in address_selectors:
                addr_elem = element.select_one(selector)
                if addr_elem:
                    address = self.clean_text(addr_elem.get_text())
                    business_data['address'] = address
                    business_data['location'] = address
                    break
            
            # Extract phone number
            phone_selectors = [
                '[data-value="Phone number"]',
                'a[href^="tel:"]',
                '.section-result-phone-number'
            ]
            
            for selector in phone_selectors:
                phone_elem = element.select_one(selector)
                if phone_elem:
                    phone_text = phone_elem.get('href', '') or phone_elem.get_text()
                    phone = self.extract_phone(phone_text)
                    if phone:
                        business_data['phone'] = phone
                        break
            
            # Extract website
            website_selectors = [
                'a[data-value="Website"]',
                'a[href^="http"]:not([href*="google.com"])',
                '.section-result-action-container a'
            ]
            
            for selector in website_selectors:
                website_elem = element.select_one(selector)
                if website_elem:
                    website_url = website_elem.get('href')
                    if website_url and not 'google.com' in website_url:
                        business_data['website'] = website_url
                        break
            
            # Extract rating and reviews (can indicate business size/activity)
            rating_elem = element.select_one('[data-value="Rating"], .section-result-rating')
            if rating_elem:
                rating_text = rating_elem.get_text()
                # Extract rating number
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    business_data['rating'] = float(rating_match.group(1))
            
            # Extract business type/category
            category_selectors = [
                '[data-value="Category"]',
                '.section-result-details',
                '.section-result-type'
            ]
            
            for selector in category_selectors:
                cat_elem = element.select_one(selector)
                if cat_elem:
                    category = self.clean_text(cat_elem.get_text())
                    if category and len(category) < 100:  # Reasonable category length
                        business_data['industry'] = category
                        break
            
            # Try to extract additional info from text content
            full_text = element.get_text()
            
            # Look for email in the text
            email = self.extract_email(full_text)
            if email:
                business_data['email'] = email
            
            # Look for additional phone if not found
            if not business_data.get('phone'):
                phone = self.extract_phone(full_text)
                if phone:
                    business_data['phone'] = phone
            
            # Set default industry based on search query if not found
            if not business_data.get('industry') and self.config.industry:
                business_data['industry'] = self.config.industry
            
            # Add some metadata
            business_data['source_type'] = 'google_maps'
            business_data['search_query'] = self.config.search_query
            
            return business_data
            
        except Exception as e:
            logger.error(f"Error extracting business data: {e}")
            return None
    
    async def scrape_business_details(self, business_url: str) -> Dict[str, Any]:
        """Scrape additional details from individual business page"""
        
        try:
            response = await self.make_request(business_url)
            if not response:
                return {}
            
            html_content = await response.text()
            soup = self.parse_html(html_content)
            
            details = {}
            
            # Extract business hours
            hours_elem = soup.select_one('[data-value="Hours"]')
            if hours_elem:
                details['business_hours'] = self.clean_text(hours_elem.get_text())
            
            # Extract more detailed description
            desc_selectors = [
                '[data-section-id="overview"]',
                '.section-editorial-quote',
                '[data-value="Description"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = self.clean_text(desc_elem.get_text())
                    if len(description) > 50:  # Only meaningful descriptions
                        details['description'] = description
                        break
            
            # Extract additional contact info
            contact_section = soup.select_one('[data-section-id="contact"]')
            if contact_section:
                contact_text = contact_section.get_text()
                
                # Look for additional emails
                email = self.extract_email(contact_text)
                if email:
                    details['email'] = email
                
                # Look for additional phones
                phone = self.extract_phone(contact_text)
                if phone:
                    details['phone'] = phone
            
            return details
            
        except Exception as e:
            logger.error(f"Error scraping business details from {business_url}: {e}")
            return {}