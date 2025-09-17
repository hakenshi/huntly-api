"""
Cache module for Huntly MVP
Provides Redis-based caching with TTL and invalidation logic
"""

from .manager import CacheManager
from .decorators import cache_result, cache_search_results, cache_lead_data
from .config import CacheConfig

__all__ = [
    'CacheManager',
    'cache_result',
    'cache_search_results', 
    'cache_lead_data',
    'CacheConfig'
]