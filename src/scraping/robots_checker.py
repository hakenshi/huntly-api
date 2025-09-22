"""
Robots.txt checker for ethical web scraping compliance
"""

import asyncio
import logging
from typing import Optional, Dict, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RobotsChecker:
    """Check robots.txt compliance for web scraping"""
    
    def __init__(self, user_agent: str = "*"):
        self.user_agent = user_agent
        self.cache: Dict[str, Dict] = {}  # Cache robots.txt data
        self.cache_ttl = timedelta(hours=24)  # Cache for 24 hours
    
    async def can_fetch(self, url: str, user_agent: str = None) -> bool:
        """
        Check if we can fetch the given URL according to robots.txt
        
        Args:
            url: The URL to check
            user_agent: User agent to check for (defaults to instance user_agent)
            
        Returns:
            True if allowed to fetch, False otherwise
        """
        try:
            user_agent = user_agent or self.user_agent
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Get robots.txt content
            robots_content = await self._get_robots_txt(base_url)
            
            if not robots_content:
                # If no robots.txt found, assume allowed
                logger.debug(f"No robots.txt found for {base_url}, allowing access")
                return True
            
            # Parse robots.txt
            rp = RobotFileParser()
            rp.set_url(urljoin(base_url, "/robots.txt"))
            rp.read()
            
            # Check if we can fetch the URL
            can_fetch = rp.can_fetch(user_agent, url)
            
            logger.debug(f"Robots.txt check for {url}: {'allowed' if can_fetch else 'disallowed'}")
            return can_fetch
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, be conservative and allow (but log the issue)
            return True
    
    async def get_crawl_delay(self, url: str, user_agent: str = None) -> Optional[float]:
        """
        Get the crawl delay specified in robots.txt
        
        Args:
            url: The URL to check
            user_agent: User agent to check for
            
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        try:
            user_agent = user_agent or self.user_agent
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            robots_content = await self._get_robots_txt(base_url)
            
            if not robots_content:
                return None
            
            # Parse robots.txt and get crawl delay
            rp = RobotFileParser()
            rp.set_url(urljoin(base_url, "/robots.txt"))
            rp.read()
            
            delay = rp.crawl_delay(user_agent)
            
            if delay:
                logger.debug(f"Crawl delay for {base_url}: {delay} seconds")
                return float(delay)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting crawl delay for {url}: {e}")
            return None
    
    async def get_request_rate(self, url: str, user_agent: str = None) -> Optional[float]:
        """
        Get the request rate specified in robots.txt
        
        Args:
            url: The URL to check
            user_agent: User agent to check for
            
        Returns:
            Request rate (requests per second), or None if not specified
        """
        try:
            user_agent = user_agent or self.user_agent
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            robots_content = await self._get_robots_txt(base_url)
            
            if not robots_content:
                return None
            
            # Parse robots.txt and get request rate
            rp = RobotFileParser()
            rp.set_url(urljoin(base_url, "/robots.txt"))
            rp.read()
            
            rate = rp.request_rate(user_agent)
            
            if rate:
                logger.debug(f"Request rate for {base_url}: {rate}")
                return float(rate.requests) / float(rate.seconds)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting request rate for {url}: {e}")
            return None
    
    async def _get_robots_txt(self, base_url: str) -> Optional[str]:
        """
        Fetch and cache robots.txt content
        
        Args:
            base_url: Base URL of the site
            
        Returns:
            robots.txt content or None if not found
        """
        # Check cache first
        if base_url in self.cache:
            cache_entry = self.cache[base_url]
            if datetime.now() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['content']
        
        try:
            robots_url = urljoin(base_url, "/robots.txt")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Cache the content
                        self.cache[base_url] = {
                            'content': content,
                            'timestamp': datetime.now()
                        }
                        
                        logger.debug(f"Fetched robots.txt from {robots_url}")
                        return content
                    else:
                        logger.debug(f"robots.txt not found at {robots_url} (status: {response.status})")
                        
                        # Cache the fact that there's no robots.txt
                        self.cache[base_url] = {
                            'content': None,
                            'timestamp': datetime.now()
                        }
                        
                        return None
                        
        except Exception as e:
            logger.debug(f"Error fetching robots.txt from {base_url}: {e}")
            return None
    
    def get_sitemap_urls(self, base_url: str) -> Set[str]:
        """
        Get sitemap URLs from cached robots.txt
        
        Args:
            base_url: Base URL of the site
            
        Returns:
            Set of sitemap URLs
        """
        sitemaps = set()
        
        try:
            if base_url in self.cache:
                content = self.cache[base_url]['content']
                if content:
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.lower().startswith('sitemap:'):
                            sitemap_url = line.split(':', 1)[1].strip()
                            sitemaps.add(sitemap_url)
            
        except Exception as e:
            logger.error(f"Error extracting sitemaps from robots.txt: {e}")
        
        return sitemaps
    
    def clear_cache(self):
        """Clear the robots.txt cache"""
        self.cache.clear()
        logger.info("Robots.txt cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached_domains': len(self.cache),
            'cache_hits': sum(1 for entry in self.cache.values() if entry['content'] is not None),
            'cache_misses': sum(1 for entry in self.cache.values() if entry['content'] is None)
        }

# Global instance for easy access
robots_checker = RobotsChecker()

async def check_robots_compliance(url: str, user_agent: str = None) -> Dict[str, any]:
    """
    Convenience function to check robots.txt compliance
    
    Args:
        url: URL to check
        user_agent: User agent string
        
    Returns:
        Dictionary with compliance information
    """
    checker = robots_checker
    
    can_fetch = await checker.can_fetch(url, user_agent)
    crawl_delay = await checker.get_crawl_delay(url, user_agent)
    request_rate = await checker.get_request_rate(url, user_agent)
    
    return {
        'can_fetch': can_fetch,
        'crawl_delay': crawl_delay,
        'request_rate': request_rate,
        'recommended_delay': max(crawl_delay or 1.0, 1.0)  # At least 1 second
    }