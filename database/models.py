from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
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
    
    leads = relationship("Lead", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_name = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))
    industry = Column(String(100))
    company_size = Column(String(50))
    revenue = Column(String(50))
    location = Column(String(255))
    status = Column(String(50), default="new")
    score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="leads")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(255), nullable=False)
    filters = Column(JSON)
    status = Column(String(50), default="active")
    leads_found = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="campaigns")
