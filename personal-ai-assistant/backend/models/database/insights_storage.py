"""
Database models for storing email insights and intelligence data.
This creates persistent storage for your Chief of Staff AI system.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from models.database.base import Base

class UserIntelligence(Base):
    """Stores user-specific business intelligence and insights"""
    __tablename__ = "user_intelligence"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String, unique=True, index=True)
    
    # Different knowledge repositories as per your architecture
    general_business_knowledge = Column(JSON, default={})  # General business context
    personal_knowledge = Column(JSON, default={})  # User-specific knowledge
    contacts_knowledge = Column(JSON, default={})  # People and relationships
    personal_goals = Column(JSON, default={})  # Goals and objectives
    tactical_notifications = Column(JSON, default=[])  # Real-time action items
    
    # Email analysis results
    last_email_analysis = Column(JSON, default={})
    email_insights_cache = Column(JSON, default={})
    
    # Relationships to structured knowledge models - using string references to avoid circular imports
    projects = relationship("Project", back_populates="user_intelligence", cascade="all, delete-orphan", lazy="dynamic")
    goals = relationship("Goal", back_populates="user_intelligence", cascade="all, delete-orphan", lazy="dynamic")
    knowledge_files = relationship("KnowledgeFile", back_populates="user_intelligence", cascade="all, delete-orphan", lazy="dynamic")
    tasks = relationship("Task", back_populates="user_intelligence", cascade="all, delete-orphan", lazy="dynamic")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailSyncStatus(Base):
    """Tracks email sync operations and results"""
    __tablename__ = "email_sync_status"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String, index=True)
    sync_type = Column(String)  # 'full', 'incremental', 'urgent'
    status = Column(String)  # 'pending', 'processing', 'completed', 'failed'
    progress = Column(Integer, default=0)
    
    # Sync results
    emails_processed = Column(Integer, default=0)
    insights_generated = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ContactIntelligence(Base):
    """Stores intelligence about individual contacts"""
    __tablename__ = "contact_intelligence"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String, index=True)
    contact_email = Column(String, index=True)
    contact_name = Column(String)
    
    # Relationship intelligence
    relationship_strength = Column(String)  # 'strong', 'medium', 'weak'
    interaction_frequency = Column(JSON)  # Pattern data
    communication_style = Column(JSON)  # Preferences and patterns
    topics_discussed = Column(JSON)  # Common topics
    
    # Context and history
    first_interaction = Column(DateTime)
    last_interaction = Column(DateTime)
    total_interactions = Column(Integer, default=0)
    
    # AI-generated insights
    relationship_summary = Column(Text)
    action_items = Column(JSON, default=[])
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)