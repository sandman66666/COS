"""
Knowledge Integration Service for connecting entity extraction, knowledge graph, and task generation.
This service integrates with the existing email processing pipeline.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

from services.knowledge_graph_service import KnowledgeGraphService
from services.entity_extraction_service import EntityExtractionService
from models.database.tasks import Task

logger = logging.getLogger(__name__)

class KnowledgeIntegrationService:
    """Service for integrating entity extraction, knowledge graph, and task generation"""
    
    def __init__(self, db_session_factory, claude_client=None):
        """
        Initialize the knowledge integration service
        
        Args:
            db_session_factory: SQLAlchemy session factory for database operations
            claude_client: Claude API client for entity extraction
        """
        self.db_session_factory = db_session_factory
        self.entity_extraction_service = EntityExtractionService(claude_client)
        
        # Initialize knowledge graph service with error handling
        try:
            self.knowledge_graph_service = KnowledgeGraphService()
            self.kg_enabled = self.knowledge_graph_service.driver is not None
        except Exception as e:
            logger.error(f"Failed to initialize knowledge graph service: {str(e)}")
            self.knowledge_graph_service = None
            self.kg_enabled = False
            
        logger.info(f"Initialized Knowledge Integration Service (KG enabled: {self.kg_enabled})")
    
    def close(self):
        """Close connections"""
        if self.knowledge_graph_service:
            self.knowledge_graph_service.close()
    
    def process_email(self, user_email: str, email_content: str, email_metadata: Dict) -> Dict:
        """
        Process an email to extract entities, update knowledge graph, and generate tasks
        
        Args:
            user_email: The email of the user
            email_content: The content of the email
            email_metadata: Metadata about the email (sender, recipients, subject, date, id)
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing email for knowledge integration: {email_metadata.get('subject', 'No subject')}")
        
        # Extract entities from email
        entities = self.entity_extraction_service.extract_entities_from_email(
            email_content, email_metadata)
        
        # Generate tasks from email
        tasks = self.entity_extraction_service.extract_tasks_from_email(
            email_content, email_metadata)
        
        # Save tasks to database
        saved_tasks = self._save_tasks_to_database(user_email, tasks)
        
        # Update knowledge graph with entities if available
        knowledge_graph_updated = False
        if self.kg_enabled and self.knowledge_graph_service:
            try:
                self._update_knowledge_graph(user_email, entities, email_metadata)
                knowledge_graph_updated = True
            except Exception as e:
                logger.error(f"Failed to update knowledge graph: {str(e)}")
        
        return {
            "entities_extracted": entities,
            "tasks_generated": len(saved_tasks),
            "knowledge_graph_updated": knowledge_graph_updated
        }
    
    def _save_tasks_to_database(self, user_email: str, tasks: List[Dict]) -> List[Task]:
        """
        Save extracted tasks to the database
        
        Args:
            user_email: The email of the user
            tasks: List of tasks extracted from email
            
        Returns:
            List of saved Task objects
        """
        saved_tasks = []
        
        # Create database session
        session = self.db_session_factory()
        
        try:
            for task_data in tasks:
                # Parse deadline if it's a string
                deadline = None
                if isinstance(task_data.get('deadline'), str):
                    try:
                        deadline = datetime.fromisoformat(task_data['deadline'])
                    except (ValueError, TypeError):
                        deadline = None
                
                # Create task object
                task = Task(
                    id=task_data.get('id', str(uuid.uuid4())),
                    user_email=user_email,
                    description=task_data.get('description', ''),
                    deadline=deadline,
                    status="pending",
                    priority=task_data.get('priority', 'medium'),
                    source_type="email",
                    source_id=task_data.get('source_id'),
                    source_snippet=task_data.get('source_snippet'),
                    related_people=task_data.get('related_people', []),
                    related_project_id=task_data.get('related_project')
                )
                
                session.add(task)
                saved_tasks.append(task)
            
            # Commit changes
            session.commit()
            logger.info(f"Saved {len(saved_tasks)} tasks to database for user {user_email}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving tasks to database: {str(e)}")
        finally:
            session.close()
        
        return saved_tasks
    
    def _update_knowledge_graph(self, user_email: str, entities: Dict, email_metadata: Dict) -> bool:
        """
        Update the knowledge graph with extracted entities
        
        Args:
            user_email: The email of the user
            entities: Dictionary of extracted entities
            email_metadata: Metadata about the email
            
        Returns:
            True if knowledge graph was updated successfully, False otherwise
        """
        if not self.kg_enabled or not self.knowledge_graph_service:
            logger.warning("Knowledge graph features disabled, skipping update")
            return False
        
        try:
            # Add the user to the knowledge graph
            self.knowledge_graph_service.create_person(
                email=user_email,
                name=user_email.split('@')[0],
                properties={"is_user": True}
            )
            
            # Add people
            for person in entities.get('people', []):
                person_email = person.get('email')
                if not person_email:
                    # Generate a placeholder email if not available
                    person_email = f"{person['name'].lower().replace(' ', '.')}@unknown.com"
                
                self.knowledge_graph_service.create_person(
                    email=person_email,
                    name=person.get('name', ''),
                    properties={"source": "email"}
                )
                
                # Create relationship with the user
                self.knowledge_graph_service.create_relationship(
                    from_type="Person",
                    from_id=user_email,
                    to_type="Person",
                    to_id=person_email,
                    rel_type="KNOWS",
                    properties={"source": "email", "last_contact": datetime.utcnow().isoformat()}
                )
            
            # Add companies
            for company in entities.get('companies', []):
                self.knowledge_graph_service.create_company(
                    name=company.get('name', ''),
                    properties={"source": "email"}
                )
            
            # Add projects
            for project in entities.get('projects', []):
                project_id = project.get('id', str(uuid.uuid4()))
                self.knowledge_graph_service.create_project(
                    project_id=project_id,
                    name=project.get('name', ''),
                    properties={"source": "email", "description": project.get('description', '')}
                )
            
            # Add tasks
            for task in entities.get('action_items', []):
                task_id = task.get('id', str(uuid.uuid4()))
                self.knowledge_graph_service.create_task(
                    task_id=task_id,
                    description=task.get('description', ''),
                    properties={
                        "deadline": task.get('deadline'),
                        "priority": task.get('priority', 'medium'),
                        "source": "email"
                    }
                )
            
            # Add meetings
            for meeting in entities.get('meetings', []):
                meeting_id = meeting.get('id', str(uuid.uuid4()))
                self.knowledge_graph_service.create_meeting(
                    meeting_id=meeting_id,
                    title=meeting.get('title', ''),
                    properties={
                        "time": meeting.get('time'),
                        "location": meeting.get('location'),
                        "source": "email"
                    }
                )
            
            # Add relationships
            for relationship in entities.get('relationships', []):
                # Determine entity types
                source_type = relationship.get('source_type', 'Person')
                target_type = relationship.get('target_type', 'Person')
                
                # Get entity IDs
                source_id = relationship.get('source')
                target_id = relationship.get('target')
                
                # Skip if missing IDs
                if not source_id or not target_id:
                    continue
                
                # Create relationship
                self.knowledge_graph_service.create_relationship(
                    from_type=source_type,
                    from_id=source_id,
                    to_type=target_type,
                    to_id=target_id,
                    rel_type=relationship.get('type', 'RELATED_TO').upper(),
                    properties={"source": "email"}
                )
            
            logger.info(f"Updated knowledge graph with entities from email: {email_metadata.get('subject', 'No subject')}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating knowledge graph: {str(e)}")
            return False
    
    def get_tasks_for_user(self, user_email: str, status: Optional[str] = None, 
                          limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Get tasks for a user from the database
        
        Args:
            user_email: The email of the user
            status: Optional filter by task status
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            
        Returns:
            List of task dictionaries
        """
        tasks = []
        
        # Create database session
        session = self.db_session_factory()
        
        try:
            # Build query
            query = session.query(Task).filter(Task.user_email == user_email)
            
            # Apply status filter if provided
            if status:
                query = query.filter(Task.status == status)
            
            # Order by deadline (null last) and creation date
            query = query.order_by(
                Task.deadline.is_(None).asc(),
                Task.deadline.asc(),
                Task.created_at.desc()
            )
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute query
            task_objects = query.all()
            
            # Convert to dictionaries
            for task in task_objects:
                tasks.append(task.to_dict())
            
            logger.info(f"Retrieved {len(tasks)} tasks for user {user_email}")
            
        except Exception as e:
            logger.error(f"Error retrieving tasks from database: {str(e)}")
        finally:
            session.close()
        
        return tasks
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """
        Update the status of a task
        
        Args:
            task_id: The ID of the task
            status: The new status of the task
            
        Returns:
            True if task was updated successfully, False otherwise
        """
        # Create database session
        session = self.db_session_factory()
        
        try:
            # Get task
            task = session.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                logger.warning(f"Task not found: {task_id}")
                return False
            
            # Update status
            task.status = status
            
            # Update completed_at if status is 'completed'
            if status == "completed":
                task.completed_at = datetime.utcnow()
            
            # Commit changes
            session.commit()
            logger.info(f"Updated task {task_id} status to {status}")
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating task status: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_knowledge_graph_statistics(self) -> Dict:
        """
        Get statistics about the knowledge graph
        
        Returns:
            Dictionary with knowledge graph statistics
        """
        if not self.kg_enabled or not self.knowledge_graph_service:
            return {"error": "Knowledge graph is not enabled or configured properly"}
            
        try:
            return self.knowledge_graph_service.get_graph_statistics()
        except Exception as e:
            logger.error(f"Error getting knowledge graph statistics: {str(e)}")
            return {"error": str(e)}
