import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from models.database.base import Base


class Project(Base):
    """Model for storing user-defined projects and initiatives."""
    __tablename__ = "projects"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String(255), ForeignKey("user_intelligence.user_email"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, planning, on_hold, completed
    priority = Column(String(50), nullable=True)  # high, medium, low
    stakeholders = Column(JSON, default=list)  # List of stakeholder names
    keywords = Column(JSON, default=list)  # Keywords for matching emails to this project
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to UserIntelligence
    user_intelligence = relationship("UserIntelligence", back_populates="projects")

    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "stakeholders": self.stakeholders,
            "keywords": self.keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Goal(Base):
    """Model for storing user-defined personal and professional goals."""
    __tablename__ = "goals"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String(255), ForeignKey("user_intelligence.user_email"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="professional")  # professional, personal, learning, financial, other
    timeframe = Column(String(50), default="medium_term")  # short_term, medium_term, long_term
    metrics = Column(Text, nullable=True)  # Success metrics
    keywords = Column(JSON, default=list)  # Keywords for matching emails to this goal
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to UserIntelligence
    user_intelligence = relationship("UserIntelligence", back_populates="goals")

    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "timeframe": self.timeframe,
            "metrics": self.metrics,
            "keywords": self.keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class KnowledgeFile(Base):
    """Model for storing uploaded knowledge base files."""
    __tablename__ = "knowledge_files"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String(255), ForeignKey("user_intelligence.user_email"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(100), nullable=False)  # MIME type
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general")  # general, product, marketing, etc.
    is_processed = Column(Boolean, default=False)  # Whether the file has been processed for knowledge extraction
    content_extracted = Column(Text, nullable=True)  # Extracted text content from the file
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to UserIntelligence
    user_intelligence = relationship("UserIntelligence", back_populates="knowledge_files")

    def to_dict(self) -> Dict[str, Any]:
        """Convert file to dictionary for API responses."""
        return {
            "id": self.id,
            "filename": self.original_filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "description": self.description,
            "category": self.category,
            "is_processed": self.is_processed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
