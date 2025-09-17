"""
Script para testar o sistema de scraping
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import SessionLocal
from src.cache.manager import CacheManager
from src.cache.config import get_redis_client
from src.scraping.manager import ScrapingManager
from src.scraping.models import ScrapingConfig, ScrapingSource

async def test_scraping_system():
    """Test the scraping system with a simple configuration"""
    print("🕷️ Testing Huntly Scraping System")
    print("=" * 50)
    
    # Get database session and cache manager
    db = SessionLocal()
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    
    try:
        # Create scraping manager
        scraping_manager = ScrapingManager(db, cache_manager)
        print("✅ Scraping manager initialized")
        
        # Test configuration
        config = ScrapingConfig(
            search_query="pizzaria",
            location="São Paulo, SP",
            max_results=5,  # Small test
            sources=[ScrapingSource.GOOGLE_MAPS],
            delay_between_requests=2.0,  # Be respectful
            required_fields=["company"]
        )
        
        print(f"🔍 Testing scraping with query: '{config.search_query}'")
        print(f"📍 Location: {config.location}")
        print(f"🎯 Max results: {config.max_results}")
        
        # Start scraping job
        job = await scraping_manager.start_scraping_job(
            user_id=1,  # Test user
            config=config
        )
        
        print(f"🚀 Job started with ID: {job.id}")
        
        # Monitor progress
        print("\n📊 Monitoring progress...")
        for i in range(30):  # Monitor for up to 30 seconds
            await asyncio.sleep(1)
            
            updated_job = scraping_manager.get_job_status(job.id)
            if not updated_job:
                print("❌ Job not found")
                break
            
            print(f"Status: {updated_job.status.value}, "
                  f"Found: {updated_job.leads_found}, "
                  f"Saved: {updated_job.leads_saved}")
            
            if updated_job.status.value in ['completed', 'failed', 'cancelled']:
                break
        
        # Show final results
        final_job = scraping_manager.get_job_status(job.id)
        if final_job:
            print(f"\n📋 Final Results:")
            print(f"   Status: {final_job.status.value}")
            print(f"   Leads found: {final_job.leads_found}")
            print(f"   Leads saved: {final_job.leads_saved}")
            
            if final_job.completed_at and final_job.started_at:
                duration = (final_job.completed_at - final_job.started_at).total_seconds()
                print(f"   Duration: {duration:.2f} seconds")
            
            if final_job.errors:
                print(f"   Errors: {len(final_job.errors)}")
                for error in final_job.errors[:3]:
                    print(f"     - {error}")
            
            if final_job.warnings:
                print(f"   Warnings: {len(final_job.warnings)}")
                for warning in final_job.warnings[:3]:
                    print(f"     - {warning}")
        
        # Test suggestions
        print(f"\n💡 Testing suggestions...")
        suggestions = await scraping_manager.get_scraping_suggestions("restaurante")
        print(f"Suggestions for 'restaurante': {suggestions}")
        
        # Test statistics
        print(f"\n📈 Testing statistics...")
        stats = scraping_manager.get_scraping_stats()
        print(f"Scraping stats: {stats}")
        
        print(f"\n✅ Scraping system test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

def test_scraping_config():
    """Test scraping configuration"""
    print("\n🔧 Testing Scraping Configuration")
    print("-" * 30)
    
    from src.scraping.config import ScrapingConfig as Config, SCRAPING_TEMPLATES
    
    # Test configuration values
    print(f"Default delay: {Config.DEFAULT_DELAY}s")
    print(f"Max concurrent jobs: {Config.MAX_CONCURRENT_JOBS}")
    print(f"Request timeout: {Config.REQUEST_TIMEOUT}s")
    print(f"User agent: {Config.USER_AGENT}")
    
    # Test source-specific configs
    print(f"\nSource configurations:")
    for source in ["google_maps", "linkedin", "company_website"]:
        config = Config.get_source_config(source)
        print(f"  {source}: {config}")
    
    # Test templates
    print(f"\nAvailable templates:")
    for template_id, template in SCRAPING_TEMPLATES.items():
        print(f"  {template_id}: {template['name']}")

def test_scraping_utils():
    """Test scraping utilities"""
    print("\n🛠️ Testing Scraping Utils")
    print("-" * 25)
    
    from src.scraping.utils import (
        clean_text, extract_email, extract_phone_br, 
        normalize_company_name, is_business_email
    )
    
    # Test text cleaning
    test_text = "  EMPRESA DE TECNOLOGIA LTDA.  "
    cleaned = clean_text(test_text)
    normalized = normalize_company_name(test_text)
    print(f"Original: '{test_text}'")
    print(f"Cleaned: '{cleaned}'")
    print(f"Normalized: '{normalized}'")
    
    # Test email extraction
    test_email_text = "Entre em contato: contato@empresa.com ou vendas@business.com.br"
    email = extract_email(test_email_text)
    is_business = is_business_email(email) if email else False
    print(f"\nEmail text: '{test_email_text}'")
    print(f"Extracted email: {email}")
    print(f"Is business email: {is_business}")
    
    # Test phone extraction
    test_phone_text = "Telefone: (11) 99999-9999 ou WhatsApp 11 98888-8888"
    phone = extract_phone_br(test_phone_text)
    print(f"\nPhone text: '{test_phone_text}'")
    print(f"Extracted phone: {phone}")

async def main():
    """Run all tests"""
    try:
        # Test configuration
        test_scraping_config()
        
        # Test utilities
        test_scraping_utils()
        
        # Test scraping system (commented out by default to avoid actual scraping)
        print(f"\n⚠️  Actual scraping test is disabled by default.")
        print(f"   Uncomment the line below to test real scraping (be respectful!):")
        print(f"   # await test_scraping_system()")
        
        # Uncomment the line below to test actual scraping
        # await test_scraping_system()
        
        print(f"\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())