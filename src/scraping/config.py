"""
Scraping system configuration
"""
import os
from typing import Dict, List

class ScrapingConfig:
    """Configuration for scraping system"""
    
    # Rate limiting settings
    DEFAULT_DELAY = float(os.getenv("SCRAPING_DEFAULT_DELAY", "1.0"))
    GOOGLE_MAPS_DELAY = float(os.getenv("SCRAPING_GOOGLE_MAPS_DELAY", "1.0"))
    LINKEDIN_DELAY = float(os.getenv("SCRAPING_LINKEDIN_DELAY", "2.0"))
    WEBSITE_DELAY = float(os.getenv("SCRAPING_WEBSITE_DELAY", "1.5"))
    
    # Job management
    MAX_CONCURRENT_JOBS = int(os.getenv("SCRAPING_MAX_CONCURRENT_JOBS", "5"))
    MAX_RESULTS_PER_JOB = int(os.getenv("SCRAPING_MAX_RESULTS_PER_JOB", "1000"))
    JOB_CLEANUP_DELAY = int(os.getenv("SCRAPING_JOB_CLEANUP_DELAY", "3600"))  # 1 hour
    
    # Request settings
    REQUEST_TIMEOUT = int(os.getenv("SCRAPING_REQUEST_TIMEOUT", "30"))
    SESSION_TIMEOUT = int(os.getenv("SCRAPING_SESSION_TIMEOUT", "300"))
    MAX_RETRIES = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
    
    # Proxy settings (optional)
    PROXY_URL = os.getenv("SCRAPING_PROXY_URL")
    PROXY_ROTATION = os.getenv("SCRAPING_PROXY_ROTATION", "false").lower() == "true"
    
    # User agent
    USER_AGENT = os.getenv(
        "SCRAPING_USER_AGENT", 
        "Mozilla/5.0 (compatible; HuntlyBot/1.0; +https://huntly.com/bot)"
    )
    
    # Compliance settings
    RESPECT_ROBOTS_TXT = os.getenv("SCRAPING_RESPECT_ROBOTS_TXT", "true").lower() == "true"
    
    @classmethod
    def get_delay_for_source(cls, source: str) -> float:
        """Get delay setting for specific source"""
        delay_map = {
            "google_maps": cls.GOOGLE_MAPS_DELAY,
            "linkedin": cls.LINKEDIN_DELAY,
            "company_website": cls.WEBSITE_DELAY,
        }
        return delay_map.get(source, cls.DEFAULT_DELAY)
    
    @classmethod
    def get_source_config(cls, source: str) -> Dict[str, any]:
        """Get configuration for specific scraping source"""
        configs = {
            "google_maps": {
                "delay": cls.GOOGLE_MAPS_DELAY,
                "timeout": cls.REQUEST_TIMEOUT,
                "max_retries": cls.MAX_RETRIES,
                "respect_robots": cls.RESPECT_ROBOTS_TXT
            },
            "linkedin": {
                "delay": cls.LINKEDIN_DELAY,
                "timeout": cls.REQUEST_TIMEOUT * 2,  # LinkedIn needs more time
                "max_retries": cls.MAX_RETRIES,
                "respect_robots": cls.RESPECT_ROBOTS_TXT,
                "requires_auth": True
            },
            "company_website": {
                "delay": cls.WEBSITE_DELAY,
                "timeout": cls.REQUEST_TIMEOUT,
                "max_retries": cls.MAX_RETRIES,
                "respect_robots": cls.RESPECT_ROBOTS_TXT
            }
        }
        return configs.get(source, {})

# Default scraping templates for different industries
SCRAPING_TEMPLATES = {
    "technology": {
        "name": "Empresas de Tecnologia",
        "description": "Buscar empresas de software e tecnologia",
        "search_terms": ["software", "tecnologia", "desenvolvimento", "startup", "saas"],
        "sources": ["google_maps", "linkedin", "company_website"],
        "required_fields": ["company", "email"],
        "filters": {
            "industry": "Tecnologia",
            "min_employees": 5,
            "max_employees": 200
        }
    },
    "restaurants": {
        "name": "Restaurantes e Alimentação",
        "description": "Buscar restaurantes e empresas de alimentação",
        "search_terms": ["restaurante", "comida", "delivery", "alimentação"],
        "sources": ["google_maps"],
        "required_fields": ["company", "phone"],
        "filters": {
            "industry": "Alimentação"
        }
    },
    "professional_services": {
        "name": "Serviços Profissionais",
        "description": "Advogados, contadores, consultores",
        "search_terms": ["advogado", "contador", "consultor", "serviços"],
        "sources": ["google_maps", "linkedin"],
        "required_fields": ["company", "phone"],
        "filters": {
            "industry": "Serviços"
        }
    },
    "ecommerce": {
        "name": "E-commerce",
        "description": "Lojas online e e-commerce",
        "search_terms": ["loja online", "ecommerce", "marketplace", "vendas"],
        "sources": ["company_website", "google_maps"],
        "required_fields": ["company", "website"],
        "filters": {
            "industry": "E-commerce"
        }
    },
    "healthcare": {
        "name": "Saúde e Bem-estar",
        "description": "Clínicas, hospitais, profissionais de saúde",
        "search_terms": ["clínica", "hospital", "médico", "dentista", "saúde"],
        "sources": ["google_maps"],
        "required_fields": ["company", "phone"],
        "filters": {
            "industry": "Saúde"
        }
    }
}