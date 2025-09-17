"""
Example usage of the Redis Cache Manager
This file demonstrates how to use the cache manager and decorators
"""
from . import CacheManager, cache_search_results, cache_lead_data, invalidate_search_cache
from ..database.connection import get_redis
from typing import List, Dict, Any

# Initialize cache manager
def get_cache_manager_instance():
    """Get a cache manager instance"""
    redis_client = get_redis()
    return CacheManager(redis_client)

# Example 1: Basic cache operations
def basic_cache_example():
    """Demonstrate basic cache operations"""
    cache = get_cache_manager_instance()
    
    # Set some data
    user_data = {"name": "John Doe", "email": "john@example.com", "preferences": {"theme": "dark"}}
    cache.set("user_prefs", "john@example.com", user_data, ttl=3600)
    
    # Get data
    cached_data = cache.get("user_prefs", "john@example.com")
    print(f"Cached user data: {cached_data}")
    
    # Check if exists
    exists = cache.exists("user_prefs", "john@example.com")
    print(f"Cache exists: {exists}")
    
    # Get TTL
    ttl = cache.get_ttl("user_prefs", "john@example.com")
    print(f"TTL remaining: {ttl} seconds")

# Example 2: Search results caching
@cache_search_results(ttl=1800)  # Cache for 30 minutes
def search_leads(text: str = None, industry: str = None, location: str = None) -> List[Dict]:
    """Example search function with caching"""
    print(f"Executing search: text='{text}', industry='{industry}', location='{location}'")
    
    # Simulate database query
    mock_results = [
        {"id": 1, "company": "TechCorp", "industry": "Technology", "location": "San Francisco"},
        {"id": 2, "company": "FinanceInc", "industry": "Finance", "location": "New York"},
        {"id": 3, "company": "HealthPlus", "industry": "Healthcare", "location": "Boston"}
    ]
    
    # Filter results based on parameters
    results = []
    for lead in mock_results:
        if industry and lead["industry"].lower() != industry.lower():
            continue
        if location and lead["location"].lower() != location.lower():
            continue
        if text and text.lower() not in lead["company"].lower():
            continue
        results.append(lead)
    
    return results

# Example 3: Lead data caching
@cache_lead_data(ttl=7200)  # Cache for 2 hours
def get_lead_details(lead_id: int) -> Dict:
    """Example function to get lead details with caching"""
    print(f"Fetching lead details for ID: {lead_id}")
    
    # Simulate database query
    mock_lead = {
        "id": lead_id,
        "company": f"Company {lead_id}",
        "contact_name": f"Contact {lead_id}",
        "email": f"contact{lead_id}@company.com",
        "phone": f"+1-555-{lead_id:04d}",
        "industry": "Technology",
        "location": "San Francisco",
        "description": f"This is a detailed description for lead {lead_id}",
        "last_updated": "2023-12-01T10:00:00Z"
    }
    
    return mock_lead

# Example 4: Cache invalidation
@invalidate_search_cache
def update_lead(lead_id: int, updates: Dict) -> Dict:
    """Example function that invalidates search cache when lead is updated"""
    print(f"Updating lead {lead_id} with: {updates}")
    
    # Simulate database update
    updated_lead = {
        "id": lead_id,
        "updated": True,
        "changes": updates
    }
    
    return updated_lead

# Example 5: Manual cache management
def manual_cache_example():
    """Demonstrate manual cache management"""
    cache = get_cache_manager_instance()
    
    # Cache search results manually
    query_data = {"text": "tech", "industry": "Technology"}
    results = [{"id": 1, "company": "TechCorp"}]
    cache.cache_search_results(query_data, results)
    
    # Retrieve cached search results
    cached_results = cache.get_cached_search_results(query_data)
    print(f"Cached search results: {cached_results}")
    
    # Cache lead data manually
    lead_data = {"id": 123, "company": "Example Corp"}
    cache.cache_lead_data(123, lead_data)
    
    # Retrieve cached lead data
    cached_lead = cache.get_cached_lead_data(123)
    print(f"Cached lead: {cached_lead}")
    
    # Popular searches
    cache.add_popular_search("technology companies")
    cache.add_popular_search("healthcare startups")
    cache.add_popular_search("technology companies")  # Increment count
    
    popular = cache.get_popular_searches(5)
    print(f"Popular searches: {popular}")

# Example 6: Health monitoring
def cache_health_example():
    """Demonstrate cache health monitoring"""
    cache = get_cache_manager_instance()
    
    health = cache.health_check()
    print(f"Cache health: {health}")
    
    if health["status"] == "healthy":
        print("✅ Cache is working properly")
    elif health["status"] == "disabled":
        print("⚠️ Cache is disabled")
    else:
        print("❌ Cache has issues")

# Example 7: Cache analytics
def cache_analytics_example():
    """Demonstrate caching analytics data"""
    cache = get_cache_manager_instance()
    
    # Cache some analytics metrics
    metrics = {
        "total_searches": 1250,
        "avg_response_time": 0.45,
        "cache_hit_rate": 0.78,
        "popular_industries": ["Technology", "Healthcare", "Finance"]
    }
    
    cache.cache_analytics_data("daily_metrics", metrics, ttl=1800)
    
    # Retrieve analytics
    cached_metrics = cache.get_cached_analytics_data("daily_metrics")
    print(f"Analytics metrics: {cached_metrics}")

if __name__ == "__main__":
    print("=== Redis Cache Manager Examples ===\n")
    
    print("1. Basic Cache Operations:")
    basic_cache_example()
    print()
    
    print("2. Search Results Caching:")
    # First call - will execute and cache
    results1 = search_leads(text="tech", industry="Technology")
    print(f"First search results: {len(results1)} items")
    
    # Second call - will use cache
    results2 = search_leads(text="tech", industry="Technology")
    print(f"Second search results: {len(results2)} items (from cache)")
    print()
    
    print("3. Lead Data Caching:")
    # First call - will execute and cache
    lead1 = get_lead_details(123)
    print(f"First lead fetch: {lead1['company']}")
    
    # Second call - will use cache
    lead2 = get_lead_details(123)
    print(f"Second lead fetch: {lead2['company']} (from cache)")
    print()
    
    print("4. Cache Invalidation:")
    update_result = update_lead(123, {"company": "Updated Company"})
    print(f"Update result: {update_result}")
    print()
    
    print("5. Manual Cache Management:")
    manual_cache_example()
    print()
    
    print("6. Cache Health Check:")
    cache_health_example()
    print()
    
    print("7. Analytics Caching:")
    cache_analytics_example()
    print()
    
    print("=== Examples Complete ===")