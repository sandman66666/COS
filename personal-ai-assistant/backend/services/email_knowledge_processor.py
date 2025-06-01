"""
Email Knowledge Processor Service.
This service processes emails from Gmail API to extract knowledge and tasks.
It integrates with the knowledge graph and task generation services.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from integrations.gmail.gmail_connector import GmailConnector
from services.knowledge_integration_service import KnowledgeIntegrationService

logger = logging.getLogger(__name__)

class EmailKnowledgeProcessor:
    """Service for processing emails to extract knowledge and tasks"""
    
    def __init__(self, db_session_factory, claude_client=None):
        """
        Initialize the email knowledge processor service
        
        Args:
            db_session_factory: SQLAlchemy session factory for database operations
            claude_client: Claude API client for entity extraction
        """
        self.db_session_factory = db_session_factory
        self.knowledge_integration_service = KnowledgeIntegrationService(db_session_factory, claude_client)
        logger.info("Initialized Email Knowledge Processor Service")
    
    def process_emails_for_user(self, user_email: str, access_token: str, days_back: int = 7) -> Dict:
        """
        Process recent emails for a user to extract knowledge and tasks
        
        Args:
            user_email: The email of the user
            access_token: OAuth access token for Gmail API
            days_back: Number of days back to process emails
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing emails for knowledge extraction: {user_email}, days back: {days_back}")
        
        # Initialize Gmail connector with the user's access token
        gmail_connector = GmailConnector(access_token)
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for Gmail API query
        start_date_str = start_date.strftime('%Y/%m/%d')
        
        try:
            # Get emails from Gmail API using the native Gmail API through GmailConnector
            # This ensures we're using real emails, not fake data
            query = f"after:{start_date_str}"
            emails = gmail_connector.get_emails(query=query, max_results=50)
            
            if not emails:
                logger.warning(f"No emails found for user {user_email} in the last {days_back} days")
                return {
                    "success": True,
                    "emails_processed": 0,
                    "entities_extracted": 0,
                    "tasks_generated": 0,
                    "knowledge_graph_updated": False
                }
            
            # Process each email
            emails_processed = 0
            entities_extracted = 0
            tasks_generated = 0
            knowledge_graph_updated = False
            
            for email in emails:
                # Skip emails without content
                if not email.get('body'):
                    continue
                
                # Prepare email metadata
                email_metadata = {
                    'id': email.get('id'),
                    'from': email.get('from'),
                    'to': email.get('to'),
                    'subject': email.get('subject'),
                    'date': email.get('date')
                }
                
                # Process email for knowledge extraction
                result = self.knowledge_integration_service.process_email(
                    user_email=user_email,
                    email_content=email.get('body'),
                    email_metadata=email_metadata
                )
                
                # Update counters
                emails_processed += 1
                entities_extracted += len(result.get('entities_extracted', {}).get('people', [])) + \
                                     len(result.get('entities_extracted', {}).get('companies', [])) + \
                                     len(result.get('entities_extracted', {}).get('projects', [])) + \
                                     len(result.get('entities_extracted', {}).get('meetings', []))
                tasks_generated += result.get('tasks_generated', 0)
                knowledge_graph_updated = knowledge_graph_updated or result.get('knowledge_graph_updated', False)
            
            logger.info(f"Processed {emails_processed} emails for user {user_email}")
            return {
                "success": True,
                "emails_processed": emails_processed,
                "entities_extracted": entities_extracted,
                "tasks_generated": tasks_generated,
                "knowledge_graph_updated": knowledge_graph_updated
            }
            
        except Exception as e:
            logger.error(f"Error processing emails for knowledge extraction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_single_email(self, user_email: str, access_token: str, email_id: str) -> Dict:
        """
        Process a single email to extract knowledge and tasks
        
        Args:
            user_email: The email of the user
            access_token: OAuth access token for Gmail API
            email_id: ID of the email to process
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing single email for knowledge extraction: {email_id}")
        
        # Initialize Gmail connector with the user's access token
        gmail_connector = GmailConnector(access_token)
        
        try:
            # Get email from Gmail API using the native Gmail API through GmailConnector
            email = gmail_connector.get_email(email_id)
            
            if not email or not email.get('body'):
                logger.warning(f"Email {email_id} not found or has no content")
                return {
                    "success": False,
                    "error": "Email not found or has no content"
                }
            
            # Prepare email metadata
            email_metadata = {
                'id': email.get('id'),
                'from': email.get('from'),
                'to': email.get('to'),
                'subject': email.get('subject'),
                'date': email.get('date')
            }
            
            # Process email for knowledge extraction
            result = self.knowledge_integration_service.process_email(
                user_email=user_email,
                email_content=email.get('body'),
                email_metadata=email_metadata
            )
            
            logger.info(f"Processed email {email_id} for user {user_email}")
            return {
                "success": True,
                "email": email_metadata,
                "entities_extracted": result.get('entities_extracted', {}),
                "tasks_generated": result.get('tasks_generated', 0),
                "knowledge_graph_updated": result.get('knowledge_graph_updated', False)
            }
            
        except Exception as e:
            logger.error(f"Error processing email for knowledge extraction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
