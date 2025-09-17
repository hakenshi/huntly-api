"""
Database module for Huntly MVP
Handles PostgreSQL and Redis connections
"""

from .connection import get_db, get_redis, create_tables, engine, SessionLocal, redis_client
from .models import Base, User, Lead, Campaign, UserPreferences
from .migrations import run_migrations, create_search_indexes
from .seeder import seed_users

__all__ = [
    "get_db", "get_redis", "create_tables", "engine", "SessionLocal", "redis_client",
    "Base", "User", "Lead", "Campaign", "UserPreferences",
    "run_migrations", "create_search_indexes",
    "seed_users"
]