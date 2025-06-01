"""
Service layer for managing email intelligence and insights.
Handles storage, retrieval, and processing of Chief of Staff data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database.insights_storage import Base, UserIntelligence, EmailSyncStatus, ContactIntelligence
from backend.core.claude_integration.email_intelligence import EmailIntelligence
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class IntelligenceService:
    def __init__(self, database_url: str, claude_client: Anthropic):
        """Initialize the intelligence service with database and Claude client"""
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.claude_client = claude_client
        self.email_intelligence = EmailIntelligence(claude_client)
    
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
                
                insights = self.email_intelligence.analyze_recent_emails(
                    user_email, 
                    access_token, 
                    actual_days_back, 
                    previous_insights=existing_insights
                )
            else:
                logger.info(f"Performing full sync for the last {days_back} days")
                insights = self.email_intelligence.analyze_recent_emails(user_email, access_token, days_back)
            
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
    
    def _update_contact_intelligence(self, session: Session, user_email: str, relationship_data: Dict):
        """Update ContactIntelligence record with new data"""
        contact_email = relationship_data.get('email')
        if not contact_email:
            return
        
        contact = session.query(ContactIntelligence).filter_by(
            user_email=user_email,
            contact_email=contact_email
        ).first()
        
        if not contact:
            contact = ContactIntelligence(
                user_email=user_email,
                contact_email=contact_email,
                contact_name=relationship_data.get('name', 'Unknown')
            )
            session.add(contact)
        
        # Update with latest data
        contact.relationship_strength = relationship_data.get('importance', 'Medium')
        contact.last_interaction = datetime.utcnow()
        contact.total_interactions += 1
        
        # Update action items if present
        if relationship_data.get('action_needed'):
            action_items = contact.action_items or []
            action_items.append({
                'action': relationship_data['action_needed'],
                'created_at': datetime.utcnow().isoformat()
            })
            contact.action_items = action_items
        
        session.commit()