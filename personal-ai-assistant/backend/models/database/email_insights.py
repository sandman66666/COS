"""
Database models for email insights and people profiles.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
import datetime

from backend.models.database.base import Base

class EmailInsight(Base):
    """
    Stores insights generated from email analysis.
    """
    __tablename__ = "email_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    analysis_date = Column(DateTime, default=datetime.datetime.utcnow)
    days_analyzed = Column(Integer, default=30)
    
    # Insights stored as JSON
    key_relationships = Column(JSON)
    active_projects = Column(JSON)
    communication_patterns = Column(JSON)
    action_items = Column(JSON)
    important_information = Column(JSON)
    
    # Raw response for debugging
    raw_response = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class UrgentEmailAlert(Base):
    """
    Stores urgent email alerts generated from recent email scans.
    """
    __tablename__ = "urgent_email_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    scan_date = Column(DateTime, default=datetime.datetime.utcnow)
    hours_scanned = Column(Integer, default=24)
    
    # Alert data
    urgent_emails = Column(JSON)
    priority_level = Column(String)  # high, medium, low
    summary = Column(Text)
    
    # Status flags
    is_read = Column(Boolean, default=False)
    is_actioned = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PersonProfile(Base):
    """
    Stores profiles of people based on email interactions.
    """
    __tablename__ = "person_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    contact_email = Column(String, index=True)
    contact_name = Column(String)
    
    # Profile data
    interaction_frequency = Column(JSON)
    response_patterns = Column(JSON)
    common_topics = Column(JSON)
    sentiment_analysis = Column(JSON)
    action_items = Column(JSON)
    relationship_context = Column(JSON)
    last_contact_date = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
