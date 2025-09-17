from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, ARRAY, Float, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    plan_type = Column(String(50), default="starter")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    leads = relationship("Lead", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Basic lead information
    company = Column(String(255), nullable=False)
    contact = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))
    
    # Classification fields
    industry = Column(String(100))
    location = Column(String(255))
    revenue = Column(String(50))
    employees = Column(String(50))
    
    # Search and scoring fields
    description = Column(Text)
    keywords = Column(ARRAY(String))
    score = Column(Integer, default=0)
    status = Column(String(50), default="Novo")
    priority = Column(String(50), default="Média")
    
    # Indexing and timestamps
    search_vector = Column(TSVECTOR)
    indexed_at = Column(DateTime)
    last_contact = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="leads")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(255), nullable=False)
    
    # Campaign configuration
    search_query = Column(Text)
    filters = Column(JSON)
    status = Column(String(50), default="Ativa")
    
    # Campaign metrics
    leads_found = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    responses = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    
    # Execution info
    next_execution = Column(String(100))
    last_execution = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="campaigns")

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Search preferences
    preferred_industries = Column(ARRAY(String))
    preferred_locations = Column(ARRAY(String))
    company_size_range = Column(String(50))
    revenue_range = Column(String(50))
    
    # Scoring weights
    scoring_weights = Column(JSON, default={
        "industry_match": 0.25,
        "location_proximity": 0.15,
        "company_size": 0.1,
        "text_relevance": 0.4,
        "data_quality": 0.1
    })
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="preferences")

# Create indexes for performance
Index('idx_leads_industry', Lead.industry)
Index('idx_leads_location', Lead.location)
Index('idx_leads_company_text', Lead.search_vector, postgresql_using='gin')
Index('idx_leads_keywords', Lead.keywords, postgresql_using='gin')
Index('idx_leads_user_status', Lead.user_id, Lead.status)
Index('idx_campaigns_user_status', Campaign.user_id, Campaign.status)
