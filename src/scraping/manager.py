"""
Scraping Manager - Orchestrates lead scraping from multiple sources
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import (
    ScrapingJob, ScrapingConfig, ScrapingResult, ScrapedLead, 
    ScrapingStatus, ScrapingSource
)
from .scrapers.base import BaseScraper
from .scrapers.google_maps import GoogleMapsScraper
from .scrapers.linkedin import LinkedInScraper
from .scrapers.company_websites import CompanyWebsiteScraper

from ..database.models import Lead as LeadModel
from ..search.indexer import LeadIndexer
from ..cache.manager import CacheManager

logger = logging.getLogger(__name__)

class ScrapingManager:
    """Manages lead scraping operations across multiple sources"""
    
    def __init__(self, db_session: Session, cache_manager: CacheManager):
        self.db = db_session
        self.cache = cache_manager
        self.indexer = LeadIndexer(db_session, cache_manager)
        
        # Active jobs tracking
        self.active_jobs: Dict[str, ScrapingJob] = {}
        
        # Scraper registry
        self.scrapers = {
            ScrapingSource.GOOGLE_MAPS: GoogleMapsScraper,
            ScrapingSource.LINKEDIN: LinkedInScraper,
            ScrapingSource.COMPANY_WEBSITE: CompanyWebsiteScraper,
        }
    
    async def start_scraping_job(
        self, 
        user_id: int, 
        config: ScrapingConfig
    ) -> ScrapingJob:
        """Start a new scraping job"""
        
        # Create job
        job = ScrapingJob(
            id=str(uuid.uuid4()),
            user_id=user_id,
            config=config,
            status=ScrapingStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store job
        self.active_jobs[job.id] = job
        
        # Start scraping in background
        asyncio.create_task(self._execute_scraping_job(job))
        
        logger.info(f"Started scraping job {job.id} for user {user_id}")
        
        return job
    
    async def _execute_scraping_job(self, job: ScrapingJob):
        """Execute a scraping job"""
        
        try:
            # Update job status
            job.status = ScrapingStatus.RUNNING
            job.started_at = datetime.now()
            job.updated_at = datetime.now()
            
            logger.info(f"Executing scraping job {job.id}")
            
            all_leads = []
            total_processed = 0
            
            # Run scrapers for each configured source
            for source in job.config.sources:
                if source not in self.scrapers:
                    job.warnings.append(f"Scraper not available for source: {source}")
                    continue
                
                logger.info(f"Running {source} scraper for job {job.id}")
                
                try:
                    # Create scraper instance
                    scraper_class = self.scrapers[source]
                    scraper = scraper_class(job.config)
                    
                    # Run scraper
                    async with scraper:
                        async for lead in scraper.scrape_leads():
                            all_leads.append(lead)
                            job.leads_found += 1
                            
                            # Update job progress
                            job.updated_at = datetime.now()
                            
                            # Save lead to database
                            if await self._save_lead_to_database(lead, job.user_id):
                                job.leads_saved += 1
                            
                            total_processed += 1
                            
                            # Check if we've reached the limit
                            if total_processed >= job.config.max_results:
                                break
                    
                    # Add scraper stats to job
                    scraper_stats = scraper.get_stats()
                    job.results_summary[source] = scraper_stats
                    job.errors.extend(scraper.errors)
                    job.warnings.extend(scraper.warnings)
                    
                except Exception as e:
                    error_msg = f"Error in {source} scraper: {str(e)}"
                    logger.error(error_msg)
                    job.errors.append(error_msg)
            
            # Update final job status
            job.leads_processed = total_processed
            job.status = ScrapingStatus.COMPLETED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            
            # Calculate success rate
            success_rate = (job.leads_saved / max(job.leads_found, 1)) * 100
            job.results_summary['overall'] = {
                'total_found': job.leads_found,
                'total_saved': job.leads_saved,
                'success_rate': success_rate,
                'execution_time': (job.completed_at - job.started_at).total_seconds()
            }
            
            logger.info(f"Completed scraping job {job.id}: {job.leads_saved} leads saved")
            
        except Exception as e:
            # Job failed
            job.status = ScrapingStatus.FAILED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            job.errors.append(f"Job execution failed: {str(e)}")
            
            logger.error(f"Scraping job {job.id} failed: {e}")
        
        finally:
            # Clean up job from active jobs after some time
            asyncio.create_task(self._cleanup_job(job.id, delay=3600))  # 1 hour
    
    async def _save_lead_to_database(self, scraped_lead: ScrapedLead, user_id: int) -> bool:
        """Save scraped lead to database"""
        
        try:
            # Check if lead already exists (by company name and location)
            existing_lead = self.db.query(LeadModel).filter(
                LeadModel.company.ilike(f"%{scraped_lead.company}%"),
                LeadModel.user_id == user_id
            ).first()
            
            if existing_lead:
                logger.debug(f"Lead already exists: {scraped_lead.company}")
                return False
            
            # Create new lead
            lead = LeadModel(
                user_id=user_id,
                company=scraped_lead.company,
                contact=scraped_lead.contact,
                email=scraped_lead.email,
                phone=scraped_lead.phone,
                website=str(scraped_lead.website) if scraped_lead.website else None,
                industry=scraped_lead.industry,
                location=scraped_lead.location,
                revenue=scraped_lead.revenue,
                employees=scraped_lead.employees,
                description=scraped_lead.description,
                keywords=scraped_lead.keywords,
                score=int(scraped_lead.confidence_score * 100),  # Convert to 0-100 scale
                status="Novo",
                priority="Média",
                created_at=datetime.now()
            )
            
            self.db.add(lead)
            self.db.commit()
            self.db.refresh(lead)
            
            # Index the lead for search
            self.indexer.index_lead(lead)
            
            logger.debug(f"Saved lead to database: {scraped_lead.company}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving lead {scraped_lead.company}: {e}")
            self.db.rollback()
            return False
    
    async def _cleanup_job(self, job_id: str, delay: int = 3600):
        """Clean up completed job after delay"""
        await asyncio.sleep(delay)
        
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job.status in [ScrapingStatus.COMPLETED, ScrapingStatus.FAILED, ScrapingStatus.CANCELLED]:
                del self.active_jobs[job_id]
                logger.info(f"Cleaned up job {job_id}")
    
    def get_job_status(self, job_id: str) -> Optional[ScrapingJob]:
        """Get status of a scraping job"""
        return self.active_jobs.get(job_id)
    
    def get_active_jobs(self, user_id: Optional[int] = None) -> List[ScrapingJob]:
        """Get all active jobs, optionally filtered by user"""
        jobs = list(self.active_jobs.values())
        
        if user_id:
            jobs = [job for job in jobs if job.user_id == user_id]
        
        return jobs
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running scraping job"""
        job = self.active_jobs.get(job_id)
        
        if not job:
            return False
        
        if job.status == ScrapingStatus.RUNNING:
            job.status = ScrapingStatus.CANCELLED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            
            logger.info(f"Cancelled scraping job {job_id}")
            return True
        
        return False
    
    async def get_scraping_suggestions(self, query: str) -> Dict[str, Any]:
        """Get suggestions for scraping configuration based on query"""
        
        suggestions = {
            "recommended_sources": [],
            "estimated_results": 0,
            "suggested_filters": {},
            "similar_queries": []
        }
        
        # Analyze query to suggest best sources
        query_lower = query.lower()
        
        # Always suggest Google Maps for local businesses
        suggestions["recommended_sources"].append(ScrapingSource.GOOGLE_MAPS)
        
        # Suggest LinkedIn for professional services
        if any(term in query_lower for term in ['consulting', 'services', 'agency', 'firm']):
            suggestions["recommended_sources"].append(ScrapingSource.LINKEDIN)
        
        # Suggest company websites for specific industries
        if any(term in query_lower for term in ['tech', 'software', 'startup', 'saas']):
            suggestions["recommended_sources"].append(ScrapingSource.COMPANY_WEBSITE)
        
        # Estimate results based on query specificity
        if len(query.split()) == 1:
            suggestions["estimated_results"] = 500  # Broad query
        elif len(query.split()) <= 3:
            suggestions["estimated_results"] = 200  # Medium specificity
        else:
            suggestions["estimated_results"] = 50   # Very specific
        
        # Suggest filters based on query
        if 'small' in query_lower or 'startup' in query_lower:
            suggestions["suggested_filters"]["max_employees"] = 50
        elif 'large' in query_lower or 'enterprise' in query_lower:
            suggestions["suggested_filters"]["min_employees"] = 100
        
        # Get similar queries from cache (popular searches)
        try:
            popular_searches = self.cache.get_popular_searches(20)
            similar = [s for s in popular_searches if any(word in s.lower() for word in query.split())]
            suggestions["similar_queries"] = similar[:5]
        except:
            pass
        
        return suggestions
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get overall scraping statistics"""
        
        active_jobs = list(self.active_jobs.values())
        
        stats = {
            "active_jobs": len(active_jobs),
            "jobs_by_status": {},
            "total_leads_found": 0,
            "total_leads_saved": 0,
            "average_success_rate": 0,
            "sources_usage": {}
        }
        
        # Calculate stats from active jobs
        success_rates = []
        
        for job in active_jobs:
            # Count by status
            status = job.status.value
            stats["jobs_by_status"][status] = stats["jobs_by_status"].get(status, 0) + 1
            
            # Sum leads
            stats["total_leads_found"] += job.leads_found
            stats["total_leads_saved"] += job.leads_saved
            
            # Track source usage
            for source in job.config.sources:
                source_name = source.value
                stats["sources_usage"][source_name] = stats["sources_usage"].get(source_name, 0) + 1
            
            # Calculate success rate
            if job.leads_found > 0:
                success_rate = (job.leads_saved / job.leads_found) * 100
                success_rates.append(success_rate)
        
        # Average success rate
        if success_rates:
            stats["average_success_rate"] = sum(success_rates) / len(success_rates)
        
        return stats