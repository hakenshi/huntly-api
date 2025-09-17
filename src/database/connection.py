from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import redis
import os
import logging

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://huntly_user:huntly_pass@localhost:5432/huntly")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# PostgreSQL Connection
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=20,
    pool_pre_ping=True,
    echo=os.getenv("ENVIRONMENT") == "development"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis Connection
redis_client = None
try:
    redis_client = redis.from_url(
        REDIS_URL,
        max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
        decode_responses=True
    )
    # Test connection
    redis_client.ping()
    logging.info("Redis connection established successfully")
except Exception as e:
    logging.warning(f"Redis connection failed: {e}. Cache will be disabled.")
    redis_client = None

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis():
    """Redis dependency for FastAPI"""
    return redis_client

def get_redis_client():
    """Get Redis client for scraping system"""
    return redis_client

def get_db_session():
    """Get database session for scraping system"""
    return SessionLocal()

def create_tables():
    """Create all database tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    logging.info("Database tables created successfully")