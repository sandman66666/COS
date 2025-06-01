"""
Database models for storing tasks extracted from emails and messages.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from models.database.base import Base

class Task(Base):
    """Model for storing automatically generated tasks from emails and messages"""
    __tablename__ = "tasks"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String(255), ForeignKey("user_intelligence.user_email"), nullable=False)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")  # pending, in_progress, completed
    priority = Column(String(50), default="medium")  # high, medium, low
    
    # Source information
    source_type = Column(String(50))  # email, message, calendar
    source_id = Column(String(255))  # ID of the source item (e.g., email ID)
    source_snippet = Column(Text, nullable=True)  # Snippet of text that generated this task
    
    # Related entities
    related_people = Column(JSON, default=list)  # List of people emails related to this task
    related_project_id = Column(String(36), nullable=True)  # ID of related project
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship to UserIntelligence
    user_intelligence = relationship("UserIntelligence", back_populates="tasks")
    
    def to_dict(self):
        """Convert task to dictionary for API responses"""
        return {
            "id": self.id,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
            "priority": self.priority,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "related_people": self.related_people,
            "related_project_id": self.related_project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
