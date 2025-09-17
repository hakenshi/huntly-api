"""
Models for lead scraping system
"""

from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class ScrapingSource(str, Enum):
    """Available scraping sources"""
    GOOGLE_MAPS = "google_maps"
    LINKEDIN = "linkedin"
    COMPANY_WEBSITE = "company_website"
    YELLOW_PAGES = "yellow_pages"
    CRUNCHBASE = "crunchbase"
    CUSTOM_API = "custom_api"

class ScrapingStatus(str, Enum):
    """Scraping job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScrapedLead(BaseModel):
    """Model for scraped lead data"""
    # Basic company info
    company: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    
    # Location and industry
    industry: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    
    # Company details
    description: Optional[str] = None
    revenue: Optional[str] = None
    employees: Optional[str] = None
    founded_year: Optional[int] = None
    
    # Social media and online presence
    linkedin_url: Optional[HttpUrl] = None
    facebook_url: Optional[HttpUrl] = None
    twitter_url: Optional[HttpUrl] = None
    
    # Scraping metadata
    source: ScrapingSource
    source_url: Optional[HttpUrl] = None
    scraped_at: datetime
    confidence_score: float = 0.0  # 0-1 score for data quality
    raw_data: Dict[str, Any] = {}  # Original scraped data
    
    # Keywords and tags
    keywords: List[str] = []
    tags: List[str] = []

class ScrapingConfig(BaseModel):
    """Configuration for scraping jobs"""
    # Search parameters
    search_query: str
    location: Optional[str] = None
    industry: Optional[str] = None
    
    # Scraping limits
    max_results: int = 100
    max_pages: int = 10
    delay_between_requests: float = 1.0  # seconds
    
    # Filtering
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    required_fields: List[str] = []  # Fields that must be present
    
    # Sources to use
    sources: List[ScrapingSource] = [ScrapingSource.GOOGLE_MAPS]
    
    # Advanced options
    use_proxy: bool = False
    proxy_rotation: bool = False
    respect_robots_txt: bool = True
    user_agent: Optional[str] = None

class ScrapingJob(BaseModel):
    """Model for scraping job tracking"""
    id: str
    user_id: int
    config: ScrapingConfig
    status: ScrapingStatus = ScrapingStatus.PENDING
    
    # Progress tracking
    total_expected: Optional[int] = None
    leads_found: int = 0
    leads_processed: int = 0
    leads_saved: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Results and errors
    results_summary: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []
    
    # Metadata
    created_at: datetime
    updated_at: datetime

class ScrapingResult(BaseModel):
    """Result of a scraping operation"""
    job_id: str
    leads: List[ScrapedLead]
    total_found: int
    total_processed: int
    success_rate: float
    execution_time: float
    errors: List[str] = []
    warnings: List[str] = []

class LeadValidationResult(BaseModel):
    """Result of lead data validation"""
    is_valid: bool
    confidence_score: float
    issues: List[str] = []
    suggestions: List[str] = []
    enhanced_data: Dict[str, Any] = {}  # Additional data found during validation