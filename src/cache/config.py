"""
Cache configuration settings
"""
import os
from typing import Dict, Any

def get_redis_client():
    """Get Redis client instance"""
    from ..database.connection import get_redis
    return get_redis()

class CacheConfig:
    """Configuration class for cache settings"""
    
    # Default TTL values (in seconds)
    DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))  # 1 hour
    SEARCH_RESULTS_TTL = int(os.getenv("SEARCH_CACHE_TTL", "3600"))  # 1 hour
    LEAD_DATA_TTL = int(os.getenv("LEAD_CACHE_TTL", "7200"))  # 2 hours
    USER_PREFERENCES_TTL = int(os.getenv("USER_PREFS_TTL", "86400"))  # 24 hours
    ANALYTICS_TTL = int(os.getenv("ANALYTICS_TTL", "1800"))  # 30 minutes
    
    # Scraping cache TTL values
    SCRAPING_JOB_TTL = int(os.getenv("SCRAPING_JOB_TTL", "86400"))  # 24 hours
    SCRAPING_SUGGESTIONS_TTL = int(os.getenv("SCRAPING_SUGGESTIONS_TTL", "21600"))  # 6 hours
    SCRAPING_RATE_LIMIT_TTL = int(os.getenv("SCRAPING_RATE_LIMIT_TTL", "60"))  # 1 minute
    
    # Cache key prefixes
    SEARCH_PREFIX = "search:"
    LEAD_PREFIX = "lead:"
    USER_PREFS_PREFIX = "user_prefs:"
    ANALYTICS_PREFIX = "analytics:"
    SUGGESTIONS_PREFIX = "suggestions:"
    POPULAR_SEARCHES_KEY = "popular_searches"
    
    # Scraping cache prefixes
    SCRAPING_JOB_PREFIX = "scraping_job:"
    SCRAPING_USER_JOBS_PREFIX = "user_scraping_jobs:"
    SCRAPING_STATS_KEY = "scraping_stats"
    SCRAPING_SUGGESTIONS_PREFIX = "scraping_suggestions:"
    SCRAPING_RATE_LIMIT_PREFIX = "scraper_rate_limit:"
    INDEX_PREFIX = "index:"
    
    # Performance settings
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "1000"))
    INDEXING_BATCH_SIZE = int(os.getenv("INDEXING_BATCH_SIZE", "100"))
    
    @classmethod
    def get_ttl_for_key_type(cls, key_type: str) -> int:
        """Get TTL based on key type"""
        ttl_map = {
            "search": cls.SEARCH_RESULTS_TTL,
            "lead": cls.LEAD_DATA_TTL,
            "user_prefs": cls.USER_PREFERENCES_TTL,
            "analytics": cls.ANALYTICS_TTL,
            "scraping_job": cls.SCRAPING_JOB_TTL,
            "scraping_suggestions": cls.SCRAPING_SUGGESTIONS_TTL,
            "scraping_rate_limit": cls.SCRAPING_RATE_LIMIT_TTL,
        }
        return ttl_map.get(key_type, cls.DEFAULT_TTL)
    
    @classmethod
    def get_key_prefix(cls, key_type: str) -> str:
        """Get key prefix based on type"""
        prefix_map = {
            "search": cls.SEARCH_PREFIX,
            "lead": cls.LEAD_PREFIX,
            "user_prefs": cls.USER_PREFS_PREFIX,
            "analytics": cls.ANALYTICS_PREFIX,
            "suggestions": cls.SUGGESTIONS_PREFIX,
            "scraping_job": cls.SCRAPING_JOB_PREFIX,
            "scraping_suggestions": cls.SCRAPING_SUGGESTIONS_PREFIX,
            "scraping_rate_limit": cls.SCRAPING_RATE_LIMIT_PREFIX,
            "index": cls.INDEX_PREFIX,
        }
        return prefix_map.get(key_type, "")