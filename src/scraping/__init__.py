"""
Lead Scraping Module
Automated lead collection from various internet sources
"""

from .scrapers.base import BaseScraper
from .scrapers.google_maps import GoogleMapsScraper
from .scrapers.linkedin import LinkedInScraper
from .scrapers.company_websites import CompanyWebsiteScraper
from .manager import ScrapingManager
from .models import ScrapedLead, ScrapingJob, ScrapingConfig

__all__ = [
    "BaseScraper",
    "GoogleMapsScraper", 
    "LinkedInScraper",
    "CompanyWebsiteScraper",
    "ScrapingManager",
    "ScrapedLead",
    "ScrapingJob",
    "ScrapingConfig"
]