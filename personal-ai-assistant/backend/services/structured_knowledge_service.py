"""
Service for managing structured knowledge components (projects, goals, files).
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from werkzeug.utils import secure_filename

from sqlalchemy.orm import Session

from models.database.structured_knowledge import Project, Goal, KnowledgeFile
from models.database.insights_storage import UserIntelligence

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx', 'xls', 'xlsx'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class StructuredKnowledgeService:
    """Service for managing structured knowledge components."""

    def __init__(self, session_local):
        """Initialize with database session factory."""
        self.SessionLocal = session_local

    def _get_user_intelligence(self, session: Session, user_email: str) -> UserIntelligence:
        """Get or create UserIntelligence record for a user."""
        user_intel = session.query(UserIntelligence).filter_by(user_email=user_email).first()
        if not user_intel:
            user_intel = UserIntelligence(user_email=user_email)
            session.add(user_intel)
            session.commit()
        return user_intel

    # Project management methods
    def get_projects(self, user_email: str) -> List[Dict[str, Any]]:
        """Get all projects for a user."""
        session = self.SessionLocal()
        try:
            projects = session.query(Project).filter_by(user_email=user_email).all()
            return [project.to_dict() for project in projects]
        finally:
            session.close()

    def get_project(self, user_email: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific project by ID."""
        session = self.SessionLocal()
        try:
            project = session.query(Project).filter_by(user_email=user_email, id=project_id).first()
            return project.to_dict() if project else None
        finally:
            session.close()

    def create_project(self, user_email: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project."""
        session = self.SessionLocal()
        try:
            # Ensure user exists
            self._get_user_intelligence(session, user_email)
            
            # Create project
            project = Project(
                user_email=user_email,
                name=project_data.get('name'),
                description=project_data.get('description'),
                status=project_data.get('status', 'active'),
                priority=project_data.get('priority'),
                stakeholders=project_data.get('stakeholders', []),
                keywords=project_data.get('keywords', [])
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            
            logger.info(f"Created project {project.id} for user {user_email}")
            return project.to_dict()
        finally:
            session.close()

    def update_project(self, user_email: str, project_id: str, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing project."""
        session = self.SessionLocal()
        try:
            project = session.query(Project).filter_by(user_email=user_email, id=project_id).first()
            if not project:
                return None
            
            # Update fields
            if 'name' in project_data:
                project.name = project_data['name']
            if 'description' in project_data:
                project.description = project_data['description']
            if 'status' in project_data:
                project.status = project_data['status']
            if 'priority' in project_data:
                project.priority = project_data['priority']
            if 'stakeholders' in project_data:
                project.stakeholders = project_data['stakeholders']
            if 'keywords' in project_data:
                project.keywords = project_data['keywords']
            
            project.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(project)
            
            logger.info(f"Updated project {project_id} for user {user_email}")
            return project.to_dict()
        finally:
            session.close()

    def delete_project(self, user_email: str, project_id: str) -> bool:
        """Delete a project."""
        session = self.SessionLocal()
        try:
            project = session.query(Project).filter_by(user_email=user_email, id=project_id).first()
            if not project:
                return False
            
            session.delete(project)
            session.commit()
            
            logger.info(f"Deleted project {project_id} for user {user_email}")
            return True
        finally:
            session.close()

    # Goal management methods
    def get_goals(self, user_email: str) -> List[Dict[str, Any]]:
        """Get all goals for a user."""
        session = self.SessionLocal()
        try:
            goals = session.query(Goal).filter_by(user_email=user_email).all()
            return [goal.to_dict() for goal in goals]
        finally:
            session.close()

    def get_goal(self, user_email: str, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific goal by ID."""
        session = self.SessionLocal()
        try:
            goal = session.query(Goal).filter_by(user_email=user_email, id=goal_id).first()
            return goal.to_dict() if goal else None
        finally:
            session.close()

    def create_goal(self, user_email: str, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new goal."""
        session = self.SessionLocal()
        try:
            # Ensure user exists
            self._get_user_intelligence(session, user_email)
            
            # Create goal
            goal = Goal(
                user_email=user_email,
                title=goal_data.get('title'),
                description=goal_data.get('description'),
                category=goal_data.get('category', 'professional'),
                timeframe=goal_data.get('timeframe', 'medium_term'),
                metrics=goal_data.get('metrics'),
                keywords=goal_data.get('keywords', [])
            )
            session.add(goal)
            session.commit()
            session.refresh(goal)
            
            logger.info(f"Created goal {goal.id} for user {user_email}")
            return goal.to_dict()
        finally:
            session.close()

    def update_goal(self, user_email: str, goal_id: str, goal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing goal."""
        session = self.SessionLocal()
        try:
            goal = session.query(Goal).filter_by(user_email=user_email, id=goal_id).first()
            if not goal:
                return None
            
            # Update fields
            if 'title' in goal_data:
                goal.title = goal_data['title']
            if 'description' in goal_data:
                goal.description = goal_data['description']
            if 'category' in goal_data:
                goal.category = goal_data['category']
            if 'timeframe' in goal_data:
                goal.timeframe = goal_data['timeframe']
            if 'metrics' in goal_data:
                goal.metrics = goal_data['metrics']
            if 'keywords' in goal_data:
                goal.keywords = goal_data['keywords']
            
            goal.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(goal)
            
            logger.info(f"Updated goal {goal_id} for user {user_email}")
            return goal.to_dict()
        finally:
            session.close()

    def delete_goal(self, user_email: str, goal_id: str) -> bool:
        """Delete a goal."""
        session = self.SessionLocal()
        try:
            goal = session.query(Goal).filter_by(user_email=user_email, id=goal_id).first()
            if not goal:
                return False
            
            session.delete(goal)
            session.commit()
            
            logger.info(f"Deleted goal {goal_id} for user {user_email}")
            return True
        finally:
            session.close()

    # File management methods
    def allowed_file(self, filename: str) -> bool:
        """Check if file type is allowed."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_knowledge_files(self, user_email: str) -> List[Dict[str, Any]]:
        """Get all knowledge files for a user."""
        session = self.SessionLocal()
        try:
            files = session.query(KnowledgeFile).filter_by(user_email=user_email).all()
            return [file.to_dict() for file in files]
        finally:
            session.close()

    def get_knowledge_file(self, user_email: str, file_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific knowledge file by ID."""
        session = self.SessionLocal()
        try:
            file = session.query(KnowledgeFile).filter_by(user_email=user_email, id=file_id).first()
            return file.to_dict() if file else None
        finally:
            session.close()

    def upload_knowledge_file(self, user_email: str, file, description: str = None, category: str = 'general') -> Optional[Dict[str, Any]]:
        """Upload and store a knowledge file."""
        if not file or not self.allowed_file(file.filename):
            return None
        
        session = self.SessionLocal()
        try:
            # Ensure user exists
            self._get_user_intelligence(session, user_email)
            
            # Generate secure filename and path
            original_filename = file.filename
            filename = secure_filename(original_filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            # Save file
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            file_type = file.content_type or 'application/octet-stream'
            
            # Create database record
            knowledge_file = KnowledgeFile(
                user_email=user_email,
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                description=description,
                category=category
            )
            session.add(knowledge_file)
            session.commit()
            session.refresh(knowledge_file)
            
            logger.info(f"Uploaded knowledge file {knowledge_file.id} for user {user_email}")
            return knowledge_file.to_dict()
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return None
        finally:
            session.close()

    def delete_knowledge_file(self, user_email: str, file_id: str) -> bool:
        """Delete a knowledge file."""
        session = self.SessionLocal()
        try:
            file = session.query(KnowledgeFile).filter_by(user_email=user_email, id=file_id).first()
            if not file:
                return False
            
            # Delete file from filesystem
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
            
            # Delete database record
            session.delete(file)
            session.commit()
            
            logger.info(f"Deleted knowledge file {file_id} for user {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
        finally:
            session.close()

    def process_knowledge_file(self, user_email: str, file_id: str) -> bool:
        """Process a knowledge file to extract content and insights."""
        # This would integrate with Claude or another text extraction service
        # For now, we'll just mark the file as processed
        session = self.SessionLocal()
        try:
            file = session.query(KnowledgeFile).filter_by(user_email=user_email, id=file_id).first()
            if not file:
                return False
            
            # TODO: Implement actual content extraction based on file type
            # For now, just mark as processed
            file.is_processed = True
            file.updated_at = datetime.utcnow()
            session.commit()
            
            logger.info(f"Marked knowledge file {file_id} as processed for user {user_email}")
            return True
        finally:
            session.close()

    # Integration with email insights
    def get_structured_knowledge_for_insights(self, user_email: str) -> Dict[str, Any]:
        """Get all structured knowledge for a user to enhance email insights."""
        session = self.SessionLocal()
        try:
            projects = session.query(Project).filter_by(user_email=user_email).all()
            goals = session.query(Goal).filter_by(user_email=user_email).all()
            
            # Format data for integration with Claude prompts
            structured_knowledge = {
                "projects": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "status": p.status,
                        "priority": p.priority,
                        "stakeholders": p.stakeholders,
                        "keywords": p.keywords
                    } for p in projects
                ],
                "goals": [
                    {
                        "title": g.title,
                        "description": g.description,
                        "category": g.category,
                        "timeframe": g.timeframe,
                        "metrics": g.metrics,
                        "keywords": g.keywords
                    } for g in goals
                ]
            }
            
            return structured_knowledge
        finally:
            session.close()
