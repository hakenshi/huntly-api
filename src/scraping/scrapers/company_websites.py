"""
Company website scraper for lead generation
Scrapes contact information from company websites
"""

import asyncio
import logging
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

from .base import BaseScraper
from ..models import ScrapedLead, ScrapingSource

logger = logging.getLogger(__name__)

class CompanyWebsiteScraper(BaseScraper):
    """Scraper for extracting lead data from company websites"""
    
    @property
    def source_name(self) -> ScrapingSource:
        return ScrapingSource.COMPANY_WEBSITE
    
    async def scrape_leads(self) -> AsyncGenerator[ScrapedLead, None]:
        """Scrape leads from company websites"""
        
        logger.info(f"Starting company website scraping for: {self.config.search_query}")
        
        try:
            # First, find company websites using search engines
            websites = await self.find_company_websites()
            
            logger.info(f"Found {len(websites)} websites to scrape")
            
            for website_url in websites:
                if self.scraped_count >= self.config.max_results:
                    break
                
                try:
                    company_data = await self.scrape_website(website_url)
                    
                    if company_data and not self.should_skip_lead(company_data):
                        lead = self.create_scraped_lead(company_data, website_url)
                        
                        if await self.validate_lead_data(lead):
                            self.scraped_count += 1
                            yield lead
                            
                            logger.debug(f"Scraped website lead: {lead.company}")
                    
                    # Add delay between websites
                    await asyncio.sleep(2.0)
                    
                except Exception as e:
                    logger.error(f"Error scraping website {website_url}: {e}")
                    self.errors.append(f"Website scraping error for {website_url}: {str(e)}")
            
            logger.info(f"Company website scraping completed. Found {self.scraped_count} leads")
            
        except Exception as e:
            logger.error(f"Error in company website scraping: {e}")
            self.errors.append(f"Company website scraping error: {str(e)}")
    
    async def find_company_websites(self) -> List[str]:
        """Find company websites using search engines"""
        
        websites = []
        
        try:
            # Use DuckDuckGo search (more scraping-friendly than Google)
            search_query = f"{self.config.search_query} site:*.com OR site:*.com.br"
            if self.config.location:
                search_query += f" {self.config.location}"
            
            search_url = f"https://duckduckgo.com/html/?q={search_query}"
            
            response = await self.make_request(search_url)
            if not response:
                logger.warning("Failed to get search results from DuckDuckGo")
                return websites
            
            html_content = await response.text()
            soup = self.parse_html(html_content)
            
            # Extract website URLs from search results
            result_links = soup.select('a[href*="uddg="]')  # DuckDuckGo result links
            
            for link in result_links[:self.config.max_results]:
                href = link.get('href')
                if href:
                    # Extract actual URL from DuckDuckGo redirect
                    actual_url = self.extract_actual_url_from_redirect(href)
                    if actual_url and self.is_valid_company_website(actual_url):
                        websites.append(actual_url)
            
            # Remove duplicates
            websites = list(set(websites))
            
        except Exception as e:
            logger.error(f"Error finding company websites: {e}")
            self.errors.append(f"Website search error: {str(e)}")
        
        return websites
    
    def extract_actual_url_from_redirect(self, redirect_url: str) -> Optional[str]:
        """Extract actual URL from search engine redirect"""
        
        try:
            # DuckDuckGo redirect pattern
            if 'uddg=' in redirect_url:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url).query)
                if 'uddg' in parsed:
                    return urllib.parse.unquote(parsed['uddg'][0])
            
            return redirect_url
            
        except Exception:
            return None
    
    def is_valid_company_website(self, url: str) -> bool:
        """Check if URL looks like a valid company website"""
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Skip common non-company sites
            skip_domains = [
                'google.com', 'facebook.com', 'linkedin.com', 'twitter.com',
                'instagram.com', 'youtube.com', 'wikipedia.org', 'amazon.com',
                'mercadolivre.com.br', 'olx.com.br', 'reclameaqui.com.br'
            ]
            
            for skip_domain in skip_domains:
                if skip_domain in domain:
                    return False
            
            # Must have a reasonable domain
            if not domain or len(domain) < 4:
                return False
            
            # Should end with common TLDs
            valid_tlds = ['.com', '.com.br', '.org', '.net', '.br', '.co']
            if not any(domain.endswith(tld) for tld in valid_tlds):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def scrape_website(self, website_url: str) -> Optional[Dict[str, Any]]:
        """Scrape contact information from a company website"""
        
        try:
            logger.debug(f"Scraping website: {website_url}")
            
            # Get main page
            response = await self.make_request(website_url)
            if not response:
                return None
            
            html_content = await response.text()
            soup = self.parse_html(html_content)
            
            company_data = {}
            
            # Extract company name
            company_name = await self.extract_company_name(soup, website_url)
            if not company_name:
                return None
            
            company_data['company'] = company_name
            company_data['website'] = website_url
            
            # Extract contact information from main page
            await self.extract_contact_info(soup, company_data)
            
            # Try to find and scrape contact/about pages
            contact_pages = await self.find_contact_pages(soup, website_url)
            
            for contact_url in contact_pages[:3]:  # Limit to 3 additional pages
                try:
                    contact_response = await self.make_request(contact_url)
                    if contact_response:
                        contact_html = await contact_response.text()
                        contact_soup = self.parse_html(contact_html)
                        await self.extract_contact_info(contact_soup, company_data)
                        
                        # Add small delay between page requests
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.debug(f"Error scraping contact page {contact_url}: {e}")
            
            # Extract additional company information
            await self.extract_company_details(soup, company_data)
            
            # Set default industry if not found
            if not company_data.get('industry') and self.config.industry:
                company_data['industry'] = self.config.industry
            
            # Add metadata
            company_data['source_type'] = 'company_website'
            company_data['search_query'] = self.config.search_query
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error scraping website {website_url}: {e}")
            return None
    
    async def extract_company_name(self, soup, website_url: str) -> Optional[str]:
        """Extract company name from website"""
        
        # Try multiple methods to get company name
        
        # 1. Page title
        title_elem = soup.find('title')
        if title_elem:
            title = self.clean_text(title_elem.get_text())
            # Clean up common title patterns
            title = re.sub(r'\s*[-|]\s*(Home|Início|Welcome).*$', '', title, flags=re.IGNORECASE)
            if len(title) > 2 and len(title) < 100:
                return title
        
        # 2. Logo alt text
        logo_selectors = [
            'img[alt*="logo"]',
            'img[class*="logo"]',
            '.logo img',
            'header img'
        ]
        
        for selector in logo_selectors:
            logo_elem = soup.select_one(selector)
            if logo_elem:
                alt_text = logo_elem.get('alt', '')
                if alt_text and len(alt_text) > 2 and len(alt_text) < 50:
                    return self.clean_text(alt_text)
        
        # 3. Main heading
        heading_selectors = ['h1', '.company-name', '.brand-name', 'header h1']
        
        for selector in heading_selectors:
            heading_elem = soup.select_one(selector)
            if heading_elem:
                heading_text = self.clean_text(heading_elem.get_text())
                if len(heading_text) > 2 and len(heading_text) < 100:
                    return heading_text
        
        # 4. Domain name as fallback
        try:
            domain = urlparse(website_url).netloc
            domain = domain.replace('www.', '').replace('.com', '').replace('.com.br', '')
            return domain.title()
        except:
            pass
        
        return None
    
    async def extract_contact_info(self, soup, company_data: Dict[str, Any]):
        """Extract contact information from HTML"""
        
        page_text = soup.get_text()
        
        # Extract emails
        if not company_data.get('email'):
            email = self.extract_email(page_text)
            if email:
                company_data['email'] = email
        
        # Extract phone numbers
        if not company_data.get('phone'):
            phone = self.extract_phone(page_text)
            if phone:
                company_data['phone'] = phone
        
        # Extract address/location
        if not company_data.get('location'):
            location = self.extract_location(page_text)
            if location:
                company_data['location'] = location
        
        # Extract social media links
        social_links = soup.find_all('a', href=True)
        for link in social_links:
            href = link.get('href', '').lower()
            
            if 'linkedin.com' in href and not company_data.get('linkedin_url'):
                company_data['linkedin_url'] = link.get('href')
            elif 'facebook.com' in href and not company_data.get('facebook_url'):
                company_data['facebook_url'] = link.get('href')
            elif 'twitter.com' in href and not company_data.get('twitter_url'):
                company_data['twitter_url'] = link.get('href')
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location/address from text"""
        
        # Brazilian location patterns
        location_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})',  # City, State
            r'Rua\s+[^,]+,\s*[^,]+,\s*([^,]+)',  # Street address with city
            r'Av\.\s+[^,]+,\s*[^,]+,\s*([^,]+)',  # Avenue address with city
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    return f"{matches[0][0]}, {matches[0][1]}"
                else:
                    return matches[0]
        
        # Look for common Brazilian cities
        cities = [
            'São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Brasília',
            'Salvador', 'Fortaleza', 'Curitiba', 'Recife', 'Porto Alegre'
        ]
        
        for city in cities:
            if city in text:
                return city
        
        return None
    
    async def find_contact_pages(self, soup, base_url: str) -> List[str]:
        """Find contact and about pages on the website"""
        
        contact_pages = []
        
        # Look for contact/about page links
        contact_keywords = [
            'contato', 'contact', 'sobre', 'about', 'empresa',
            'quem somos', 'who we are', 'fale conosco'
        ]
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text().lower()
            
            # Check if link text or href contains contact keywords
            if any(keyword in text or keyword in href for keyword in contact_keywords):
                full_url = urljoin(base_url, link.get('href'))
                
                # Avoid duplicates and external links
                if full_url not in contact_pages and urlparse(full_url).netloc == urlparse(base_url).netloc:
                    contact_pages.append(full_url)
        
        return contact_pages
    
    async def extract_company_details(self, soup, company_data: Dict[str, Any]):
        """Extract additional company details"""
        
        page_text = soup.get_text()
        
        # Extract description from meta tags or about sections
        if not company_data.get('description'):
            # Try meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
                if len(description) > 20:
                    company_data['description'] = self.clean_text(description)
            
            # Try about sections
            about_selectors = [
                '.about', '#about', '.company-description',
                '.intro', '.overview', '.description'
            ]
            
            for selector in about_selectors:
                about_elem = soup.select_one(selector)
                if about_elem:
                    about_text = self.clean_text(about_elem.get_text())
                    if len(about_text) > 50 and len(about_text) < 500:
                        company_data['description'] = about_text
                        break
        
        # Try to extract industry from page content
        if not company_data.get('industry'):
            industry_keywords = {
                'tecnologia': ['software', 'tech', 'desenvolvimento', 'sistemas', 'ti'],
                'consultoria': ['consultoria', 'consulting', 'advisory'],
                'marketing': ['marketing', 'publicidade', 'advertising'],
                'saúde': ['saúde', 'health', 'medical', 'medicina'],
                'educação': ['educação', 'education', 'ensino', 'escola'],
                'financeiro': ['financeiro', 'finance', 'banco', 'investimento']
            }
            
            page_text_lower = page_text.lower()
            
            for industry, keywords in industry_keywords.items():
                if any(keyword in page_text_lower for keyword in keywords):
                    company_data['industry'] = industry.title()
                    break