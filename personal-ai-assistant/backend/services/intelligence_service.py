"""
Service layer for managing email intelligence and insights.
Handles storage, retrieval, and processing of Chief of Staff data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database.insights_storage import Base, UserIntelligence, EmailSyncStatus, ContactIntelligence
from core.claude_integration.email_intelligence import EmailIntelligence
from services.structured_knowledge_service import StructuredKnowledgeService
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Create a shared engine and metadata
_engine = None
_SessionLocal = None

def get_engine(database_url: str):
    global _engine
    if _engine is None:
        _engine = create_engine(database_url)
        Base.metadata.create_all(_engine)
    return _engine

def get_session_local(database_url: str):
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal

class IntelligenceService:
    """Service for managing user intelligence and insights"""
    
    def __init__(self, database_url: str, claude_client: Anthropic):
        """Initialize the intelligence service with database and Claude client"""
        self.engine = get_engine(database_url)
        self.SessionLocal = get_session_local(database_url)
        self.claude_client = claude_client
        self.email_intelligence = EmailIntelligence(claude_client)
        self.structured_knowledge_service = StructuredKnowledgeService(self.SessionLocal)
    
    def process_and_store_email_insights(self, user_email: str, access_token: str, days_back: int = 30, force_full_sync: bool = False) -> Dict[str, Any]:
        """
        Process emails and store insights in appropriate knowledge repositories.
        This is the main entry point for email sync operations.
        
        Args:
            user_email: The email address of the user
            access_token: Google OAuth access token
            days_back: Number of days to look back for emails
            force_full_sync: If True, forces a full sync even if a previous sync exists
        """
        session = self.SessionLocal()
        try:
            # Check if we have a previous sync for this user
            user_intel = session.query(UserIntelligence).filter_by(user_email=user_email).first()
            last_sync = None
            sync_type = 'full'
            
            if user_intel and user_intel.email_insights_cache and not force_full_sync:
                # Get the last sync time from the cache
                cache = user_intel.email_insights_cache
                if 'generated_at' in cache:
                    last_sync = datetime.fromisoformat(cache['generated_at'])
                    sync_type = 'incremental'
                    logger.info(f"Found previous sync at {last_sync}, performing incremental sync")
            
            if not last_sync:
                logger.info("No previous sync found or full sync forced, performing full sync")
        
            # Create or update sync status
            sync_status = EmailSyncStatus(
                user_email=user_email,
                sync_type=sync_type,
                status='processing',
                progress=10
            )
            session.add(sync_status)
            session.commit()
            
            # Get or create user intelligence record
            user_intel = session.query(UserIntelligence).filter_by(user_email=user_email).first()
            if not user_intel:
                user_intel = UserIntelligence(user_email=user_email)
                session.add(user_intel)
            
            # Analyze emails using EmailIntelligence
            logger.info(f"Analyzing emails for {user_email}")
            sync_status.progress = 30
            session.commit()
            
            # If we have a last sync time, only analyze emails since then
            if sync_type == 'incremental' and last_sync:
                # Calculate days since last sync
                days_since_last_sync = (datetime.utcnow() - last_sync).days + 1  # +1 for overlap
                actual_days_back = min(days_back, days_since_last_sync)
                
                # Get existing insights to provide context for incremental analysis
                existing_insights = None
                if user_intel and user_intel.email_insights_cache:
                    existing_insights = user_intel.email_insights_cache
                    
                    # Log summary of existing insights for debugging
                    relationship_count = len(existing_insights.get('key_relationships', []))
                    project_count = len(existing_insights.get('active_projects', []))
                    action_count = len(existing_insights.get('action_items', []))
                    info_count = len(existing_insights.get('important_information', []))
                    
                    logger.info(f"Providing previous insights as context for incremental analysis: "
                              f"{relationship_count} relationships, {project_count} projects, "
                              f"{action_count} action items, {info_count} information items")
                
                # Get structured knowledge to enhance email analysis
                structured_knowledge = self._get_structured_knowledge_context(user_email)
                
                insights = self.email_intelligence.analyze_recent_emails(
                    user_email, 
                    access_token, 
                    actual_days_back, 
                    previous_insights=existing_insights,
                    structured_knowledge=structured_knowledge
                )
            else:
                logger.info(f"Performing full sync for the last {days_back} days")
                # Get structured knowledge to enhance email analysis
                structured_knowledge = self._get_structured_knowledge_context(user_email)
                
                insights = self.email_intelligence.analyze_recent_emails(
                    user_email, 
                    access_token, 
                    days_back,
                    structured_knowledge=structured_knowledge
                )
            
            # Process and categorize insights into knowledge repositories
            if insights.get('status') == 'success' or insights.get('key_relationships'):
                # 1. Update contacts knowledge
                contacts_knowledge = user_intel.contacts_knowledge or {}
                for relationship in insights.get('key_relationships', []):
                    if isinstance(relationship, dict):
                        contact_email = relationship.get('email', 'unknown')
                        contacts_knowledge[contact_email] = {
                            'name': relationship.get('name'),
                            'role': relationship.get('role'),
                            'importance': relationship.get('importance'),
                            'recent_interactions': relationship.get('recent_interactions'),
                            'last_updated': datetime.utcnow().isoformat()
                        }
                        
                        # Also create/update ContactIntelligence record
                        self._update_contact_intelligence(session, user_email, relationship)
                
                user_intel.contacts_knowledge = contacts_knowledge
                sync_status.progress = 50
                session.commit()
                
                # 2. Update general business knowledge
                business_knowledge = user_intel.general_business_knowledge or {}
                for project in insights.get('active_projects', []):
                    if isinstance(project, dict):
                        project_name = project.get('name', 'Unknown Project')
                        business_knowledge[project_name] = {
                            'description': project.get('description'),
                            'status': project.get('status'),
                            'priority': project.get('priority'),
                            'stakeholders': project.get('key_stakeholders', []),
                            'last_updated': datetime.utcnow().isoformat()
                        }
                
                user_intel.general_business_knowledge = business_knowledge
                sync_status.progress = 70
                session.commit()
                
                # 3. Extract tactical notifications (urgent action items)
                tactical_items = []
                for action in insights.get('action_items', []):
                    if isinstance(action, dict):
                        tactical_items.append({
                            'description': action.get('description'),
                            'deadline': action.get('deadline'),
                            'priority': action.get('priority', 'Medium'),
                            'context': action.get('context'),
                            'created_at': datetime.utcnow().isoformat(),
                            'status': 'pending'
                        })
                
                user_intel.tactical_notifications = tactical_items
                
                # Log summary of new insights for comparison
                relationship_count = len(insights.get('key_relationships', []))
                project_count = len(insights.get('active_projects', []))
                action_count = len(insights.get('action_items', []))
                info_count = len(insights.get('important_information', []))
                
                logger.info(f"Storing new augmented insights: "
                          f"{relationship_count} relationships, {project_count} projects, "
                          f"{action_count} action items, {info_count} information items")
                
                # 4. Store the complete analysis for quick retrieval
                user_intel.last_email_analysis = insights
                
                # Store the insights directly (not nested under 'insights' key)
                # This is important for the cumulative knowledge building to work correctly
                user_intel.email_insights_cache = insights
                
                # Add metadata to the insights
                insights['generated_at'] = datetime.utcnow().isoformat()
                insights['days_analyzed'] = days_back if sync_type == 'full' else actual_days_back
                
                # Update sync status
                sync_status.status = 'completed'
                sync_status.progress = 100
                sync_status.emails_processed = len(insights.get('key_relationships', []))
                
                # Initialize insights_generated with default values to avoid NoneType errors
                sync_status.insights_generated = {
                    'relationships': len(insights.get('key_relationships', [])) if insights.get('key_relationships') else 0,
                    'projects': len(insights.get('active_projects', [])) if insights.get('active_projects') else 0,
                    'action_items': len(insights.get('action_items', [])) if insights.get('action_items') else 0,
                    'important_info': len(insights.get('important_information', [])) if insights.get('important_information') else 0
                }
                sync_status.completed_at = datetime.utcnow()
                
                session.commit()
                
                logger.info(f"Successfully processed and stored insights for {user_email}")
                return {
                    'status': 'success',
                    'sync_id': sync_status.id,
                    'insights_summary': sync_status.insights_generated
                }
            else:
                # Handle error case
                sync_status.status = 'failed'
                sync_status.error_message = insights.get('message', 'Unknown error')
                sync_status.completed_at = datetime.utcnow()
                session.commit()
                
                return {
                    'status': 'error',
                    'message': insights.get('message', 'Failed to analyze emails')
                }
                
        except Exception as e:
            logger.error(f"Error processing email insights: {str(e)}")
            if 'sync_status' in locals():
                sync_status.status = 'failed'
                sync_status.error_message = str(e)
                sync_status.completed_at = datetime.utcnow()
                session.commit()
            
            return {
                'status': 'error',
                'message': str(e)
            }
        finally:
            session.close()
    
    def get_user_insights(self, user_email: str) -> Dict[str, Any]:
        """Retrieve stored insights for a user"""
        session = self.SessionLocal()
        try:
            user_intel = session.query(UserIntelligence).filter_by(user_email=user_email).first()
            
            if not user_intel or not user_intel.email_insights_cache:
                return {
                    'status': 'no_data',
                    'message': 'No insights available. Please sync your emails first.'
                }
            
            # Return the cached insights - now stored directly, not nested under 'insights' key
            insights = user_intel.email_insights_cache
            
            # Add metadata if not already present
            if 'cached_at' not in insights and 'generated_at' in insights:
                insights['cached_at'] = insights['generated_at']
            
            return insights
            
        finally:
            session.close()
    
    def get_tactical_notifications(self, user_email: str) -> List[Dict[str, Any]]:
        """Get pending tactical notifications/action items for a user"""
        session = self.SessionLocal()
        try:
            user_intel = session.query(UserIntelligence).filter_by(user_email=user_email).first()
            
            if not user_intel:
                return []
            
            # Filter for pending items only
            notifications = user_intel.tactical_notifications or []
            pending = [n for n in notifications if n.get('status') == 'pending']
            
            return pending
            
        finally:
            session.close()
    
    def get_contact_intelligence(self, user_email: str, contact_email: str) -> Dict[str, Any]:
        """Get intelligence about a specific contact"""
        session = self.SessionLocal()
        try:
            contact = session.query(ContactIntelligence).filter_by(
                user_email=user_email,
                contact_email=contact_email
            ).first()
            
            if not contact:
                return {'status': 'not_found'}
            
            return {
                'name': contact.contact_name,
                'email': contact.contact_email,
                'relationship_strength': contact.relationship_strength,
                'interaction_frequency': contact.interaction_frequency,
                'topics_discussed': contact.topics_discussed,
                'last_interaction': contact.last_interaction.isoformat() if contact.last_interaction else None,
                'action_items': contact.action_items,
                'summary': contact.relationship_summary
            }
            
        finally:
            session.close()
    
    def _update_contact_intelligence(self, session: Session, user_email: str, relationship: Dict[str, Any]) -> None:
        """Create or update a ContactIntelligence record"""
        contact_email = relationship.get('email', 'unknown')
        if contact_email == 'unknown':
            return
            
        # Check if contact already exists
        contact = session.query(ContactIntelligence).filter_by(
            user_email=user_email,
            contact_email=contact_email
        ).first()
        
        if not contact:
            contact = ContactIntelligence(
                user_email=user_email,
                contact_email=contact_email
            )
            session.add(contact)
        
        # Update contact data
        contact.name = relationship.get('name')
        contact.role = relationship.get('role')
        contact.importance = relationship.get('importance')
        contact.recent_interactions = relationship.get('recent_interactions')
        contact.last_updated = datetime.utcnow()
        
    def _get_structured_knowledge_context(self, user_email: str) -> Dict[str, Any]:
        """Gather structured knowledge to enhance email analysis"""
        # Get projects, goals, and knowledge files
        projects = self.structured_knowledge_service.get_projects(user_email)
        goals = self.structured_knowledge_service.get_goals(user_email)
        knowledge_files = self.structured_knowledge_service.get_knowledge_files(user_email)
        
        # Extract content from knowledge files
        knowledge_content = []
        for file in knowledge_files:
            if file.content_extracted:
                knowledge_content.append({
                    'filename': file.original_filename,
                    'content': file.content_extracted,
                    'category': file.category
                })
        
        return {
            'projects': projects,
            'goals': goals,
            'knowledge_files': knowledge_content
        }
        
    def process_email(self, email: Dict[str, Any], user_email: str) -> None:
        """Process a single email and update the database with extracted information
        
        Args:
            email: Email data from the Gmail API
            user_email: The user's email address
        """
        logger.info(f"Processing email: {email.get('subject', 'No subject')}")
        
        session = self.SessionLocal()
        try:
            # Get or create user intelligence record
            user_intel = session.query(UserIntelligence).filter_by(user_email=user_email).first()
            if not user_intel:
                user_intel = UserIntelligence(user_email=user_email)
                session.add(user_intel)
                session.commit()
            
            # Extract contact information
            if 'from' in email and email['from'].get('email'):
                contact_email = email['from'].get('email')
                contact_name = email['from'].get('name', '')
                
                # Skip if the contact is the user
                if contact_email != user_email:
                    # Update contacts knowledge
                    contacts_knowledge = user_intel.contacts_knowledge or {}
                    
                    if contact_email not in contacts_knowledge:
                        contacts_knowledge[contact_email] = {
                            'name': contact_name,
                            'email': contact_email,
                            'first_contact': email.get('date'),
                            'last_contact': email.get('date'),
                            'email_count': 1,
                            'topics': [email.get('subject', 'No subject')]
                        }
                    else:
                        contacts_knowledge[contact_email]['email_count'] += 1
                        contacts_knowledge[contact_email]['last_contact'] = email.get('date')
                        
                        # Add subject to topics if not already present
                        if email.get('subject') and email.get('subject') not in contacts_knowledge[contact_email].get('topics', []):
                            if 'topics' not in contacts_knowledge[contact_email]:
                                contacts_knowledge[contact_email]['topics'] = []
                            contacts_knowledge[contact_email]['topics'].append(email.get('subject'))
                    
                    user_intel.contacts_knowledge = contacts_knowledge
            
            # Extract potential action items from email content
            if email.get('snippet'):
                snippet = email.get('snippet', '')
                subject = email.get('subject', 'No subject')
                
                # Simple heuristic to detect potential action items
                action_keywords = ['please', 'need', 'required', 'action', 'todo', 'to-do', 'deadline', 'by tomorrow', 'asap']
                is_potential_action = any(keyword in snippet.lower() or keyword in subject.lower() for keyword in action_keywords)
                
                if is_potential_action:
                    # Add to tactical notifications
                    tactical_notifications = user_intel.tactical_notifications or []
                    
                    # Create a new notification
                    notification = {
                        'id': str(len(tactical_notifications) + 1),
                        'text': f"Action item from email: {subject}",
                        'source': 'email',
                        'date': email.get('date'),
                        'priority': 'medium',
                        'email_id': email.get('id', '')
                    }
                    
                    tactical_notifications.append(notification)
                    user_intel.tactical_notifications = tactical_notifications
            
            # Update last_email_analysis with basic info
            last_analysis = user_intel.last_email_analysis or {}
            last_analysis['last_processed_email_date'] = email.get('date')
            last_analysis['total_emails_processed'] = last_analysis.get('total_emails_processed', 0) + 1
            last_analysis['summary'] = f"Processed {last_analysis.get('total_emails_processed', 0)} emails"
            
            user_intel.last_email_analysis = last_analysis
            
            # Update email_insights_cache
            insights_cache = user_intel.email_insights_cache or {}
            insights_cache['generated_at'] = datetime.utcnow().isoformat()
            
            # Update key relationships in insights cache
            if 'key_relationships' not in insights_cache:
                insights_cache['key_relationships'] = []
            
            # Convert contacts to relationships format
            for email_addr, contact in user_intel.contacts_knowledge.items():
                # Check if this contact is already in key_relationships
                existing = False
                for rel in insights_cache['key_relationships']:
                    if rel.get('email') == email_addr:
                        existing = True
                        # Update existing relationship
                        rel['email_count'] = contact.get('email_count', 0)
                        rel['last_contact'] = contact.get('last_contact', '')
                        break
                
                if not existing:
                    # Add new relationship
                    insights_cache['key_relationships'].append({
                        'name': contact.get('name', ''),
                        'email': email_addr,
                        'relationship': 'Contact',
                        'email_count': contact.get('email_count', 0),
                        'last_contact': contact.get('last_contact', '')
                    })
            
            # Add action items to insights cache
            if 'action_items' not in insights_cache:
                insights_cache['action_items'] = []
            
            # Add notifications to action items
            for notification in user_intel.tactical_notifications or []:
                # Check if this notification is already in action_items
                existing = False
                for action in insights_cache['action_items']:
                    if action.get('text') == notification.get('text'):
                        existing = True
                        break
                
                if not existing:
                    # Add new action item
                    insights_cache['action_items'].append({
                        'text': notification.get('text', ''),
                        'due_date': '',  # No due date from simple processing
                        'priority': notification.get('priority', 'medium'),
                        'status': 'open'
                    })
            
            user_intel.email_insights_cache = insights_cache
            
            # Commit changes
            session.commit()
            
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            logger.error(traceback.format_exc())
            session.rollback()
        finally:
            session.close()