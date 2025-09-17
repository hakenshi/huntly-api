from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.auth.routes import router as auth_router
from src.routes.leads import router as leads_router
from src.routes.campaigns import router as campaigns_router
from src.routes.analytics import router as analytics_router
from src.database.connection import create_tables, get_redis
from src.database.migrations import run_migrations
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Huntly API", 
    version="1.0.0",
    description="Discovery engine for lead generation and qualification"
)

# CORS - permite frontend em produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://*.railway.app",
        os.getenv("FRONTEND_URL", "")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    try:
        # Create database tables
        create_tables()
        logger.info("Database tables created successfully")
        
        # Run migrations
        migration_success = run_migrations()
        if migration_success:
            logger.info("Database migrations completed successfully")
        else:
            logger.warning("Database migrations failed - some features may be limited")
        
        # Test Redis connection
        redis_client = get_redis()
        if redis_client:
            logger.info("Redis connection established")
        else:
            logger.warning("Redis not available - cache disabled")
            
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# Include routers
app.include_router(auth_router)
app.include_router(leads_router)
app.include_router(campaigns_router)
app.include_router(analytics_router)

# Include preferences router
from src.routes.preferences import router as preferences_router
app.include_router(preferences_router)

# Import and include scraping router
try:
    from src.routes.scraping import router as scraping_router
    app.include_router(scraping_router)
    logger.info("Scraping routes registered successfully")
except ImportError as e:
    logger.warning(f"Scraping routes not available: {e}")

@app.get("/")
def root():
    return {
        "message": "Huntly API", 
        "version": "1.0.0", 
        "status": "running",
        "description": "Discovery engine for lead generation"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    redis_client = get_redis()
    
    # Check scraping system availability
    scraping_available = False
    try:
        from src.scraping.manager import ScrapingManager
        scraping_available = True
    except ImportError:
        pass
    
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected" if redis_client else "disconnected",
        "scraping": "available" if scraping_available else "unavailable",
        "version": "1.0.0",
        "features": {
            "search": True,
            "authentication": True,
            "caching": bool(redis_client),
            "scraping": scraping_available
        }
    }
