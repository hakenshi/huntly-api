"""
Example usage of the lead scraping system
"""

import asyncio
import logging
from sqlalchemy.orm import Session
from ..database.connection import SessionLocal
from ..cache.manager import CacheManager
from ..cache.config import get_redis_client
from .manager import ScrapingManager
from .models import ScrapingConfig, ScrapingSource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_google_maps_scraping():
    """Example: Scrape leads from Google Maps"""
    print("\n=== Google Maps Scraping Example ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    
    # Create scraping manager
    scraping_manager = ScrapingManager(db, cache_manager)
    
    try:
        # Configure scraping
        config = ScrapingConfig(
            search_query="restaurante pizza",
            location="São Paulo, SP",
            max_results=10,
            sources=[ScrapingSource.GOOGLE_MAPS],
            delay_between_requests=1.0,
            required_fields=["company", "phone"]
        )
        
        print(f"Starting scraping job for: {config.search_query}")
        
        # Start scraping job
        job = await scraping_manager.start_scraping_job(
            user_id=1,  # Assuming user exists
            config=config
        )
        
        print(f"Job started with ID: {job.id}")
        
        # Monitor job progress
        while True:
            await asyncio.sleep(2)
            
            updated_job = scraping_manager.get_job_status(job.id)
            if not updated_job:
                break
            
            print(f"Status: {updated_job.status}, Leads found: {updated_job.leads_found}, Saved: {updated_job.leads_saved}")
            
            if updated_job.status.value in ['completed', 'failed', 'cancelled']:
                break
        
        # Show final results
        final_job = scraping_manager.get_job_status(job.id)
        if final_job:
            print(f"\n📊 Final Results:")
            print(f"   Status: {final_job.status}")
            print(f"   Leads found: {final_job.leads_found}")
            print(f"   Leads saved: {final_job.leads_saved}")
            print(f"   Execution time: {(final_job.completed_at - final_job.started_at).total_seconds():.2f}s")
            
            if final_job.errors:
                print(f"   Errors: {len(final_job.errors)}")
                for error in final_job.errors[:3]:
                    print(f"     - {error}")
        
    except Exception as e:
        logger.error(f"Error in Google Maps scraping example: {e}")
    finally:
        db.close()

async def example_multi_source_scraping():
    """Example: Scrape leads from multiple sources"""
    print("\n=== Multi-Source Scraping Example ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    
    # Create scraping manager
    scraping_manager = ScrapingManager(db, cache_manager)
    
    try:
        # Configure scraping with multiple sources
        config = ScrapingConfig(
            search_query="empresa software desenvolvimento",
            location="São Paulo",
            industry="Tecnologia",
            max_results=20,
            sources=[
                ScrapingSource.GOOGLE_MAPS,
                ScrapingSource.COMPANY_WEBSITE
            ],
            delay_between_requests=1.5,
            required_fields=["company"],
            min_employees=10,
            max_employees=200
        )
        
        print(f"Starting multi-source scraping for: {config.search_query}")
        print(f"Sources: {[source.value for source in config.sources]}")
        
        # Start scraping job
        job = await scraping_manager.start_scraping_job(
            user_id=1,
            config=config
        )
        
        print(f"Job started with ID: {job.id}")
        
        # Monitor job progress
        while True:
            await asyncio.sleep(3)
            
            updated_job = scraping_manager.get_job_status(job.id)
            if not updated_job:
                break
            
            print(f"Status: {updated_job.status}, Leads found: {updated_job.leads_found}, Saved: {updated_job.leads_saved}")
            
            # Show progress by source
            if updated_job.results_summary:
                for source, stats in updated_job.results_summary.items():
                    if isinstance(stats, dict) and 'scraped_count' in stats:
                        print(f"   {source}: {stats['scraped_count']} scraped")
            
            if updated_job.status.value in ['completed', 'failed', 'cancelled']:
                break
        
        # Show final results
        final_job = scraping_manager.get_job_status(job.id)
        if final_job:
            print(f"\n📊 Final Results:")
            print(f"   Status: {final_job.status}")
            print(f"   Total leads found: {final_job.leads_found}")
            print(f"   Total leads saved: {final_job.leads_saved}")
            
            if final_job.results_summary:
                print(f"   Results by source:")
                for source, stats in final_job.results_summary.items():
                    if isinstance(stats, dict):
                        print(f"     {source}: {stats}")
        
    except Exception as e:
        logger.error(f"Error in multi-source scraping example: {e}")
    finally:
        db.close()

async def example_scraping_suggestions():
    """Example: Get scraping suggestions"""
    print("\n=== Scraping Suggestions Example ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    
    # Create scraping manager
    scraping_manager = ScrapingManager(db, cache_manager)
    
    try:
        # Test different queries
        test_queries = [
            "restaurante italiano",
            "empresa software",
            "consultoria marketing",
            "clínica médica",
            "loja roupas"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            
            suggestions = await scraping_manager.get_scraping_suggestions(query)
            
            print(f"   Recommended sources: {suggestions['recommended_sources']}")
            print(f"   Estimated results: {suggestions['estimated_results']}")
            
            if suggestions['suggested_filters']:
                print(f"   Suggested filters: {suggestions['suggested_filters']}")
            
            if suggestions['similar_queries']:
                print(f"   Similar queries: {suggestions['similar_queries']}")
        
    except Exception as e:
        logger.error(f"Error in suggestions example: {e}")
    finally:
        db.close()

async def example_scraping_stats():
    """Example: Get scraping statistics"""
    print("\n=== Scraping Statistics Example ===")
    
    # Get database session and cache manager
    db: Session = SessionLocal()
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    
    # Create scraping manager
    scraping_manager = ScrapingManager(db, cache_manager)
    
    try:
        stats = scraping_manager.get_scraping_stats()
        
        print(f"📊 Scraping Statistics:")
        print(f"   Active jobs: {stats['active_jobs']}")
        print(f"   Total leads found: {stats['total_leads_found']}")
        print(f"   Total leads saved: {stats['total_leads_saved']}")
        print(f"   Average success rate: {stats['average_success_rate']:.1f}%")
        
        if stats['jobs_by_status']:
            print(f"   Jobs by status:")
            for status, count in stats['jobs_by_status'].items():
                print(f"     {status}: {count}")
        
        if stats['sources_usage']:
            print(f"   Source usage:")
            for source, count in stats['sources_usage'].items():
                print(f"     {source}: {count}")
        
    except Exception as e:
        logger.error(f"Error in stats example: {e}")
    finally:
        db.close()

def example_scraping_config():
    """Example: Different scraping configurations"""
    print("\n=== Scraping Configuration Examples ===")
    
    # Basic configuration
    basic_config = ScrapingConfig(
        search_query="pizzaria",
        location="Rio de Janeiro",
        max_results=50
    )
    print(f"Basic config: {basic_config.dict()}")
    
    # Advanced configuration
    advanced_config = ScrapingConfig(
        search_query="startup tecnologia",
        location="São Paulo",
        industry="Tecnologia",
        max_results=100,
        max_pages=5,
        delay_between_requests=2.0,
        sources=[ScrapingSource.GOOGLE_MAPS, ScrapingSource.LINKEDIN],
        required_fields=["company", "email"],
        min_employees=5,
        max_employees=100,
        use_proxy=False,
        respect_robots_txt=True
    )
    print(f"\nAdvanced config: {advanced_config.dict()}")
    
    # Industry-specific configurations
    configs = {
        "Restaurantes": ScrapingConfig(
            search_query="restaurante comida",
            sources=[ScrapingSource.GOOGLE_MAPS],
            required_fields=["company", "phone"],
            max_results=200
        ),
        "Tech Startups": ScrapingConfig(
            search_query="startup software saas",
            industry="Tecnologia",
            sources=[ScrapingSource.LINKEDIN, ScrapingSource.COMPANY_WEBSITE],
            required_fields=["company", "website"],
            min_employees=5,
            max_employees=50,
            max_results=100
        ),
        "Serviços Profissionais": ScrapingConfig(
            search_query="advogado contador consultor",
            industry="Serviços",
            sources=[ScrapingSource.GOOGLE_MAPS, ScrapingSource.LINKEDIN],
            required_fields=["company", "phone"],
            max_results=150
        )
    }
    
    print(f"\n📋 Industry-specific configurations:")
    for industry, config in configs.items():
        print(f"   {industry}:")
        print(f"     Query: {config.search_query}")
        print(f"     Sources: {[s.value for s in config.sources]}")
        print(f"     Required fields: {config.required_fields}")
        print(f"     Max results: {config.max_results}")

async def main():
    """Run all examples"""
    print("🕷️ Lead Scraping System Examples")
    print("=" * 50)
    
    try:
        # Configuration examples (synchronous)
        example_scraping_config()
        
        # Async examples
        await example_scraping_suggestions()
        await example_scraping_stats()
        
        # Uncomment to run actual scraping (takes time)
        # await example_google_maps_scraping()
        # await example_multi_source_scraping()
        
        print("\n✅ All examples completed!")
        print("\n💡 To run actual scraping:")
        print("   - Uncomment the scraping examples in main()")
        print("   - Make sure you have a user in the database")
        print("   - Be respectful of websites' robots.txt and rate limits")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\n❌ Examples failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())