"""
Example usage of the Lead Indexing System
Demonstrates how to use the LeadIndexer for indexing and searching leads
"""

import logging
from sqlalchemy.orm import Session
from ..database.connection import SessionLocal, get_redis
from ..database.models import Lead as LeadModel
from ..cache.manager import CacheManager
from .indexer import LeadIndexer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_index_single_lead():
    """Example: Index a single lead"""
    print("\n=== Indexing Single Lead ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis()
    cache_manager = CacheManager(redis_client)
    
    # Create indexer
    indexer = LeadIndexer(db, cache_manager)
    
    try:
        # Get a lead from database (or create one for testing)
        lead = db.query(LeadModel).first()
        
        if not lead:
            print("No leads found in database. Creating a sample lead...")
            # Create sample lead
            lead = LeadModel(
                user_id=1,  # Assuming user exists
                company="TechInova Solutions",
                contact="Carlos Silva",
                email="carlos@techinova.com.br",
                phone="(11) 99999-9999",
                industry="Tecnologia",
                location="São Paulo, SP",
                description="Empresa de tecnologia especializada em soluções SaaS para e-commerce",
                keywords=["saas", "ecommerce", "tecnologia", "python", "react"]
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
        
        # Index the lead
        print(f"Indexing lead: {lead.company}")
        success = indexer.index_lead(lead)
        
        if success:
            print("✅ Lead indexed successfully!")
            
            # Show extracted metadata
            metadata = indexer.extract_searchable_metadata(lead)
            print(f"Searchable text: {metadata['searchable_text'][:100]}...")
            print(f"Keywords: {metadata['keywords']}")
            print(f"Company tokens: {metadata['company_tokens']}")
            print(f"Industry tokens: {metadata['industry_tokens']}")
        else:
            print("❌ Failed to index lead")
            
    except Exception as e:
        logger.error(f"Error in example: {e}")
    finally:
        db.close()

def example_bulk_index_leads():
    """Example: Bulk index multiple leads"""
    print("\n=== Bulk Indexing Leads ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis()
    cache_manager = CacheManager(redis_client)
    
    # Create indexer
    indexer = LeadIndexer(db, cache_manager)
    
    try:
        # Check current indexing status
        status = indexer.get_indexing_status()
        print(f"Current status:")
        print(f"  Total leads: {status['total_leads']}")
        print(f"  Indexed leads: {status['indexed_leads']}")
        print(f"  Coverage: {status['indexing_coverage']:.1f}%")
        
        if status['unindexed_leads'] > 0:
            print(f"\nIndexing {status['unindexed_leads']} unindexed leads...")
            
            # Perform bulk indexing
            stats = indexer.bulk_index_leads(batch_size=50)
            
            print(f"\n📊 Indexing Results:")
            print(f"  Total processed: {stats.total_leads}")
            print(f"  Successfully indexed: {stats.indexed_leads}")
            print(f"  Failed: {stats.failed_leads}")
            print(f"  Processing time: {stats.processing_time:.2f}s")
            
            if stats.errors:
                print(f"  Errors: {len(stats.errors)}")
                for error in stats.errors[:3]:  # Show first 3 errors
                    print(f"    - {error}")
        else:
            print("All leads are already indexed!")
            
    except Exception as e:
        logger.error(f"Error in bulk indexing example: {e}")
    finally:
        db.close()

def example_search_leads():
    """Example: Search leads using the indexing system"""
    print("\n=== Searching Leads ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis()
    cache_manager = CacheManager(redis_client)
    
    # Create indexer
    indexer = LeadIndexer(db, cache_manager)
    
    try:
        # Example searches
        search_terms = [
            ["tecnologia", "saas"],
            ["ecommerce"],
            ["python", "react"],
            ["são paulo"]
        ]
        
        for terms in search_terms:
            print(f"\n🔍 Searching for: {', '.join(terms)}")
            
            # Search using Redis inverted index
            lead_ids = indexer.search_leads_by_tokens(terms, limit=10)
            
            if lead_ids:
                print(f"Found {len(lead_ids)} leads: {lead_ids}")
                
                # Get actual lead data from database
                leads = db.query(LeadModel).filter(LeadModel.id.in_(lead_ids)).all()
                
                for lead in leads[:3]:  # Show first 3 results
                    print(f"  - {lead.company} ({lead.industry}) - {lead.location}")
            else:
                print("No leads found")
                
    except Exception as e:
        logger.error(f"Error in search example: {e}")
    finally:
        db.close()

def example_reindex_all():
    """Example: Reindex all leads (useful after schema changes)"""
    print("\n=== Reindexing All Leads ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis()
    cache_manager = CacheManager(redis_client)
    
    # Create indexer
    indexer = LeadIndexer(db, cache_manager)
    
    try:
        print("Starting full reindex of all leads...")
        print("⚠️  This will clear existing Redis indexes and rebuild them")
        
        # Perform full reindex
        stats = indexer.reindex_all_leads()
        
        print(f"\n📊 Reindexing Results:")
        print(f"  Total processed: {stats.total_leads}")
        print(f"  Successfully indexed: {stats.indexed_leads}")
        print(f"  Failed: {stats.failed_leads}")
        print(f"  Processing time: {stats.processing_time:.2f}s")
        
        if stats.errors:
            print(f"  Errors encountered: {len(stats.errors)}")
            
    except Exception as e:
        logger.error(f"Error in reindex example: {e}")
    finally:
        db.close()

def example_cache_operations():
    """Example: Direct cache operations"""
    print("\n=== Cache Operations ===")
    
    redis_client = get_redis()
    if not redis_client:
        print("❌ Redis not available - cache operations disabled")
        return
    
    cache_manager = CacheManager(redis_client)
    
    try:
        # Test cache health
        health = cache_manager.health_check()
        print(f"Cache status: {health['status']}")
        print(f"Redis available: {health['redis_available']}")
        
        if health['redis_available']:
            print(f"Connected clients: {health.get('connected_clients', 'unknown')}")
            print(f"Memory usage: {health.get('used_memory_human', 'unknown')}")
        
        # Example: Add terms to inverted index
        print("\n📝 Adding terms to inverted index...")
        cache_manager.add_to_inverted_index("tecnologia", 1)
        cache_manager.add_to_inverted_index("tecnologia", 2)
        cache_manager.add_to_inverted_index("saas", 1)
        cache_manager.add_to_inverted_index("saas", 3)
        
        # Search using inverted index
        print("\n🔍 Searching inverted index...")
        tech_leads = cache_manager.get_index_intersection(["tecnologia"])
        saas_leads = cache_manager.get_index_intersection(["saas"])
        both_leads = cache_manager.get_index_intersection(["tecnologia", "saas"])
        
        print(f"Leads with 'tecnologia': {tech_leads}")
        print(f"Leads with 'saas': {saas_leads}")
        print(f"Leads with both: {both_leads}")
        
    except Exception as e:
        logger.error(f"Error in cache operations example: {e}")

def main():
    """Run all examples"""
    print("🚀 Lead Indexing and Search System Examples")
    print("=" * 60)
    
    try:
        # Run indexing examples
        example_index_single_lead()
        example_bulk_index_leads()
        example_search_leads()
        example_cache_operations()
        
        # Run search engine examples
        example_search_engine()
        example_query_processing()
        example_ranking_algorithm()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\n❌ Examples failed: {e}")

if __name__ == "__main__":
    main()
d
def example_search_engine():
    """Example: Using the SearchEngine for advanced search"""
    print("\n=== Search Engine Examples ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis()
    cache_manager = CacheManager(redis_client)
    
    # Import SearchEngine and related models
    from .engine import SearchEngine
    from ..models.search import SearchQuery, SearchFilters, UserPreferences
    
    # Create search engine
    search_engine = SearchEngine(db, cache_manager)
    
    try:
        print("\n🔍 Example 1: Simple text search")
        query = SearchQuery(
            text="technology startup",
            limit=5
        )
        
        results = search_engine.search_leads(query)
        print(f"Found {len(results)} results for '{query.text}'")
        
        for result in results:
            print(f"  - {result.lead.company} (Score: {result.relevance_score:.3f})")
            if result.match_reasons:
                print(f"    Reasons: {', '.join(result.match_reasons[:2])}")
        
        print("\n🔍 Example 2: Search with filters")
        filters = SearchFilters(
            industry="Tecnologia",
            location="São Paulo"
        )
        
        query_with_filters = SearchQuery(
            text="software development",
            filters=filters,
            limit=3
        )
        
        results = search_engine.search_leads(query_with_filters)
        print(f"Filtered search found {len(results)} results")
        
        for result in results:
            print(f"  - {result.lead.company} in {result.lead.location}")
            print(f"    Industry: {result.lead.industry}, Score: {result.relevance_score:.3f}")
        
        print("\n🔍 Example 3: Search with user preferences")
        user_prefs = UserPreferences(
            preferred_industries=["Tecnologia", "E-commerce"],
            preferred_locations=["São Paulo", "Rio de Janeiro"],
            scoring_weights={
                "text_relevance": 0.3,
                "industry_match": 0.4,
                "location_proximity": 0.2,
                "company_size": 0.05,
                "data_quality": 0.05
            }
        )
        
        personalized_query = SearchQuery(
            text="ecommerce platform",
            limit=3
        )
        
        results = search_engine.search_leads(personalized_query, user_prefs)
        print(f"Personalized search found {len(results)} results")
        
        for result in results:
            print(f"  - {result.lead.company} (Score: {result.relevance_score:.3f})")
            print(f"    Match reasons: {', '.join(result.match_reasons[:2])}")
        
        print("\n💡 Example 4: Get search suggestions")
        suggestions = search_engine.get_search_suggestions("tech", limit=5)
        print(f"Suggestions for 'tech': {suggestions}")
        
        suggestions = search_engine.get_search_suggestions("e-com", limit=5)
        print(f"Suggestions for 'e-com': {suggestions}")
        
        print("\n📊 Example 5: Search engine statistics")
        stats = search_engine.get_search_stats()
        print(f"Search engine stats:")
        print(f"  Indexing coverage: {stats['indexing_status'].get('indexing_coverage', 0):.1f}%")
        print(f"  Popular searches: {stats.get('popular_searches', [])[:3]}")
        print(f"  Cache status: {stats['cache_health'].get('status', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Error in search engine example: {e}")
        print(f"❌ Search engine example failed: {e}")
    finally:
        db.close()

def example_query_processing():
    """Example: Query processing and parsing"""
    print("\n=== Query Processing Examples ===")
    
    from .engine import QueryProcessor
    
    processor = QueryProcessor()
    
    # Test queries
    test_queries = [
        "technology startup in São Paulo",
        "\"software development\" company",
        "ecommerce platform with python",
        "large tech company in Rio de Janeiro",
        "small healthcare startup"
    ]
    
    for query_text in test_queries:
        print(f"\n📝 Query: '{query_text}'")
        parsed = processor.parse_query(query_text)
        
        print(f"  Terms: {parsed['terms']}")
        print(f"  Phrases: {parsed['phrases']}")
        print(f"  Implicit filters: {parsed['filters']}")

def example_ranking_algorithm():
    """Example: Ranking algorithm demonstration"""
    print("\n=== Ranking Algorithm Examples ===")
    
    # Get database session
    db: Session = SessionLocal()
    
    try:
        from .engine import RankingAlgorithm
        from ..models.search import UserPreferences, SearchFilters
        
        # Create user preferences
        user_prefs = UserPreferences(
            preferred_industries=["Tecnologia"],
            preferred_locations=["São Paulo"],
            scoring_weights={
                "text_relevance": 0.5,
                "industry_match": 0.3,
                "location_proximity": 0.2
            }
        )
        
        # Create ranking algorithm
        ranker = RankingAlgorithm(user_prefs)
        
        # Get some leads to rank
        leads = db.query(LeadModel).limit(3).all()
        
        if leads:
            # Example query and filters
            parsed_query = {
                "terms": ["tecnologia", "software"],
                "phrases": [],
                "filters": {}
            }
            
            filters = SearchFilters(industry="Tecnologia")
            
            print("🏆 Ranking results:")
            for lead in leads:
                score, reasons = ranker.calculate_relevance_score(lead, parsed_query, filters)
                print(f"\n  Lead: {lead.company}")
                print(f"  Score: {score:.3f}")
                print(f"  Reasons: {', '.join(reasons[:3])}")
        else:
            print("No leads available for ranking example")
            
    except Exception as e:
        logger.error(f"Error in ranking example: {e}")
        print(f"❌ Ranking example failed: {e}")
    finally:
        db.close()